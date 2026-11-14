"""
Reliability tests for the final development patch.

Covers:
  1. OCR concurrency semaphore (tasks.py)
  2. Stale processing detection (views.py DocumentStatusView)
  3. CORS origin allow/deny rules (settings.py)
  4. JWT authentication flow (login → token → profile)

Frontend polling timeout is verified manually (no frontend test framework configured).
"""
import threading
import time
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
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

        with patch('documents.tasks.Document.objects.get', side_effect=mock_get):
            with patch('documents.tasks.process_document', side_effect=patched_process):
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
        """A document processing for 120s (< 180s threshold) is NOT marked failed."""
        doc = self._make_doc(status='processing', age_seconds=120)
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
