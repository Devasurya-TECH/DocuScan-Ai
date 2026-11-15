"""Safe DOCX text extraction; legacy binary .doc is intentionally not executed."""
from docx import Document as DocxDocument


def extract_docx_data(file_path):
    document = DocxDocument(str(file_path))
    pieces = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            pieces.append(paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                pieces.append(' | '.join(cells))
    return '\n'.join(pieces)
