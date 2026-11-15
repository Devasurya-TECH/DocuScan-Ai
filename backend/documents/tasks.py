import logging
import threading
import time
import uuid

from django.conf import settings
from django.db import close_old_connections, connections as db_connections
from django.utils import timezone
from celery import shared_task

from .models import Document
from .services.document_processing import process_document

logger = logging.getLogger(__name__)

# In-process concurrency limiter for CPU/memory-bound OCR operations.
# SCOPE NOTE: This semaphore restricts concurrent OCR tasks within the single
# Gunicorn application process (e.g., Render Free tier with --workers 1 --threads 2).
# It guarantees that simultaneous uploads queue cleanly in memory and only ONE heavy
# image-processing pass executes at any instant, keeping total RSS safely under 512 MB.
# It does NOT provide distributed coordination across multi-worker/multi-server clusters.
OCR_SEMAPHORE = threading.Semaphore(1)

# In-memory registry of documents currently queued or actively processing in this process.
# Protected by ACTIVE_TASKS_LOCK to guarantee thread safety across concurrent requests.
ACTIVE_TASKS_LOCK = threading.Lock()
ACTIVE_TASKS = {}  # doc_id -> {'job_id': str, 'stage': str, 'started_at': float, 'thread_name': str}


def register_active_task(document_id, job_id='', stage='queued'):
    """Record that a document task is actively queued or running in this worker process."""
    with ACTIVE_TASKS_LOCK:
        ACTIVE_TASKS[document_id] = {
            'job_id': job_id,
            'stage': stage,
            'started_at': time.monotonic(),
            'thread_name': threading.current_thread().name,
        }


def update_active_task_stage(document_id, stage):
    """Update progress stage of an active task."""
    with ACTIVE_TASKS_LOCK:
        if document_id in ACTIVE_TASKS:
            ACTIVE_TASKS[document_id]['stage'] = stage


def unregister_active_task(document_id, job_id=None):
    """
    Remove document from active tracking upon task completion or exit.
    If job_id is provided, only unregisters if the registered job matches,
    preventing a superseded task from accidentally unregistering a newer active job.
    """
    with ACTIVE_TASKS_LOCK:
        if document_id in ACTIVE_TASKS:
            registered_job = ACTIVE_TASKS[document_id].get('job_id')
            if job_id is None or not registered_job or registered_job == job_id:
                ACTIVE_TASKS.pop(document_id, None)


def is_document_active(document_id):
    """Return True if document is currently queued or executing in this process."""
    with ACTIVE_TASKS_LOCK:
        return document_id in ACTIVE_TASKS


def get_active_tasks():
    """Return a snapshot of active document IDs and task metadata."""
    with ACTIVE_TASKS_LOCK:
        return dict(ACTIVE_TASKS)


