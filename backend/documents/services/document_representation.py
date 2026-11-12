"""Build the shared, editable representation used by reconstruction/export work."""

from .document_understanding import understand_document
from .layout_analysis import analyse_layout


def _normalised_position(position, page):
    width, height = max(page['width'], 1), max(page['height'], 1)
    return {
        'x': round(position['x'] / width, 6),
        'y': round(position['y'] / height, 6),
        'width': round(position['width'] / width, 6),
        'height': round(position['height'] / height, 6),
    }


def _block(block_type, text, position, page, confidence, source_line_ids, **extra):
    return {
        'type': block_type,
        'text': text,
        'position': _normalised_position(position, page),
        'source_position': position,
        'confidence': round(float(confidence), 6),
        'source_line_ids': source_line_ids,
        **extra,
    }


def validate_representation(representation):
    """Validate our JSON contract without adding a schema dependency."""
    if not isinstance(representation, dict) or representation.get('version') != 1:
        raise ValueError('document representation must have version 1')
    page = representation.get('page')
    if not isinstance(page, dict) or page.get('width', 0) <= 0 or page.get('height', 0) <= 0:
        raise ValueError('document representation requires positive page dimensions')
    if not isinstance(representation.get('blocks'), list):
        raise ValueError('document representation requires blocks')
    for block in representation['blocks']:
        if block.get('type') not in {'heading', 'paragraph', 'table', 'summary', 'text'}:
            raise ValueError('document representation contains an unsupported block type')
        if block['type'] != 'summary':
            position = block.get('position')
            if not isinstance(position, dict) or any(key not in position for key in ('x', 'y', 'width', 'height')):
                raise ValueError('positioned blocks require normalized coordinates')
    return representation


def build_document_representation(detections, page_width=None, page_height=None):
    """Convert OCR detections to the normalized representation for all renderers."""
    layout = analyse_layout(detections, page_width, page_height)
    page = layout['page']
    understanding = understand_document(layout)
    lines_by_id = {line['id']: line for line in layout['lines']}
    heading_ids = {section['heading_line_id'] for section in layout['sections']}
    table_line_ids = {line_id for table in layout['tables'] for line_id in table['line_ids']}
    paragraph_line_ids = {line_id for paragraph in layout['paragraphs'] for line_id in paragraph['line_ids']}
    blocks = []

    for line_id in heading_ids:
        line = lines_by_id[line_id]
        blocks.append(_block('heading', line['text'], line['position'], page, line['confidence'], [line_id]))
    for paragraph in layout['paragraphs']:
        blocks.append(_block('paragraph', paragraph['text'], paragraph['position'], page, paragraph['confidence'], paragraph['line_ids']))
    for table in layout['tables']:
        rows = [[cell['text'] for cell in row['cells']] for row in table['rows']]
        blocks.append(_block(
            'table', '', table['position'], page, 0.0, table['line_ids'],
            columns=table['columns'], rows=rows,
        ))
    for line in layout['lines']:
        if line['id'] not in heading_ids | table_line_ids | paragraph_line_ids:
            blocks.append(_block('text', line['text'], line['position'], page, line['confidence'], [line['id']]))

    fields = {name: value for name, value in understanding['fields'].items() if value['value'] is not None}
    if fields:
        blocks.append({
            'type': 'summary',
            'fields': fields,
            'items': understanding['items'],
            'review_flags': understanding['review_flags'],
        })
    blocks.sort(key=lambda block: block.get('source_position', {}).get('y', float('inf')))
    return validate_representation({
        'version': 1,
        'document_type': understanding['document_type'],
        'page': page,
        'reading_order': layout['reading_order'],
        'blocks': blocks,
        'layout': {
            'columns': layout['columns'],
            'header_line_ids': layout['header_line_ids'],
            'footer_line_ids': layout['footer_line_ids'],
            'sections': layout['sections'],
        },
        'review_flags': understanding['review_flags'],
    })
