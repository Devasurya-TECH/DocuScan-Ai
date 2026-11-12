"""Editable reconstruction plans derived from the shared document representation.

This module produces renderer-neutral JSON, not a PDF/DOCX. Keeping it separate
lets both export services render the same reconstructed structure later.
"""

from .document_representation import validate_representation


def _style_for(block):
    block_type = block['type']
    if block_type == 'heading':
        return {'font_size': 18, 'font_weight': 'bold', 'align': 'left'}
    if block_type == 'table':
        return {'font_size': 10, 'font_weight': 'normal', 'borders': 'rows'}
    if block_type == 'summary':
        return {'font_size': 11, 'font_weight': 'bold', 'align': 'right'}
    return {'font_size': 11, 'font_weight': 'normal', 'align': 'left'}


def reconstruct_original_layout(representation):
    """Preserve semantic blocks and their normalised source positions.

    It is deliberately approximate: OCR positions are geometric clues, not an
    assertion of pixel-perfect or font-perfect recovery from a photograph.
    """
    validate_representation(representation)
    blocks = []
    for index, block in enumerate(representation['blocks']):
        reconstructed = {
            'id': f'original_{index}',
            'type': block['type'],
            'editable': block['type'] != 'summary',
            'style': _style_for(block),
            'confidence': block.get('confidence'),
            'source_line_ids': block.get('source_line_ids', []),
        }
        if block['type'] == 'summary':
            reconstructed['fields'] = block['fields']
            reconstructed['items'] = block.get('items', [])
            reconstructed['review_flags'] = block.get('review_flags', [])
        else:
            reconstructed['text'] = block.get('text', '')
            reconstructed['position'] = block['position']
            reconstructed['source_position'] = block['source_position']
            if block['type'] == 'table':
                reconstructed['columns'] = block['columns']
                reconstructed['rows'] = block['rows']
        blocks.append(reconstructed)
    return {
        'version': 1,
        'mode': 'original',
        'document_type': representation['document_type'],
        'page': representation['page'],
        'blocks': blocks,
        'limitations': [
            'Positions and spacing are reconstructed from OCR geometry.',
            'Original fonts, photographs, borders, and decorative elements are not guaranteed to be recovered.',
        ],
    }


def reconstruct_clean_layout(representation):
    """Produce a semantic, readable document plan instead of coordinate placement."""
    validate_representation(representation)
    summary = next((block for block in representation['blocks'] if block['type'] == 'summary'), None)
    fields = summary['fields'] if summary else {}
    document_type = representation['document_type']['type']
    title = fields.get('vendor', {}).get('value') or document_type.replace('_', ' ').title()
    metadata_names = ('date', 'invoice_number', 'receipt_number')
    metadata = {name: fields[name] for name in metadata_names if name in fields}
    content = []
    for block in representation['blocks']:
        if block['type'] == 'summary':
            continue
        if block['type'] == 'heading' and block.get('text') == title:
            continue
        content.append({
            'type': block['type'],
            'text': block.get('text', ''),
            'columns': block.get('columns', []),
            'rows': block.get('rows', []),
            'confidence': block.get('confidence'),
            'source_line_ids': block.get('source_line_ids', []),
        })
    financial_summary = {
        name: fields[name]
        for name in ('subtotal', 'tax', 'discount', 'total', 'currency')
        if name in fields
    }
    return {
        'version': 1,
        'mode': 'clean',
        'document_type': representation['document_type'],
        'title': title,
        'metadata': metadata,
        'content': content,
        'items': summary.get('items', []) if summary else [],
        'financial_summary': financial_summary,
        'review_flags': representation.get('review_flags', []),
        'limitations': [
            'Clean layout optimises semantic readability rather than preserving original pixel placement.',
            'Fields flagged for review should be verified before the document is relied upon.',
        ],
    }


def reconstruct_document(representation, mode):
    if mode == 'original':
        return reconstruct_original_layout(representation)
    if mode == 'clean':
        return reconstruct_clean_layout(representation)
    raise ValueError("reconstruction mode must be 'original' or 'clean'")
