"""
Document export service — TXT, DOCX (reconstructed layout), PDF (sandwich image+text overlay).

PDF export  : Sandwich PDF — the cropped/deskewed document image is drawn as the full-page
              background; every OCR word is drawn invisibly at its exact pixel position so
              the resulting file looks identical to the scan but supports text selection,
              copy, search and highlight.

DOCX export : Reconstructed DOCX — layout analysis groups words into headings, paragraphs
              and tables; python-docx inserts native Word elements (Heading styles, body
              paragraphs with tab-stop key-value pairs, and proper Table objects) so the
              exported Word document is fully editable while preserving the original
              column / grid structure.

TXT export  : Plain UTF-8 text dump of the latest human-corrected content.
"""

from __future__ import annotations

import io
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from django.core.files import File

# ── python-docx ──────────────────────────────────────────────────────────────
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor, Twips

# ── ReportLab (PDF) ───────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from ..models import DocumentExport


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def create_export(document, export_format: str, reconstruction_mode: str = 'clean'):
    """
    Export a completed document to TXT, DOCX, or PDF and persist as a
    ``DocumentExport`` record.  Returns the saved export object.
    """
    if document.status != 'completed':
        raise ValueError('Only completed documents can be exported.')
    if export_format not in {'pdf', 'docx', 'txt'}:
        raise ValueError("format must be 'pdf', 'docx', or 'txt'")

    effective_text: str = document.corrected_text or document.extracted_text or ''

    export = DocumentExport(
        document=document,
        export_format=export_format,
        reconstruction_mode=reconstruction_mode,
    )
    safe_stem = (
        Path(document.uploaded_file.name).stem
        if document.uploaded_file
        else f'document_{document.id}'
    )
    storage_filename = f'document_{document.id}/{safe_stem}.{export_format}'

    with NamedTemporaryFile(suffix=f'.{export_format}', delete=False) as tmp:
        local_path = Path(tmp.name)

    try:
        if export_format == 'txt':
            _build_txt(effective_text, local_path)

        elif export_format == 'docx':
            _build_reconstructed_docx(document, effective_text, local_path)

        elif export_format == 'pdf':
            _build_sandwich_pdf(document, effective_text, local_path)

        with local_path.open('rb') as generated:
            export.file.save(storage_filename, File(generated), save=False)
        export.save()

    finally:
        local_path.unlink(missing_ok=True)

    return export


# ─────────────────────────────────────────────────────────────────────────────
# TXT
# ─────────────────────────────────────────────────────────────────────────────

def _build_txt(text: str, path: Path) -> None:
    path.write_text(text, encoding='utf-8')


# ─────────────────────────────────────────────────────────────────────────────
# Sandwich PDF
# ─────────────────────────────────────────────────────────────────────────────

def _build_sandwich_pdf(document, fallback_text: str, path: Path) -> None:
    """
    Draw the document image as a full-page background, then overlay every OCR
    word at its exact bounding-box position using invisible (render mode 3) text.
    Falls back to a plain-text ReportLab PDF when no image or bounding boxes exist.
    """
    # ── 1. Resolve the best available image ──────────────────────────────────
    image_path: Path | None = None
    if document.processed_file:
        try:
            image_path = Path(document.processed_file.path)
            if not image_path.exists():
                image_path = None
        except Exception:
            image_path = None

    if image_path is None and document.uploaded_file:
        try:
            image_path = Path(document.uploaded_file.path)
            if not image_path.exists():
                image_path = None
        except Exception:
            image_path = None

    # ── 2. No image → plain-text fallback ────────────────────────────────────
    if image_path is None:
        _build_plain_pdf(fallback_text, path)
        return

    # ── 3. Measure image in pixels ───────────────────────────────────────────
    try:
        from PIL import Image as PilImage
        with PilImage.open(image_path) as pil_img:
            img_w_px, img_h_px = pil_img.size
    except Exception:
        _build_plain_pdf(fallback_text, path)
        return

    if img_w_px <= 0 or img_h_px <= 0:
        _build_plain_pdf(fallback_text, path)
        return

    # ── 4. Scale to A4 (preserve aspect ratio) ───────────────────────────────
    a4_w_pt, a4_h_pt = A4  # 595.27 × 841.89 pts
    scale = min(a4_w_pt / img_w_px, a4_h_pt / img_h_px)
    page_w_pt = img_w_px * scale
    page_h_pt = img_h_px * scale

    # px → pt conversion factor
    px_to_pt = scale  # 1 px = scale pts

    # ── 5. Create canvas ──────────────────────────────────────────────────────
    c = pdf_canvas.Canvas(str(path), pagesize=(page_w_pt, page_h_pt))

    # ── 6. Draw the image as background ──────────────────────────────────────
    # ReportLab Y-axis is bottom-up; image top-left maps to PDF (0, 0) only when
    # drawn at y=0 with height=page_h_pt (fills whole page).
    c.drawImage(
        str(image_path),
        x=0, y=0,
        width=page_w_pt, height=page_h_pt,
        preserveAspectRatio=False,
        mask='auto',
    )

    # ── 7. Overlay invisible text at bounding-box positions ───────────────────
    detections: list[dict[str, Any]] = document.ocr_results or []
    if detections:
        _draw_invisible_text_layer(c, detections, img_w_px, img_h_px, page_w_pt, page_h_pt, px_to_pt)
    else:
        # No bounding boxes — write visible text in a simple column so the PDF
        # still has selectable content (better than nothing).
        _draw_fallback_text_column(c, fallback_text, page_w_pt, page_h_pt)

    c.save()


