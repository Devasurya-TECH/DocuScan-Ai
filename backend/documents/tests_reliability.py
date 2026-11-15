"""
Reliability tests for the final development patch.

Covers:
  1. OCR concurrency semaphore (tasks.py)
  2. Stale processing detection (views.py DocumentStatusView)
  3. CORS origin allow/deny rules (settings.py)
  4. JWT authentication flow (login → token → profile)
  5. DB connection lifecycle in the daemon thread (tasks.py)

Frontend polling timeout is verified manually (no frontend test framework configured).
"""
import threading
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.db import OperationalError as DjDBError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from documents.models import Document
from documents.tasks import OCR_SEMAPHORE, _execute_processing


# =============================================================================
# 1. OCR SEMAPHORE TESTS
# =============================================================================

class OCRSemaphoreTests(TestCase):
    """Verify that OCR_SEMAPHORE is released correctly under all conditions."""

    def setUp(self):
        self.user = User.objects.create_user(username='semtest', password='pass1234!')
        # Create a minimal document record (no real file needed for semaphore tests)
        self.doc = Document.objects.create(
            user=self.user,
            title='test.png',
            uploaded_file='documents/test.png',
            status='uploaded',
        )

    def _initial_semaphore_value(self):
        """Return current semaphore internal counter value."""
        return OCR_SEMAPHORE._value

    def test_semaphore_released_after_success(self):
        """Semaphore is at 1 (free) after a successful processing call."""
        before = self._initial_semaphore_value()
        self.assertEqual(before, 1, "Semaphore should start free")

        with patch('documents.tasks.process_document') as mock_proc:
            mock_proc.return_value = None
            _execute_processing(self.doc.pk)

        self.assertEqual(self._initial_semaphore_value(), 1,
                         "Semaphore must be released after success")

    def test_semaphore_released_after_exception(self):
        """Semaphore is at 1 (free) even when process_document raises."""
        with patch('documents.tasks.process_document', side_effect=RuntimeError("OCR boom")):
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                _execute_processing(self.doc.pk)

        self.assertEqual(self._initial_semaphore_value(), 1,
                         "Semaphore must be released after exception")

    def test_concurrent_ocr_serialized(self):
        """
        Two simultaneous _execute_processing calls do not overlap inside the
        semaphore-guarded section. We verify that max concurrent executions == 1.
        """
        from unittest.mock import MagicMock
        active_count = 0
        max_concurrent = 0
        counter_lock = threading.Lock()

        mock_doc1 = MagicMock(id=1, pk=1)
        mock_doc2 = MagicMock(id=2, pk=2)

        def mock_get(pk, **kwargs):
            return mock_doc1 if pk == 1 else mock_doc2

        def patched_process(document, **kwargs):
            nonlocal active_count, max_concurrent
            with counter_lock:
                active_count += 1
                if active_count > max_concurrent:
                    max_concurrent = active_count
            time.sleep(0.08)
            with counter_lock:
                active_count -= 1

        mock_filter_qs = MagicMock()
        mock_filter_qs.values.return_value.first.return_value = None

        with patch('documents.tasks.Document.objects.get', side_effect=mock_get), \
             patch('documents.tasks.Document.objects.filter', return_value=mock_filter_qs), \
             patch('documents.tasks.process_document', side_effect=patched_process), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()):
            t1 = threading.Thread(target=_execute_processing, args=(1,))
            t2 = threading.Thread(target=_execute_processing, args=(2,))
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)

        self.assertEqual(max_concurrent, 1,
                         "Only 1 OCR execution should be active at any time under the semaphore")
        self.assertEqual(self._initial_semaphore_value(), 1, "Semaphore must be free at end")


# =============================================================================
# 2. STALE PROCESSING DETECTION TESTS
# =============================================================================

