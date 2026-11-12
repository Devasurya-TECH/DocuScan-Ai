"""Human-in-the-loop corrections for OCR-derived document data."""

from copy import deepcopy


VERIFIABLE_FIELDS = {
    'vendor', 'date', 'invoice_number', 'receipt_number', 'subtotal',
    'tax', 'discount', 'total', 'currency',
}


def apply_human_correction(document, corrected_text=None, verified_fields=None):
    """Persist user-verified values without replacing unverified OCR evidence."""
    representation = deepcopy(document.document_data or {})
    corrections = representation.setdefault('human_corrections', {})

    if corrected_text is not None:
        document.corrected_text = corrected_text
        corrections['corrected_text'] = corrected_text

    if verified_fields:
        summary = next(
            (block for block in representation.get('blocks', []) if block.get('type') == 'summary'),
            None,
        )
        if summary is None:
            summary = {'type': 'summary', 'fields': {}, 'items': [], 'review_flags': []}
            representation.setdefault('blocks', []).append(summary)
        fields = summary.setdefault('fields', {})
        verified = corrections.setdefault('verified_fields', {})
        for name, value in verified_fields.items():
            if name not in VERIFIABLE_FIELDS:
                raise ValueError(f'Unsupported verified field: {name}')
            fields[name] = {
                'value': value,
                'source_line_ids': [],
                'confidence': 1.0,
                'needs_review': False,
                'verified_by_user': True,
            }
            verified[name] = value

    document.document_data = representation
    document.save(update_fields=['corrected_text', 'document_data', 'updated_at'])
    return document