def _execute_processing(document_id, job_id=None, languages=None):
    """
    Core execution logic for document processing with in-process concurrency guard.

    DB Connection Lifecycle (critical for Neon serverless free tier):
    ----------------------------------------------------------------
    Django DB connections are thread-local. This function runs in a daemon thread
    that is NOT a Django request handler, so the normal request-lifecycle connection
    management (close_old_connections on request start/end) never fires automatically.

    The lifecycle here is explicit:
      1. close_old_connections() at entry — discard any inherited or stale handle.
      2. Connection opens naturally on the first ORM call.
      3. db_connections.close_all() before the OCR subprocess — Tesseract can run
         for 30–90 s with no DB activity. Neon serverless closes idle sockets far
         sooner than CONN_MAX_AGE on the free tier. No connection is held open
         across this idle window.
      4. close_old_connections() before writing OCR results — guarantees the handle
         used for the final saves is freshly opened, not a stale cached one.
      5. finally: db_connections.close_all() & unregister_active_task() — release
         the connection and memory tracking when the thread exits.
    """
    thread_name = threading.current_thread().name
    start_time = time.monotonic()
    effective_job_id = job_id or uuid.uuid4().hex

    logger.info(
        '[doc=%s thread=%s job=%s] Processing started.',
        document_id, thread_name, effective_job_id,
    )

    # Step 1: Discard any stale handle inherited from the HTTP thread or a prior run.
    close_old_connections()

    # Register in active tasks registry as queued
    register_active_task(document_id, effective_job_id, stage='queued')

    try:
        # --- Initial DB reads and status update (connection opened here) ---
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            logger.error('[doc=%s thread=%s job=%s] Document not found.', document_id, thread_name, effective_job_id)
            return {'status': 'not_found', 'document_id': document_id}

        effective_job_id = job_id or document.job_id or effective_job_id
        document.job_id = effective_job_id
        register_active_task(document_id, effective_job_id, stage='queued')
        document.status = 'processing'
        document.progress_stage = 'starting'
        document.progress_percent = 10
        document.save(update_fields=['job_id', 'status', 'progress_stage', 'progress_percent', 'updated_at'])

        logger.info(
            '[doc=%s thread=%s job=%s] Status set to processing. Waiting for OCR semaphore.',
            document.id, thread_name, effective_job_id,
        )

        semaphore_wait_start = time.monotonic()

        with OCR_SEMAPHORE:
            semaphore_acquired = time.monotonic()
            wait_duration = semaphore_acquired - semaphore_wait_start
            update_active_task_stage(document.id, 'ocr_running')
            logger.info(
                '[doc=%s thread=%s job=%s] Semaphore acquired after %.2fs. Starting OCR pipeline.',
                document.id, thread_name, effective_job_id, wait_duration,
            )

            # Check if document was cancelled or superseded while waiting for semaphore
            close_old_connections()
            current_state = Document.objects.filter(pk=document.id).values('status', 'job_id').first()
            if current_state and (current_state['status'] != 'processing' or (effective_job_id and current_state.get('job_id') and current_state['job_id'] != effective_job_id)):
                logger.warning(
                    '[doc=%s thread=%s job=%s] Document status/job changed while waiting for semaphore '
                    '(status=%s, job_id=%s). Aborting execution.',
                    document.id, thread_name, effective_job_id,
                    current_state.get('status'), current_state.get('job_id'),
                )
                return {'status': 'aborted_superseded', 'document_id': document.id}

            try:
                # Step 3: Explicitly close the DB connection before the OCR subprocess.
                # process_document() calls document.save() internally at progress stages,
                # then enters the Tesseract subprocess which can block for 30–90s with no DB activity.
                db_connections.close_all()
                logger.debug(
                    '[doc=%s thread=%s job=%s] DB connection closed before OCR subprocess.',
                    document.id, thread_name, effective_job_id,
                )

                ocr_start = time.monotonic()
                process_document(document, languages=languages)
                ocr_elapsed = time.monotonic() - ocr_start
                logger.info(
                    '[doc=%s thread=%s job=%s] process_document() completed in %.2fs.',
                    document.id, thread_name, effective_job_id, ocr_elapsed,
                )

                # Step 4: Ensure a fresh connection before post-OCR saves.
                close_old_connections()

                # Concurrency check: Ensure the document was not marked failed or superseded externally
                current_state = Document.objects.filter(pk=document.id).values('status', 'job_id').first()
                if current_state and (current_state['status'] not in ('processing', 'completed') or (effective_job_id and current_state.get('job_id') and current_state['job_id'] != effective_job_id)):
                    logger.warning(
                        '[doc=%s thread=%s job=%s] Document was modified externally during OCR '
                        '(status=%s, job_id=%s); aborting completion save.',
                        document.id, thread_name, effective_job_id,
                        current_state.get('status'), current_state.get('job_id'),
                    )
                    return {'status': 'aborted_superseded', 'document_id': document.id}

                document.refresh_from_db()
                document.progress_stage = 'completed'
                document.progress_percent = 100
                document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])

                total_elapsed = time.monotonic() - start_time
                logger.info(
                    '[doc=%s thread=%s job=%s] Processing completed successfully in %.2fs total.',
                    document.id, thread_name, effective_job_id, total_elapsed,
                )
                return {'status': 'completed', 'document_id': document.id}

            except Exception as exc:
                elapsed = time.monotonic() - start_time
                logger.exception(
                    '[doc=%s thread=%s job=%s] Processing failed after %.2fs: %s',
                    document.id, thread_name, effective_job_id, elapsed, exc,
                )

                # Step 6: Close and reopen before persisting the failed status.
                # Concurrency check: only update if document is still 'processing' and matching job_id.
                try:
                    close_old_connections()
                    current_state = Document.objects.filter(pk=document.id).values('status', 'job_id').first()
                    if not current_state or (current_state['status'] == 'processing' and (not effective_job_id or not current_state.get('job_id') or current_state['job_id'] == effective_job_id)):
                        document.status = 'failed'
                        document.progress_stage = 'failed'
                        document.failure_reason = str(exc)[:1000]
                        document.save(update_fields=[
                            'status', 'progress_stage', 'failure_reason', 'updated_at'
                        ])
                        logger.info(
                            '[doc=%s thread=%s job=%s] Failed status persisted to database.',
                            document.id, thread_name, effective_job_id,
                        )
                    else:
                        logger.warning(
                            '[doc=%s thread=%s job=%s] Document was superseded or no longer processing; failed status not persisted.',
                            document.id, thread_name, effective_job_id,
                        )
                except Exception as save_exc:
                    # The DB is unreachable. The stale-detection path in
                    # DocumentStatusView will mark the document failed after
                    # _STALE_PROCESSING_SECONDS when polling resumes.
                    logger.critical(
                        '[doc=%s thread=%s job=%s] UNRECOVERABLE: could not persist failed '
                        'status (original error: %s | save error: %s). '
                        'Stale detection will recover the record after the threshold.',
                        document.id, thread_name, effective_job_id, exc, save_exc,
                    )

                if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                    raise exc
                return {'status': 'failed', 'document_id': document.id, 'error': str(exc)}

    finally:
        # Step 7: Unconditionally release this task from active tracking and close DB connections on exit.
        unregister_active_task(document_id, effective_job_id)
        db_connections.close_all()
        logger.debug(
            '[doc=%s thread=%s job=%s] DB connections released and task unregistered on thread exit.',
            document_id, thread_name, effective_job_id,
        )


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_document_task(self, document_id, languages=None, job_id=None):
    """
    Asynchronous task for end-to-end document processing.
    When running in eager mode (e.g. single-container Render free tier),
    dispatches in a background thread so the HTTP upload responds in <200ms
    and never hits reverse-proxy 502 timeouts.
    """
    effective_job_id = job_id or (self.request.id if hasattr(self, 'request') and self.request.id else uuid.uuid4().hex)
    register_active_task(document_id, effective_job_id, stage='queued')

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        t = threading.Thread(
            target=_execute_processing,
            args=(document_id, effective_job_id, languages),
            daemon=True,
        )
        t.start()
        return {'status': 'dispatched_thread', 'document_id': document_id, 'job_id': effective_job_id}

    return _execute_processing(
        document_id,
        effective_job_id,
        languages,
    )
