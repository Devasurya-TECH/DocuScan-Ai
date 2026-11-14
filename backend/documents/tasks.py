import logging
from celery import shared_task
from django.utils import timezone
from .models import Document
from .services.document_processing import process_document

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_document_task(self, document_id, languages=None):
    """
    Asynchronous Celery task for end-to-end document processing.
    Updates processing stage and progress percentage on the document model.
    """
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error(f'Document {document_id} not found for task {self.request.id}')
        return {'status': 'not_found', 'document_id': document_id}

    document.job_id = self.request.id or ''
    document.status = 'processing'
    document.progress_stage = 'starting'
    document.progress_percent = 10
    document.save(update_fields=['job_id', 'status', 'progress_stage', 'progress_percent', 'updated_at'])

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
        raise exc
