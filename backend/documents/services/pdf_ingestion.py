"""
Multi-page PDF document ingestion service using pypdf.
Extracts pages, text blocks, embedded images, and page-level metadata.
"""

import os
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
import numpy as np


def is_pdf(file_path):
    return str(file_path).lower().endswith('.pdf')


def extract_pdf_data(file_path):
    """
    Reads a multi-page PDF document, extracting page text and embedded images.
    Returns:
        total_pages (int), pages_data (list of dicts)
    """
    reader = PdfReader(str(file_path))
    if reader.is_encrypted:
        try:
            if reader.decrypt('') == 0:
                raise ValueError('Password-protected PDFs cannot be processed.')
        except Exception as exc:
            raise ValueError('Password-protected PDFs cannot be processed.') from exc
    total_pages = len(reader.pages)
    pages = []

    for index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ''
        images_found = []
        
        # Extract embedded images on this page if present
        try:
            for img_idx, img_obj in enumerate(page.images):
                img_name = f'page_{index + 1}_img_{img_idx + 1}.png'
                images_found.append({
                    'name': img_name,
                    'data': img_obj.data,
                })
        except Exception:
            pass

        pages.append({
            'page_number': index + 1,
            'text': page_text,
            'image_count': len(images_found),
            'has_embedded_images': len(images_found) > 0,
        })

    return total_pages, pages


def render_pdf_page(file_path, page_index, scale=1.5):
    """Render one scanned PDF page at a time, avoiding an entire-PDF memory spike."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ValueError('Scanned PDF support requires pypdfium2.') from exc
    pdf = pdfium.PdfDocument(str(file_path))
    try:
        page = pdf[page_index]
        try:
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            return np.array(pil.convert('RGB'))[:, :, ::-1].copy()
        finally:
            page.close()
    finally:
        pdf.close()
