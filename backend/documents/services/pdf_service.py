"""PDF renderers for original-position and clean semantic reconstruction plans."""

from pathlib import Path


def _font_size(block):
    return max(7, min(18, block.get('style', {}).get('font_size', 10)))


def _fitted_font_size(pdf, text, font_name, preferred_size, available_width):
    """Prevent a noisy OCR line from overflowing its reconstructed source block."""
    if not text or available_width <= 0:
        return preferred_size
    measured = pdf.stringWidth(text, font_name, preferred_size)
    if measured <= available_width:
        return preferred_size
    return max(5.5, preferred_size * available_width / measured)


def export_original_layout_pdf(reconstruction, destination):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    source = reconstruction['page']
    page_width, page_height = letter
    margin = 36
    scale = min((page_width - margin * 2) / source['width'], (page_height - margin * 2) / source['height'])
    draw_width, draw_height = source['width'] * scale, source['height'] * scale
    x_offset, y_offset = (page_width - draw_width) / 2, (page_height - draw_height) / 2
    pdf = canvas.Canvas(str(destination), pagesize=letter)
    for block in reconstruction['blocks']:
        if block['type'] == 'summary' or 'position' not in block:
            continue
        position = block['position']
        x = x_offset + position['x'] * draw_width
        y = y_offset + draw_height - (position['y'] * draw_height)
        font_name = 'Helvetica-Bold' if block['style'].get('font_weight') == 'bold' else 'Helvetica'
        preferred_size = _font_size(block)
        available_width = max(18, position['width'] * draw_width)
        if block['type'] == 'table':
            for row_index, row in enumerate(block['rows']):
                row_text = '    '.join(row)
                size = _fitted_font_size(pdf, row_text, font_name, preferred_size, available_width)
                pdf.setFont(font_name, size)
                pdf.drawString(x, y - row_index * (size + 3), row_text)
        else:
            for line_index, line in enumerate(block.get('text', '').splitlines() or ['']):
                size = _fitted_font_size(pdf, line, font_name, preferred_size, available_width)
                pdf.setFont(font_name, size)
                pdf.drawString(x, y - line_index * (size + 3), line)
    pdf.showPage()
    pdf.save()
    return Path(destination)


def export_clean_layout_pdf(reconstruction, destination):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body, heading = styles['BodyText'], styles['Heading2']
    story = [Paragraph(reconstruction['title'], styles['Title'])]
    for name, field in reconstruction['metadata'].items():
        story.append(Paragraph(f'<b>{name.replace("_", " ").title()}:</b> {field["value"]}', body))
    if reconstruction['metadata']:
        story.append(Spacer(1, 0.16 * inch))
    for block in reconstruction['content']:
        if block['type'] == 'heading':
            story.append(Paragraph(block['text'], heading))
        elif block['type'] == 'table':
            data = [block['columns']] + block['rows'] if block['columns'] else block['rows']
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D9D9D9')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.extend([Spacer(1, 0.1 * inch), table, Spacer(1, 0.12 * inch)])
        elif block.get('text'):
            story.append(Paragraph(block['text'].replace('\n', '<br/>'), body))
            story.append(Spacer(1, 0.08 * inch))
    if reconstruction['financial_summary']:
        data = [[name.replace('_', ' ').title(), str(field['value'])] for name, field in reconstruction['financial_summary'].items()]
        table = Table(data, hAlign='RIGHT')
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D9D9D9')), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')]))
        story.append(table)
    SimpleDocTemplate(str(destination), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.7 * inch, bottomMargin=0.7 * inch).build(story)
    return Path(destination)


def export_pdf(reconstruction, destination):
    if reconstruction['mode'] == 'original':
        return export_original_layout_pdf(reconstruction, destination)
    if reconstruction['mode'] == 'clean':
        return export_clean_layout_pdf(reconstruction, destination)
    raise ValueError('Unsupported reconstruction mode')