def _draw_invisible_text_layer(
    c,
    detections: list[dict],
    img_w_px: float,
    img_h_px: float,
    page_w_pt: float,
    page_h_pt: float,
    px_to_pt: float,
) -> None:
    """
    For every OCR detection place a text object in render-mode 3 (invisible)
    at the matching page coordinate.  The font size is scaled to fit the
    bounding-box height so copy-pasted text has correct word spacing.
    """
    for det in detections:
        word_text: str = str(det.get('text') or '').strip()
        bbox = det.get('bounding_box') or []
        if not word_text or len(bbox) < 4:
            continue

        # Pixel coordinates of the top-left and bottom-right corners
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        x1_px, y1_px = min(xs), min(ys)   # top-left in image space
        x2_px, y2_px = max(xs), max(ys)   # bottom-right in image space
        box_h_px = max(1, y2_px - y1_px)
        box_w_px = max(1, x2_px - x1_px)

        # Convert to PDF points (PDF Y is bottom-up)
        x_pt = x1_px * px_to_pt
        # In PDF, y=0 is bottom of page; image y=0 is top of image
        y_pt = page_h_pt - (y2_px * px_to_pt)   # baseline ≈ bottom of bbox

        font_size = max(4.0, box_h_px * px_to_pt * 0.85)

        # Clamp width so text fits in the bbox
        char_count = max(1, len(word_text))
        available_w = box_w_px * px_to_pt
        # Rough: Helvetica char width ≈ 0.5 × font_size
        est_w = char_count * font_size * 0.5
        if est_w > available_w and est_w > 0:
            font_size = font_size * (available_w / est_w)
            font_size = max(4.0, font_size)

        try:
            t = c.beginText(x_pt, y_pt)
            t.setTextRenderMode(3)      # 3 = invisible (no fill, no stroke)
            t.setFont('Helvetica', font_size)
            t.textLine(word_text)
            c.drawText(t)
        except Exception:
            pass  # never crash export on a single bad word


def _draw_fallback_text_column(c, text: str, page_w_pt: float, page_h_pt: float) -> None:
    """Draw plain-black readable text when there are no bounding boxes."""
    margin = 36  # 0.5 inch
    font_size = 10
    leading = 14
    x = margin
    y = page_h_pt - margin - font_size

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', font_size)

    for line in text.split('\n'):
        if y < margin:
            c.showPage()
            y = page_h_pt - margin - font_size
            c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica', font_size)
        c.drawString(x, y, line[:200])  # truncate extremely long lines
        y -= leading


def _build_plain_pdf(text: str, path: Path) -> None:
    """ReportLab flowable PDF — used when there is no document image."""
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontSize = 10
    normal.leading = 14

    story = []
    for para in text.split('\n'):
        if para.strip():
            safe = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe, normal))
        else:
            story.append(Spacer(1, 0.08 * inch))

    if not story:
        story.append(Paragraph('No text extracted.', normal))

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
# Reconstructed DOCX
# ─────────────────────────────────────────────────────────────────────────────