class StaleProcessingDetectionTests(TestCase):
    """Verify that DocumentStatusView marks stale processing jobs as failed."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='staletest', password='pass1234!')
        self.client.force_authenticate(user=self.user)

    def _make_doc(self, status='processing', age_seconds=0):
        doc = Document.objects.create(
            user=self.user,
            title='scan.png',
            uploaded_file='documents/scan.png',
            status=status,
            progress_stage='ocr_inference',
        )
        if age_seconds:
            # Backdating updated_at simulates a job that has been stuck
            Document.objects.filter(pk=doc.pk).update(
                updated_at=timezone.now() - timedelta(seconds=age_seconds)
            )
            doc.refresh_from_db()
        return doc

    def test_stale_processing_marked_failed(self):
        """A document stuck in processing for >3 min is marked failed on poll."""
        doc = self._make_doc(status='processing', age_seconds=200)  # 3m20s ago
        url = f'/api/documents/{doc.pk}/status/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'failed',
                         "Stale processing document must be reported as failed")
        self.assertIn('interrupted', data.get('failure_reason', '').lower(),
                      "Failure reason must explain interruption")

        # Confirm the DB was updated too
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'failed')

    def test_fresh_processing_not_touched(self):
        """A document that just started processing is NOT marked failed."""
        doc = self._make_doc(status='processing', age_seconds=10)
        url = f'/api/documents/{doc.pk}/status/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'processing',
                         "A recently started processing job must remain in processing state")

    def test_completed_document_unaffected(self):
        """Completed documents are never touched by stale detection."""
        doc = self._make_doc(status='completed', age_seconds=300)
        url = f'/api/documents/{doc.pk}/status/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')

    def test_processing_below_threshold_not_marked_stale(self):
        """A document processing for 90s (< 110s threshold) is NOT marked failed."""
        doc = self._make_doc(status='processing', age_seconds=90)
        url = f'/api/documents/{doc.pk}/status/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'processing')

    def test_processing_past_threshold_is_stale(self):
        """A document processing for >180s (e.g. 200s) IS marked failed."""
        doc = self._make_doc(status='processing', age_seconds=200)
        url = f'/api/documents/{doc.pk}/status/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'failed')


# =============================================================================
# 3. CORS ORIGIN TESTS
# =============================================================================

class CORSOriginTests(TestCase):
    """
    Verify that CORS allows the correct origins and blocks others.

    Uses Django's test client with HTTP_ORIGIN header.
    django-cors-headers adds Access-Control-Allow-Origin to responses when
    the origin matches the allowed list / regex.
    """

    def _cors_header(self, origin):
        """
        Issue an OPTIONS preflight to /api/auth/token/ with the given origin,
        return the Access-Control-Allow-Origin response header value (or '').
        """
        response = self.client.options(
            '/api/auth/token/',
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        )
        return response.get('Access-Control-Allow-Origin', '')

    def test_production_vercel_origin_allowed(self):
        header = self._cors_header('https://docu-scan-ai-sigma.vercel.app')
        self.assertIn('docu-scan-ai-sigma.vercel.app', header,
                      "Production Vercel URL must be CORS-allowed")

    def test_vercel_preview_deploy_allowed(self):
        """Preview deploys like docu-scan-ai-sigma-git-main-xyz.vercel.app must be allowed."""
        header = self._cors_header('https://docu-scan-ai-sigma-git-main-abc123.vercel.app')
        self.assertIn('docu-scan-ai-sigma', header,
                      "Vercel preview deploys for this project must be CORS-allowed")

    def test_unrelated_vercel_domain_blocked(self):
        """Other people's Vercel deployments must NOT be allowed."""
        header = self._cors_header('https://totally-different-app.vercel.app')
        self.assertEqual(header, '',
                         "Unrelated *.vercel.app domains must be CORS-blocked")

    def test_localhost_5173_allowed(self):
        """Development origin http://localhost:5173 must be allowed."""
        header = self._cors_header('http://localhost:5173')
        self.assertIn('localhost', header,
                      "localhost:5173 must be CORS-allowed for local development")

    def test_localhost_3000_allowed(self):
        header = self._cors_header('http://localhost:3000')
        self.assertIn('localhost', header)

    def test_arbitrary_http_origin_blocked(self):
        """Random HTTP origins must be blocked."""
        header = self._cors_header('http://evil.example.com')
        self.assertEqual(header, '')


