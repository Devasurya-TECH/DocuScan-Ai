"""
Deterministic, evidence-preserving document understanding.
Extracts structured document entities, table items, and semantic types
grounded in source OCR lines and bounding coordinates.
"""

import re

MONEY_PATTERN = re.compile(r'(?P<currency>[$€£₹]|USD|EUR|GBP|INR|Rs\.?)\s?(?P<amount>\d{1,3}(?:,\d{3})*\.\d{2})', re.IGNORECASE)
BARE_AMOUNT_PATTERN = re.compile(r'(?P<amount>\d{1,3}(?:,\d{3})*\.\d{2})')

# Supports both spelled-out dates (e.g., 24 May 2024, May 24, 2024) and numeric dates (2024-05-24, 24/05/2024, 05/24/2024)
DATE_PATTERNS = [
    re.compile(
        r'\b(?:0?[1-9]|[12]\d|3[01])[-/\s]+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[-/\s,]+(?:19|20)\d{2}\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[-/\s]+(?:0?[1-9]|[12]\d|3[01])[-/\s,]+(?:19|20)\d{2}\b',
        re.IGNORECASE,
    ),
    re.compile(r'\b(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b'),  # YYYY-MM-DD
    re.compile(r'\b(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:19|20)?\d{2}\b'),   # DD/MM/YYYY or DD/MM/YY
]

INVOICE_PATTERN = re.compile(r'\b(?:tax\s+)?(?:invoice|bill|inv\.?)(?:\s*(?:no|number|#|:|-))?\s*([A-Z0-9\-\/]{3,})\b', re.IGNORECASE)
RECEIPT_PATTERN = re.compile(r'\b(?:receipt|order|sale|trans(?:action)?)(?:\s*(?:no|number|#|:|-))?\s*([A-Z0-9\-\/]{3,})\b', re.IGNORECASE)

TOTAL_KEYWORDS = {
    'subtotal': re.compile(r'\b(?:sub\s*total|net\s*amount)\b', re.IGNORECASE),
    'tax': re.compile(r'\b(?:tax|vat|gst|cgst|sgst|sales\s*tax)\b', re.IGNORECASE),
    'discount': re.compile(r'\b(?:discount|savings?|rebate)\b', re.IGNORECASE),
    'total': re.compile(r'\b(?:grand\s*)?(?:total|balance\s*due|amount\s*payable|amount\s*due)\b', re.IGNORECASE),
}


def _field(value=None, source_line_ids=None, confidence=0.0, needs_review=True):
    return {
        'value': value,
        'source_line_ids': source_line_ids or [],
        'confidence': round(float(confidence), 4),
        'needs_review': needs_review,
    }


def _line_money(line):
    match = MONEY_PATTERN.search(line['text'])
    if not match:
        match = BARE_AMOUNT_PATTERN.search(line['text'])
    if not match:
        return None
    curr = match.groupdict().get('currency')
    if curr:
        curr = curr.strip()
    return {
        'amount': float(match.group('amount').replace(',', '')),
        'currency': curr,
        'source_line_id': line['id'],
        'confidence': line['confidence'],
    }


def _find_keyword_amount(lines, keyword):
    for line in lines:
        if TOTAL_KEYWORDS[keyword].search(line['text']):
            money = _line_money(line)
            if money:
                return money
    return None


def classify_document(layout):
    """
    Classify document type using structured layout cues, vocabulary, and script metadata.
    """
    text = ' '.join(line['text'] for line in layout.get('lines', [])).lower()
    
    # Check if elements are tagged as handwritten
    handwritten_count = sum(1 for el in layout.get('elements', []) if el.get('region_type') == 'handwritten_text')
    if handwritten_count > len(layout.get('elements', [])) * 0.4 and len(layout.get('elements', [])) > 0:
        return {'type': 'handwritten_note', 'confidence': 0.85, 'needs_review': False}
        
    score = 0.0
    if re.search(r'\breceipt\b', text):
        score += 0.55
    if re.search(r'\b(?:subtotal|tax|cashier|terminal|store\s*#)\b', text):
        score += 0.25
    if layout.get('tables'):
        score += 0.15
        
    if re.search(r'\b(?:tax\s+)?invoice\b|\bbill\s+to\b|\bdue\s+date\b', text):
        return {'type': 'invoice', 'confidence': round(max(score, 0.8), 4), 'needs_review': False}
    if score >= 0.5:
        return {'type': 'receipt', 'confidence': round(score, 4), 'needs_review': False}
    if re.search(r'\b(?:application|registration|form|signature|applicant|declaration)\b', text):
        return {'type': 'printed_form', 'confidence': 0.75, 'needs_review': False}
        
    return {'type': 'general_printed_document', 'confidence': round(score, 4), 'needs_review': score > 0}


