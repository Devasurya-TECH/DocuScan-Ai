import logging
import threading
from celery import shared_task
from django.conf import settings
from django.utils import timezone
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


def _execute_processing(document_id, job_id=None, languages=None):
    """Core execution logic for document processing with in-process concurrency guard."""
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error(f'Document {document_id} not found')
        return {'status': 'not_found', 'document_id': document_id}

    document.job_id = job_id or ''
    document.status = 'processing'
    document.progress_stage = 'starting'
    document.progress_percent = 10
    document.save(update_fields=['job_id', 'status', 'progress_stage', 'progress_percent', 'updated_at'])

    with OCR_SEMAPHORE:
        try:
            process_document(document, languages=languages)
            document.refresh_from_db()
            document.progress_stage = 'completed'
            document.progress_percent = 100
            document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])
            return {'status': 'completed', 'document_id': document.id}
        except Exception as exc:
            logger.exception(f'Error processing document {document.id}: {exc}')
            document.status = 'failed'
            document.progress_stage = 'failed'
            document.failure_reason = str(exc)[:1000]
            document.save(update_fields=['status', 'progress_stage', 'failure_reason', 'updated_at'])
            if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                raise exc
            return {'status': 'failed', 'document_id': document.id, 'error': str(exc)}


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_document_task(self, document_id, languages=None):
    """
    Asynchronous task for end-to-end document processing.
    When running in eager mode (e.g. single-container Render free tier),
    dispatches in a background thread so the HTTP upload responds in <200ms
    and never hits reverse-proxy 502 timeouts.
    """
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        t = threading.Thread(
            target=_execute_processing,
            args=(document_id, self.request.id if hasattr(self, 'request') else '', languages),
            daemon=True,
        )
        t.start()
        return {'status': 'dispatched_thread', 'document_id': document_id}

    return _execute_processing(
        document_id,
        self.request.id if hasattr(self, 'request') else '',
        languages,
    )