def _build_reconstructed_docx(document, fallback_text: str, path: Path) -> None:
    """
    Build a DOCX that mirrors the original layout:
    - Headings for detected heading lines
    - Native Word Table objects for detected price/data tables
    - Tab-stop aligned key-value pairs for summary sections
    - Multi-column text wrapped in a two-column section (when detected)
    Falls back to a simple paragraph dump when layout data is absent.
    """
    layout: dict[str, Any] = {}
    if document.document_data and isinstance(document.document_data, dict):
        layout = document.document_data

    # If layout analysis ran and produced structured output use it;
    # otherwise run it now from raw ocr_results.
    if not layout.get('lines') and document.ocr_results:
        try:
            from .layout_analysis import analyse_layout
            layout = analyse_layout(document.ocr_results)
        except Exception:
            layout = {}

    doc = DocxDocument()

    # ── Default body font ─────────────────────────────────────────────────────
    _set_default_font(doc, 'Calibri', 11)

    if not layout.get('lines'):
        # Simple paragraph fallback
        _add_plain_paragraphs(doc, fallback_text)
        doc.save(str(path))
        return

    lines: list[dict] = layout.get('lines', [])
    paragraphs: list[dict] = layout.get('paragraphs', [])
    tables_data: list[dict] = layout.get('tables', [])
    sections_data: list[dict] = layout.get('sections', [])
    columns: list[dict] = layout.get('columns', [])
    reading_order: list[str] = layout.get('reading_order', [line['id'] for line in lines])
    header_line_ids: set[str] = set(layout.get('header_line_ids', []))
    footer_line_ids: set[str] = set(layout.get('footer_line_ids', []))

    # Build lookup maps
    line_by_id: dict[str, dict] = {ln['id']: ln for ln in lines}
    table_line_ids: set[str] = {lid for t in tables_data for lid in t.get('line_ids', [])}
    heading_line_ids: set[str] = set()
    for sec in sections_data:
        if sec.get('heading_line_id'):
            heading_line_ids.add(sec['heading_line_id'])

    # Paragraph lines lookup
    para_line_ids: dict[str, str] = {}  # line_id → paragraph_id
    for para in paragraphs:
        for lid in para.get('line_ids', []):
            para_line_ids[lid] = para['id']

    # ── Build doc in reading order ────────────────────────────────────────────
    emitted_table_ids: set[str] = set()
    emitted_line_ids: set[str] = set()

    for line_id in reading_order:
        line = line_by_id.get(line_id)
        if not line:
            continue
        if line_id in emitted_line_ids:
            continue

        # ── Header / footer — emit as smaller italic ──────────────────────────
        if line_id in header_line_ids or line_id in footer_line_ids:
            p = doc.add_paragraph()
            run = p.add_run(line['text'])
            run.font.size = Pt(8)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
            emitted_line_ids.add(line_id)
            continue

        # ── Heading ───────────────────────────────────────────────────────────
        if line_id in heading_line_ids:
            doc.add_heading(line['text'], level=1)
            emitted_line_ids.add(line_id)
            continue

        # ── Table ─────────────────────────────────────────────────────────────
        table_match = next(
            (t for t in tables_data if line_id in t.get('line_ids', []) and t['id'] not in emitted_table_ids),
            None,
        )
        if table_match:
            _add_table_block(doc, table_match)
            emitted_table_ids.add(table_match['id'])
            for lid in table_match.get('line_ids', []):
                emitted_line_ids.add(lid)
            continue

        # ── Regular line / key-value pair ─────────────────────────────────────
        if line_id in table_line_ids:
            emitted_line_ids.add(line_id)
            continue  # already handled above

        _add_line_paragraph(doc, line)
        emitted_line_ids.add(line_id)

    doc.save(str(path))


# ── DOCX helpers ──────────────────────────────────────────────────────────────

def _set_default_font(doc: DocxDocument, name: str, size_pt: int) -> None:
    style = doc.styles['Normal']
    style.font.name = name
    style.font.size = Pt(size_pt)


def _add_plain_paragraphs(doc: DocxDocument, text: str) -> None:
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
        else:
            doc.add_paragraph('')


def _add_table_block(doc: DocxDocument, table_data: dict) -> None:
    """Insert a native Word Table for a detected receipt/data table."""
    rows_data = table_data.get('rows', [])
    columns = table_data.get('columns', ['description', 'amount'])
    if not rows_data:
        return

    num_cols = len(columns)
    tbl = doc.add_table(rows=1, cols=num_cols)
    tbl.style = 'Table Grid'

    # Header row
    hdr_cells = tbl.rows[0].cells
    for col_idx, col_name in enumerate(columns):
        cell = hdr_cells[col_idx]
        cell.text = col_name.title()
        for run in cell.paragraphs[0].runs:
            run.font.bold = True

    # Data rows
    for row_data in rows_data:
        cells_data = row_data.get('cells', [])
        row_cells = tbl.add_row().cells
        for col_idx in range(num_cols):
            if col_idx < len(cells_data):
                row_cells[col_idx].text = cells_data[col_idx].get('text', '')
            else:
                row_cells[col_idx].text = ''

    # Add a blank paragraph after the table
    doc.add_paragraph('')


def _add_line_paragraph(doc: DocxDocument, line: dict) -> None:
    """
    Add a paragraph for a single OCR line.  Lines that look like key-value
    pairs (e.g. "Date: 12/01/2025") get a tab-stop so the value aligns
    with other values in the section.
    """
    text: str = line.get('text', '').strip()
    if not text:
        return

    elements: list[dict] = line.get('elements', [])
    # Detect key-value: exactly two spatially-separated elements where the
    # first ends with ':' or is a known label word.
    if len(elements) == 2:
        gap = (elements[1]['position']['x']
               - (elements[0]['position']['x'] + elements[0]['position']['width']))
        total_w = max(e['position']['x'] + e['position']['width'] for e in elements) - min(e['position']['x'] for e in elements)
        if gap > total_w * 0.15 or elements[0]['text'].rstrip().endswith(':'):
            p = doc.add_paragraph()
            p.paragraph_format.tab_stops.add_tab_stop(Inches(2.5))
            p.add_run(elements[0]['text'] + '\t')
            p.add_run(elements[1]['text'])
            return

    doc.add_paragraph(text)
