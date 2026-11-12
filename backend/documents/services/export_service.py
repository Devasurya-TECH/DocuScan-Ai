"""Store PDF/DOCX exports generated from a document's saved representation."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.files import File

from ..models import DocumentExport
from .docx_service import export_docx
from .pdf_service import export_pdf
from .reconstruction_service import reconstruct_document


def create_export(document, export_format, reconstruction_mode):
    if document.status != 'completed' or not document.document_data:
        raise ValueError('Only completed documents with a saved representation can be exported.')
    if export_format not in {'pdf', 'docx'}:
        raise ValueError("format must be 'pdf' or 'docx'")

    reconstruction = reconstruct_document(document.document_data, reconstruction_mode)
    export = DocumentExport(document=document, export_format=export_format, reconstruction_mode=reconstruction_mode)
    filename = f'document_{document.id}/{reconstruction_mode}_layout.{export_format}'
    with NamedTemporaryFile(suffix=f'.{export_format}', delete=False) as temporary:
        local_path = Path(temporary.name)
    try:
        if export_format == 'pdf':
            export_pdf(reconstruction, local_path)
        else:
            export_docx(reconstruction, local_path)
        with local_path.open('rb') as generated:
            export.file.save(filename, File(generated), save=False)
        export.save()
    finally:
        local_path.unlink(missing_ok=True)
    return export
