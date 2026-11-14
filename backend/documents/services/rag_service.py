"""
Evidence-grounded Document Question Answering (RAG) service.
Answers user queries grounded strictly in OCR-extracted text and structured metadata,
returning exact source bounding boxes and evidence citations.
"""

import re
from typing import Dict, Any, List


def _tokenize(text: str) -> List[str]:
    return [word.lower() for word in re.findall(r'\b\w+\b', text or '') if len(word) > 1]


def _score_chunk(chunk_tokens: List[str], query_tokens: List[str]) -> float:
    if not chunk_tokens or not query_tokens:
        return 0.0
    matches = sum(1 for q in query_tokens if q in chunk_tokens)
    return matches / len(query_tokens)


def answer_document_question(document, question: str) -> Dict[str, Any]:
    """
    Answers a query about a document using retrieval over its OCR blocks and structured fields.
    Returns:
        {
            "question": str,
            "answer": str,
            "grounded": bool,
            "confidence": float,
            "sources": List[dict]
        }
    """
    clean_question = (question or '').strip()
    if not clean_question:
        raise ValueError("Question cannot be empty.")

    q_lower = clean_question.lower()
    q_tokens = _tokenize(q_lower)

    doc_data = document.document_data or {}
    fields = doc_data.get('fields') or {}
    lines = []
    
    # Extract lines with coordinates
    for block in doc_data.get('blocks', []):
        if block.get('type') in ('heading', 'paragraph', 'text'):
            lines.append({
                'text': block.get('text', ''),
                'bounding_box': block.get('source_position') or block.get('position'),
                'source_line_ids': block.get('source_line_ids', []),
                'confidence': block.get('confidence', 0.9),
            })
    
    # Also index structured fields
    structured_answers = {}
    if 'total' in q_lower or 'amount' in q_lower or 'pay' in q_lower:
        val = fields.get('total', {}).get('value')
        curr = fields.get('currency', {}).get('value') or ''
        if val is not None:
            structured_answers['total'] = f"The total amount is {curr}{val}."

    if 'vendor' in q_lower or 'merchant' in q_lower or 'seller' in q_lower or 'store' in q_lower or 'who' in q_lower:
        val = fields.get('vendor', {}).get('value')
        if val:
            structured_answers['vendor'] = f"The vendor / merchant is {val}."

    if 'date' in q_lower or 'when' in q_lower:
        val = fields.get('date', {}).get('value')
        if val:
            structured_answers['date'] = f"The document date is {val}."

    if 'tax' in q_lower or 'vat' in q_lower or 'gst' in q_lower:
        val = fields.get('tax', {}).get('value')
        curr = fields.get('currency', {}).get('value') or ''
        if val is not None:
            structured_answers['tax'] = f"The tax amount is {curr}{val}."

    if 'invoice' in q_lower or 'number' in q_lower or 'id' in q_lower:
        inv = fields.get('invoice_number', {}).get('value')
        rec = fields.get('receipt_number', {}).get('value')
        if inv:
            structured_answers['invoice_number'] = f"The invoice number is {inv}."
        elif rec:
            structured_answers['receipt_number'] = f"The receipt number is {rec}."

    if 'items' in q_lower or 'purchased' in q_lower or 'bought' in q_lower:
        items = doc_data.get('items') or []
        if items:
            item_desc = ', '.join([f"{item.get('description', '')} ({item.get('amount', '')})" for item in items[:5]])
            structured_answers['items'] = f"Purchased items include: {item_desc}."

    # Direct match from structured fields
    for key, ans in structured_answers.items():
        entry = {
            'question': clean_question,
            'answer': ans,
            'grounded': True,
            'confidence': 0.95,
            'sources': [{'type': 'structured_field', 'field': key}],
        }
        _record_qa(document, entry)
        return entry

    # Contextual passage retrieval over lines
    scored_lines = []
    for line in lines:
        line_tokens = _tokenize(line['text'])
        score = _score_chunk(line_tokens, q_tokens)
        if score > 0:
            scored_lines.append((score, line))

    scored_lines.sort(key=lambda x: x[0], reverse=True)

    if scored_lines and scored_lines[0][0] >= 0.25:
        top_matches = [line for score, line in scored_lines[:3]]
        combined_text = ' '.join(m['text'] for m in top_matches)
        entry = {
            'question': clean_question,
            'answer': f"Based on the document: \"{combined_text}\"",
            'grounded': True,
            'confidence': round(float(scored_lines[0][0]), 2),
            'sources': [
                {
                    'text': m['text'],
                    'bounding_box': m['bounding_box'],
                    'confidence': m['confidence'],
                }
                for m in top_matches
            ],
        }
        _record_qa(document, entry)
        return entry

    # Fallback if no relevant fact is found
    entry = {
        'question': clean_question,
        'answer': "The document does not contain clear information to answer this question.",
        'grounded': False,
        'confidence': 0.0,
        'sources': [],
    }
    _record_qa(document, entry)
    return entry


def _record_qa(document, entry):
    history = list(document.qa_history or [])
    history.append(entry)
    document.qa_history = history[-20:]  # Keep latest 20 Q&A records
    document.save(update_fields=['qa_history', 'updated_at'])
