"""Editable DOCX exporters built from the shared reconstruction plans."""

from pathlib import Path


def _set_table_borders(table):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = OxmlElement(f'w:{edge}')
        tag.set(qn('w:val'), 'single')
        tag.set(qn('w:sz'), '4')
        tag.set(qn('w:color'), 'D9D9D9')
        borders.append(tag)
    table._tbl.tblPr.append(borders)


def _add_table(document, columns, rows):
    table = document.add_table(rows=1, cols=max(1, len(columns)))
    table.style = 'Table Grid'
    headers = columns or [f'Column {index + 1}' for index in range(max(len(row) for row in rows))]
    for index, value in enumerate(headers):
        table.rows[0].cells[index].text = value.replace('_', ' ').title()
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            if index < len(cells):
                cells[index].text = str(value)
    _set_table_borders(table)
    return table


def export_clean_layout_docx(reconstruction, destination):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.7)
    section.left_margin = section.right_margin = Inches(0.75)
    title = document.add_paragraph(style='Title')
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run(reconstruction['title'])
    for name, field in reconstruction['metadata'].items():
        paragraph = document.add_paragraph()
        paragraph.add_run(f'{name.replace("_", " ").title()}: ').bold = True
        paragraph.add_run(str(field['value']))
    for block in reconstruction['content']:
        if block['type'] == 'heading':
            document.add_heading(block['text'], level=1)
        elif block['type'] == 'table':
            _add_table(document, block['columns'], block['rows'])
        elif block.get('text'):
            paragraph = document.add_paragraph()
            paragraph.add_run(block['text'])
            paragraph.paragraph_format.space_after = Pt(7)
    if reconstruction['financial_summary']:
        rows = [[name.replace('_', ' ').title(), str(field['value'])] for name, field in reconstruction['financial_summary'].items()]
        _add_table(document, ['Summary', 'Value'], rows)
    document.save(str(destination))
    return Path(destination)


def export_original_layout_docx(reconstruction, destination):
    """Create editable Word paragraphs/tables in source reading order.

    Word's normal flow layout cannot reproduce arbitrary OCR coordinates without
    using non-editable text boxes, so coordinates guide spacing but all content
    remains ordinary editable Word text and tables.
    """
    from docx import Document
    from docx.shared import Inches, Pt

    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.7)
    section.left_margin = section.right_margin = Inches(0.75)
    previous_y = 0.0
    for block in reconstruction['blocks']:
        if block['type'] == 'summary':
            continue
        if block['type'] == 'table':
            _add_table(document, block['columns'], block['rows'])
            continue
        position = block.get('position', {})
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(min(18, max(0, (position.get('y', 0) - previous_y) * 48)))
        run = paragraph.add_run(block.get('text', ''))
        run.font.size = Pt(block.get('style', {}).get('font_size', 11))
        run.bold = block.get('style', {}).get('font_weight') == 'bold'
        previous_y = position.get('y', previous_y)
    document.save(str(destination))
    return Path(destination)


def export_docx(reconstruction, destination):
    if reconstruction['mode'] == 'original':
        return export_original_layout_docx(reconstruction, destination)
    if reconstruction['mode'] == 'clean':
        return export_clean_layout_docx(reconstruction, destination)
    raise ValueError('Unsupported reconstruction mode')
