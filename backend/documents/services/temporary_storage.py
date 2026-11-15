"""Bounded retention for the public, no-account workflow."""
from datetime import timedelta
from django.conf import settings
from django.utils import timezone


def purge_expired_documents(hours=None):
    """Delete database rows and their private storage files after retention."""
    retention = hours if hours is not None else int(getattr(settings, 'TEMP_DOCUMENT_RETENTION_HOURS', 1))
    expired = __import__('documents.models', fromlist=['Document']).Document.objects.filter(
        created_at__lt=timezone.now() - timedelta(hours=retention)
    )
    count = 0
    for document in expired.iterator():
        for field in (document.uploaded_file, document.processed_file):
            if field:
                try: field.delete(save=False)
                except Exception: pass
        for export in document.exports.all():
            try: export.file.delete(save=False)
            except Exception: pass
        document.delete(); count += 1
    return count