# =============================================================================
# 4. JWT AUTHENTICATION FLOW TEST
# =============================================================================

class JWTAuthFlowTests(TestCase):
    """End-to-end: register → login → access protected endpoint → logout."""

    def setUp(self):
        self.client = APIClient()

    def test_register_login_profile_flow(self):
        # 1. Register
        reg_resp = self.client.post('/api/auth/register/', {
            'username': 'flowuser',
            'email': 'flow@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }, format='json')
        self.assertIn(reg_resp.status_code, [200, 201],
                      f"Registration failed: {reg_resp.data}")

        # 2. Obtain tokens
        token_resp = self.client.post('/api/auth/token/', {
            'username': 'flowuser',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(token_resp.status_code, 200,
                         f"Token endpoint failed: {token_resp.data}")
        access = token_resp.data.get('access')
        refresh = token_resp.data.get('refresh')
        self.assertIsNotNone(access, "Access token must be returned")
        self.assertIsNotNone(refresh, "Refresh token must be returned")

        # 3. Access profile with Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        profile_resp = self.client.get('/api/auth/me/')
        self.assertEqual(profile_resp.status_code, 200,
                         f"Profile endpoint failed: {profile_resp.data}")
        self.assertEqual(profile_resp.data.get('username'), 'flowuser')

        # Also test the /auth/profile/ alias
        alias_resp = self.client.get('/api/auth/profile/')
        self.assertEqual(alias_resp.status_code, 200)

        # 4. Refresh token
        self.client.credentials()  # clear auth header
        refresh_resp = self.client.post('/api/auth/token/refresh/', {
            'refresh': refresh,
        }, format='json')
        self.assertEqual(refresh_resp.status_code, 200,
                         "Token refresh must succeed with valid refresh token")
        self.assertIn('access', refresh_resp.data)

        # 5. Unauthenticated request to protected endpoint returns 401
        self.client.credentials()
        unauth_resp = self.client.get('/api/auth/me/')
        self.assertEqual(unauth_resp.status_code, 401,
                         "Unauthenticated request to /api/auth/me/ must return 401")

    def test_invalid_credentials_rejected(self):
        User.objects.create_user(username='realuser', password='correct123!')
        resp = self.client.post('/api/auth/token/', {
            'username': 'realuser',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(resp.status_code, 401,
                         "Invalid credentials must return 401")

    def test_expired_refresh_token_rejected(self):
        """Tampered / expired refresh tokens must be rejected."""
        resp = self.client.post('/api/auth/token/refresh/', {
            'refresh': 'this.is.not.a.valid.jwt',
        }, format='json')
        self.assertIn(resp.status_code, [400, 401],
                      "Invalid refresh token must be rejected")


# =============================================================================
# 5. DB CONNECTION LIFECYCLE TESTS
# =============================================================================

class DBConnectionLifecycleTests(TestCase):
    """
    Verify the daemon-thread DB connection lifecycle introduced to prevent
    OperationalError from Neon serverless closing idle connections during OCR.

    All tests patch close_old_connections and db_connections to avoid touching
    a real database socket — the behaviour under test is the call sequence, not
    the network layer.
    """

    def setUp(self):
        from documents.tasks import ACTIVE_TASKS
        ACTIVE_TASKS.clear()
        self.user = User.objects.create_user(username='dbtest', password='pass1234!')
        self.doc = Document.objects.create(
            user=self.user,
            title='test.png',
            uploaded_file='documents/test.png',
            status='uploaded',
        )

    def tearDown(self):
        from documents.tasks import ACTIVE_TASKS
        ACTIVE_TASKS.clear()

    # ------------------------------------------------------------------
    # Test 1 — Successful OCR updates status to completed
    # ------------------------------------------------------------------
    def test_successful_ocr_sets_completed(self):
        """
        process_document succeeds → _execute_processing returns 'completed'
        and the post-OCR fields are written to the database.

        Note: status='completed' is written by process_document() (mocked here).
        _execute_processing itself writes progress_stage='completed' and
        progress_percent=100 after process_document returns. We assert both the
        return value and those post-OCR fields to confirm the success path runs
        end-to-end. db_connections is a MagicMock so close_all() is a no-op
        and does not wipe the real SQLite test connection.
        """
        mock_db_conns = MagicMock()

        def fake_process_document(document, **kwargs):
            # Simulate what real process_document does: write status=completed
            document.status = 'completed'
            document.save(update_fields=['status', 'updated_at'])

        with patch('documents.tasks.process_document', side_effect=fake_process_document), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', mock_db_conns):
            result = _execute_processing(self.doc.pk)

        self.assertEqual(result['status'], 'completed')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'completed')
        self.assertEqual(self.doc.progress_stage, 'completed')
        self.assertEqual(self.doc.progress_percent, 100)

    # ------------------------------------------------------------------
    # Test 2 — OCR exception updates status to failed
    # ------------------------------------------------------------------
    def test_ocr_exception_sets_failed(self):
        """process_document raising → document.status == 'failed' with reason stored."""
        with patch('documents.tasks.process_document', side_effect=ValueError('OCR boom')), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()), \
             override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = _execute_processing(self.doc.pk)

        self.assertEqual(result['status'], 'failed')
        self.assertIn('OCR boom', result.get('error', ''))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'failed')
        self.assertIn('OCR boom', self.doc.failure_reason)

    # ------------------------------------------------------------------
    # Test 3 — DB connection failure during final save is logged at CRITICAL
    # ------------------------------------------------------------------
    def test_db_error_during_save_logged_at_critical(self):
        """
        When process_document raises OperationalError AND the error-handler
        save also raises, a CRITICAL log is emitted and no exception leaks
        out of _execute_processing (the daemon thread must not crash).

        The blanket Document.save mock must allow the two pre-semaphore saves
        (status='processing', progress_stage='starting') to succeed so the
        document record is reachable before we simulate a mid-OCR DB loss.
        Only saves that occur inside the semaphore block are intercepted.
        """
        save_calls = {'n': 0}
        original_save = Document.save

        def selective_save(self_inst, *args, **kwargs):
            save_calls['n'] += 1
            if save_calls['n'] <= 1:
                # Let the initial pre-semaphore status save succeed
                return original_save(self_inst, *args, **kwargs)
            # Simulate Neon closing the connection on all subsequent saves
            raise DjDBError('Neon closed socket')

        with patch('documents.tasks.process_document', side_effect=DjDBError('Neon closed socket')), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()), \
             patch.object(Document, 'save', selective_save), \
             override_settings(CELERY_TASK_ALWAYS_EAGER=True), \
             self.assertLogs('documents.tasks', level='CRITICAL') as log_ctx:
            # Must not raise — exception must be contained within the function
            _execute_processing(self.doc.pk)

        self.assertTrue(
            any('UNRECOVERABLE' in line for line in log_ctx.output),
            'A CRITICAL UNRECOVERABLE log must be emitted when both the OCR '
            'and the error-handler save fail',
        )

    # ------------------------------------------------------------------
    # Test 4 — Stale connection is recovered before saving OCR results
    # ------------------------------------------------------------------
    def test_close_old_connections_called_at_entry_and_before_post_ocr_save(self):
        """
        close_old_connections() must be called at least twice:
          • once at thread entry (discard inherited stale handle)
          • once after process_document returns (before the post-OCR save)
        This guarantees the final DB write uses a fresh connection.
        """
        close_calls = []

        def track_close():
            close_calls.append(time.monotonic())

        with patch('documents.tasks.close_old_connections', side_effect=track_close) as mock_close, \
             patch('documents.tasks.process_document') as mock_proc, \
             patch('documents.tasks.db_connections', MagicMock()):
            mock_proc.return_value = self.doc
            _execute_processing(self.doc.pk)

        self.assertGreaterEqual(
            mock_close.call_count, 2,
            'close_old_connections() must be called at entry AND before the '
            'post-OCR save — found only %d call(s)' % mock_close.call_count,
        )

    # ------------------------------------------------------------------
    # Test 5 — Multiple uploads respect the OCR semaphore
    # ------------------------------------------------------------------
    def test_concurrent_uploads_serialized_by_semaphore(self):
        """
        Two simultaneous _execute_processing calls must never execute OCR
        concurrently. Max concurrent OCR == 1 at any instant.
        The semaphore must be fully released (value == 1) when both finish.

        All DB operations are mocked so threads never issue concurrent SQLite
        writes (SQLite in-memory test DB serialises writes and raises
        'table is locked' under real concurrency). The semaphore behaviour
        — not the ORM — is what this test verifies.
        """
        active = {'count': 0, 'max': 0}
        counter_lock = threading.Lock()

        def patched_process(document, **kwargs):
            with counter_lock:
                active['count'] += 1
                active['max'] = max(active['max'], active['count'])
            time.sleep(0.05)
            with counter_lock:
                active['count'] -= 1

        # Build a minimal mock document that satisfies all attribute accesses
        # inside _execute_processing without touching the real database.
        def make_mock_doc(pk):
            doc = MagicMock(spec=Document)
            doc.pk = pk
            doc.id = pk
            doc.save = MagicMock()
            doc.refresh_from_db = MagicMock()
            return doc

        mock_doc1 = make_mock_doc(1001)
        mock_doc2 = make_mock_doc(1002)

        def mock_get(pk, **kwargs):
            return mock_doc1 if pk == 1001 else mock_doc2

        mock_filter_qs = MagicMock()
        mock_filter_qs.values.return_value.first.return_value = None

        with patch('documents.tasks.Document.objects.get', side_effect=mock_get), \
             patch('documents.tasks.Document.objects.filter', return_value=mock_filter_qs), \
             patch('documents.tasks.process_document', side_effect=patched_process), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()):
            t1 = threading.Thread(target=_execute_processing, args=(1001,))
            t2 = threading.Thread(target=_execute_processing, args=(1002,))
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)

        self.assertEqual(
            active['max'], 1,
            'At most 1 OCR pass must be active concurrently under the semaphore',
        )
        self.assertEqual(OCR_SEMAPHORE._value, 1,
                         'Semaphore must be fully released after both threads finish')

    # ------------------------------------------------------------------
    # Test 6 — Stale document recovered after frontend polling stops
    # ------------------------------------------------------------------
    def test_stale_document_recovered_on_next_poll_after_timeout(self):
        """
        A document stuck in 'processing' for > _STALE_PROCESSING_SECONDS (110 s)
        is marked 'failed' on the next status poll, even if the browser had
        stopped polling for a while and then resumed.
        """
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Simulate a document stuck well past the 110 s threshold
        doc = Document.objects.create(
            user=self.user,
            title='stuck.png',
            uploaded_file='documents/stuck.png',
            status='processing',
            progress_stage='ocr_inference',
        )
        Document.objects.filter(pk=doc.pk).update(
            updated_at=timezone.now() - timedelta(seconds=200)
        )

        # Simulate browser resuming a poll after a pause
        response = client.get(f'/api/documents/{doc.pk}/status/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data['status'], 'failed',
            'A document stuck for 200 s must be marked failed on the next poll '
            '(threshold is 110 s)',
        )
        self.assertIn('interrupted', data.get('failure_reason', '').lower())

        doc.refresh_from_db()
        self.assertEqual(doc.status, 'failed',
                         'The failed status must be persisted to the database')

    # ------------------------------------------------------------------
    # Test 7 — Active processing is NOT incorrectly marked failed
    # ------------------------------------------------------------------
    def test_document_processing_within_threshold_not_marked_stale(self):
        """
        A document whose updated_at is 90 s ago (< 110 s threshold) must
        remain in 'processing' — Tesseract may still be running.
        """
        client = APIClient()
        client.force_authenticate(user=self.user)

        doc = Document.objects.create(
            user=self.user,
            title='active.png',
            uploaded_file='documents/active.png',
            status='processing',
            progress_stage='ocr_inference',
        )
        Document.objects.filter(pk=doc.pk).update(
            updated_at=timezone.now() - timedelta(seconds=90)
        )

        response = client.get(f'/api/documents/{doc.pk}/status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['status'], 'processing',
            'A document updated 90 s ago must NOT be marked stale '
            '(threshold is 110 s, so 90 s is still within the active window)',
        )

    # ------------------------------------------------------------------
    # Test 8 — DB connections closed during OCR execution
    # ------------------------------------------------------------------
    def test_db_connections_closed_during_ocr_execution(self):
        """
        Verify that db_connections.close_all() is called before OCR execution
        so that idle database connections are not kept open during OCR.
        """
        closed_during_ocr = False
        mock_db_conns = MagicMock()

        def fake_ocr(doc, **kwargs):
            nonlocal closed_during_ocr
            closed_during_ocr = mock_db_conns.close_all.called

        with patch('documents.tasks.process_document', side_effect=fake_ocr), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', mock_db_conns):
            _execute_processing(self.doc.pk)

        self.assertTrue(closed_during_ocr, "db_connections.close_all() must be called before OCR execution")

    # ------------------------------------------------------------------
    # Test 9 — Document waiting for semaphore is NOT marked stale
    # ------------------------------------------------------------------
    def test_document_waiting_for_semaphore_not_marked_stale(self):
        """
        A document that has been waiting in memory for OCR_SEMAPHORE for > 110s
        must NOT be marked stale, because it is actively queued in memory.
        """
        from documents.tasks import register_active_task, unregister_active_task

        client = APIClient()
        client.force_authenticate(user=self.user)

        doc = Document.objects.create(
            user=self.user,
            title='waiting.png',
            uploaded_file='documents/waiting.png',
            status='processing',
            progress_stage='queued',
        )
        Document.objects.filter(pk=doc.pk).update(
            updated_at=timezone.now() - timedelta(seconds=200)
        )

        register_active_task(doc.pk, 'job-wait', stage='queued')
        try:
            response = client.get(f'/api/documents/{doc.pk}/status/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json()['status'], 'processing',
                'A document waiting for the semaphore must NOT be marked stale',
            )
            doc.refresh_from_db()
            self.assertEqual(doc.status, 'processing')
        finally:
            unregister_active_task(doc.pk)

    # ------------------------------------------------------------------
    # Test 10 — Active OCR task is NOT marked stale
    # ------------------------------------------------------------------
    def test_active_ocr_task_not_marked_stale(self):
        """
        A document actively executing OCR in memory for > 110s must NOT be
        marked stale by status polling.
        """
        from documents.tasks import register_active_task, unregister_active_task

        client = APIClient()
        client.force_authenticate(user=self.user)

        doc = Document.objects.create(
            user=self.user,
            title='active_ocr.png',
            uploaded_file='documents/active_ocr.png',
            status='processing',
            progress_stage='ocr_running',
        )
        Document.objects.filter(pk=doc.pk).update(
            updated_at=timezone.now() - timedelta(seconds=200)
        )

        register_active_task(doc.pk, 'job-ocr', stage='ocr_running')
        try:
            response = client.get(f'/api/documents/{doc.pk}/status/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json()['status'], 'processing',
                'An actively executing OCR document must NOT be marked stale',
            )
            doc.refresh_from_db()
            self.assertEqual(doc.status, 'processing')
        finally:
            unregister_active_task(doc.pk)

    # ------------------------------------------------------------------
    # Test 11 — Completed document cannot become failed due to stale recovery
    # ------------------------------------------------------------------
    def test_completed_document_cannot_become_failed_due_to_stale_recovery(self):
        """
        A completed document with an old updated_at (> 300s) must never be
        touched by stale recovery.
        """
        client = APIClient()
        client.force_authenticate(user=self.user)

        doc = Document.objects.create(
            user=self.user,
            title='done.png',
            uploaded_file='documents/done.png',
            status='completed',
            progress_stage='completed',
            progress_percent=100,
        )
        Document.objects.filter(pk=doc.pk).update(
            updated_at=timezone.now() - timedelta(seconds=500)
        )

        response = client.get(f'/api/documents/{doc.pk}/status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'completed')

    # ------------------------------------------------------------------
    # Test 12 — Failed document cannot become completed by old background task
    # ------------------------------------------------------------------
    def test_failed_document_cannot_become_completed_by_old_task(self):
        """
        If a document is marked failed while OCR is running, when the old
        task finishes, it must NOT overwrite the failed status with completed.
        """
        def fake_ocr(document, **kwargs):
            # Simulate external failure (stale recovery or user cancellation)
            Document.objects.filter(pk=document.pk).update(
                status='failed',
                failure_reason='Interrupted externally',
            )

        with patch('documents.tasks.process_document', side_effect=fake_ocr), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()):
            _execute_processing(self.doc.pk)

        self.doc.refresh_from_db()
        self.assertEqual(
            self.doc.status, 'failed',
            'An old task must not overwrite a failed status back to completed',
        )

    # ------------------------------------------------------------------
    # Test 13 — Retry does not allow older task to overwrite its status
    # ------------------------------------------------------------------
    def test_retry_does_not_allow_older_task_to_overwrite_status(self):
        """
        If a document is retried with a new job_id, an older task finishing
        must NOT overwrite the new retry's status or progress stage.
        """
        old_job_id = 'job-v1-old'
        new_job_id = 'job-v2-new'

        def fake_ocr(document, **kwargs):
            # Simulate reprocess triggered during slow OCR of old job
            Document.objects.filter(pk=document.pk).update(
                job_id=new_job_id,
                status='processing',
                progress_stage='reprocessing',
            )

        with patch('documents.tasks.process_document', side_effect=fake_ocr), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()):
            _execute_processing(self.doc.pk, job_id=old_job_id)

        self.doc.refresh_from_db()
        self.assertEqual(self.doc.job_id, new_job_id)
        self.assertEqual(
            self.doc.progress_stage, 'reprocessing',
            'Old task must abort and preserve the newer retry job stage',
        )

    # ------------------------------------------------------------------
    # Test 14 — Multiple threads do not cause inconsistent document states
    # ------------------------------------------------------------------
    def test_multiple_threads_do_not_cause_inconsistent_document_states(self):
        """
        Multiple concurrent processing threads serialized through the semaphore
        all finish in consistent completed states without corrupted fields.
        """
        from documents.tasks import get_active_tasks

        def make_mock_doc(pk):
            doc = MagicMock(spec=Document)
            doc.pk = pk
            doc.id = pk
            doc.job_id = f'job-{pk}'
            doc.status = 'uploaded'
            doc.save = MagicMock()
            doc.refresh_from_db = MagicMock()
            return doc

        mock_doc1 = make_mock_doc(201)
        mock_doc2 = make_mock_doc(202)
        mock_doc3 = make_mock_doc(203)

        def mock_get(pk, **kwargs):
            if pk == 201:
                return mock_doc1
            if pk == 202:
                return mock_doc2
            return mock_doc3

        mock_filter_qs = MagicMock()
        mock_filter_qs.values.return_value.first.return_value = None

        def mock_proc(doc, **kwargs):
            time.sleep(0.02)
            doc.status = 'completed'

        # Run 3 threads concurrently
        with patch('documents.tasks.Document.objects.get', side_effect=mock_get), \
             patch('documents.tasks.Document.objects.filter', return_value=mock_filter_qs), \
             patch('documents.tasks.process_document', side_effect=mock_proc), \
             patch('documents.tasks.close_old_connections'), \
             patch('documents.tasks.db_connections', MagicMock()):
            threads = [
                threading.Thread(target=_execute_processing, args=(201,)),
                threading.Thread(target=_execute_processing, args=(202,)),
                threading.Thread(target=_execute_processing, args=(203,)),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        self.assertEqual(mock_doc1.status, 'completed')
        self.assertEqual(mock_doc2.status, 'completed')
        self.assertEqual(mock_doc3.status, 'completed')
        self.assertEqual(OCR_SEMAPHORE._value, 1)
        self.assertEqual(len(get_active_tasks()), 0, "All active tasks must be unregistered on exit")