def _vendor(layout, document_type):
    if document_type not in {'receipt', 'invoice'}:
        return _field()
    candidates = []
    for line in layout.get('lines', [])[:5]:
        text = line['text'].strip()
        alpha = ''.join(character for character in text if character.isalpha())
        if len(alpha) >= 3 and not re.search(r'\b(receipt|invoice|tax|total|date|phone|ph|tel|address|road|st|street)\b', text, re.IGNORECASE):
            upper_ratio = sum(character.isupper() for character in alpha) / len(alpha)
            if upper_ratio >= 0.50:
                candidates.append(line)
    if not candidates:
        return _field()
    line = candidates[0]
    return _field(line['text'], [line['id']], line['confidence'], line['confidence'] < 0.85)


def _identifier(lines, pattern):
    for line in lines:
        match = pattern.search(line['text'])
        if match and match.group(1):
            return _field(match.group(1), [line['id']], line['confidence'], line['confidence'] < 0.85)
    return _field()


def _date(lines):
    for line in lines:
        for pat in DATE_PATTERNS:
            match = pat.search(line['text'])
            if match:
                return _field(match.group(0), [line['id']], line['confidence'], line['confidence'] < 0.85)
    return _field()


def _financial_field(lines, key):
    found = _find_keyword_amount(lines, key)
    if not found:
        return _field()
    return _field(found['amount'], [found['source_line_id']], found['confidence'], found['confidence'] < 0.85)


def _currency(lines):
    for line in lines:
        found = _line_money(line)
        if found and found['currency']:
            return _field(found['currency'], [found['source_line_id']], found['confidence'], found['confidence'] < 0.85)
    return _field()


def _items(layout):
    """
    Extract line items from detected table rows, preserving columns and cell values.
    """
    items = []
    for table in layout.get('tables', []):
        for row in table['rows']:
            cells = row['cells']
            if len(cells) == 2:
                items.append({
                    'description': cells[0]['text'],
                    'amount': cells[1]['text'],
                    'source_line_id': row['line_id'],
                    'needs_review': True,
                })
            elif len(cells) > 2:
                items.append({
                    'description': cells[0]['text'],
                    'quantity': cells[1]['text'] if len(cells) >= 3 else '',
                    'unit_price': cells[2]['text'] if len(cells) >= 4 else '',
                    'amount': cells[-1]['text'],
                    'source_line_id': row['line_id'],
                    'needs_review': True,
                })
    return items


def understand_document(layout):
    """
    Extract transparent document-understanding schema from analyzed layout.
    """
    lines = layout.get('lines', [])
    classification = classify_document(layout)
    document_type = classification['type']
    
    fields = {
        'vendor': _vendor(layout, document_type),
        'date': _date(lines),
        'invoice_number': _identifier(lines, INVOICE_PATTERN),
        'receipt_number': _identifier(lines, RECEIPT_PATTERN),
        'subtotal': _financial_field(lines, 'subtotal'),
        'tax': _financial_field(lines, 'tax'),
        'discount': _financial_field(lines, 'discount'),
        'total': _financial_field(lines, 'total'),
        'currency': _currency(lines),
    }
    
    missing_required = [name for name in ('vendor', 'total') if fields[name]['value'] is None]
    
    return {
        'version': 1,
        'document_type': classification,
        'fields': fields,
        'items': _items(layout),
        'review_flags': (
            ([f'{name}_not_found' for name in missing_required] if document_type in {'receipt', 'invoice'} else [])
            + (['no_reliable_item_table'] if document_type in {'receipt', 'invoice'} and not layout.get('tables') else [])
        ),
    }
