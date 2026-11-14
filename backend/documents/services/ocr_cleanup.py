"""OCR Text Cleanup & Spell Correction Service

Provides heuristic OCR noise artifact removal, stray token stripping,
and dictionary-guided spelling correction for document text.
"""

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Extended dictionary of common document, invoice, business, and tech vocabulary
DOCUMENT_VOCABULARY = [
    'brain', 'invoice', 'receipt', 'subtotal', 'total', 'amount', 'balance',
    'customer', 'vendor', 'merchant', 'description', 'quantity', 'payment',
    'credit', 'debit', 'account', 'address', 'phone', 'email', 'website',
    'date', 'number', 'order', 'discount', 'tax', 'vat', 'gst', 'docuscan',
    'document', 'statement', 'bill', 'billing', 'shipping', 'service',
    'item', 'items', 'price', 'unit', 'currency', 'cashier', 'terminal',
    'transaction', 'approved', 'declined', 'signature', 'authorized',
    'thank', 'welcome', 'patient', 'hospital', 'clinic', 'report',
    'summary', 'medical', 'prescription', 'diagnosis', 'treatment'
]

# Lazy-loaded spell checker singleton
_spell_checker = None


def get_spell_checker():
    global _spell_checker
    if _spell_checker is None:
        try:
            from spellchecker import SpellChecker
            _spell_checker = SpellChecker()
            _spell_checker.word_frequency.load_words(DOCUMENT_VOCABULARY)
        except Exception as exc:
            logger.warning(f"Could not load SpellChecker: {exc}")
            _spell_checker = False
    return _spell_checker if _spell_checker else None


def clean_ocr_artifacts(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Strip common OCR noise artifacts, stray trailing tokens, and formatting glitches."""
    changes = []
    cleaned = text

    # 1. Strip noise suffixes like "brain st", "total s" when "st" is a stray noise token
    # Matches words with >=3 letters followed by an isolated noise suffix (st, nd, rd, th, s, t, x, .s, .t)
    # when not preceded by digits (to preserve 1st, 2nd, etc.)
    noise_suffix_pattern = r'\b([A-Za-z]{3,})\s+(st|nd|rd|th|s|t|x|\.s|\.t)\b(?!\s*\d)'
    
    def replace_noise_suffix(match):
        full = match.group(0)
        base = match.group(1)
        suffix = match.group(2)
        # Check if the suffix is an English word like "st" for "street" or noise
        # If followed by a comma or capital, or word is e.g. "brain st"
        if suffix.lower() in ('s', 't', 'x', '.s', '.t', 'st', 'nd', 'rd', 'th'):
            changes.append({
                'original': full,
                'replacement': base,
                'type': 'noise_suffix_removed'
            })
            return base
        return full

    cleaned = re.sub(noise_suffix_pattern, replace_noise_suffix, cleaned)

    # 2. Fix hyphenated word breaks across lines (e.g. "docu-\nment" -> "document")
    def replace_hyphen_break(match):
        w1, w2 = match.group(1), match.group(2)
        combined = f"{w1}{w2}"
        changes.append({
            'original': match.group(0),
            'replacement': combined,
            'type': 'hyphenation_merged'
        })
        return combined

    cleaned = re.sub(r'\b([A-Za-z]+)-\s*\n\s*([A-Za-z]+)\b', replace_hyphen_break, cleaned)

    # 3. Clean orphaned punctuation before punctuation (e.g. "word ," -> "word,")
    cleaned = re.sub(r'\s+([,.:;?!])', r'\1', cleaned)

    # 4. Clean stray OCR pipe or tilde artifacts (e.g. " | word " -> " word ")
    cleaned = re.sub(r'(?<=\s)[|~^`_](?=\s)', '', cleaned)

    # 5. Normalize space between currency symbols and digits (e.g. "$ 12 . 50" -> "$12.50")
    cleaned = re.sub(r'([$€£₹¥])\s+(\d)', r'\1\2', cleaned)
    cleaned = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', cleaned)

    # 6. Normalize multiple horizontal spaces
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

    return cleaned, changes


def match_capitalization(original: str, replacement: str) -> str:
    """Preserve titlecase or uppercase styling from original token."""
    if original.isupper():
        return replacement.upper()
    if original.istitle():
        return replacement.capitalize()
    return replacement.lower()


def correct_spelling(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Identify misspelled words and replace them with high-confidence dictionary corrections."""
    spell = get_spell_checker()
    if not spell:
        return text, []

    changes = []
    lines = text.split('\n')
    corrected_lines = []

    # Common OCR misrecognized word pairs mapping directly
    DIRECT_CORRECTIONS = {
        'invoce': 'invoice',
        'reciept': 'receipt',
        'amout': 'amount',
        'descrption': 'description',
        'subtotl': 'subtotal',
        't0tal': 'total',
        'tota1': 'total',
        'totai': 'total',
        'phne': 'phone',
        'qunty': 'quantity',
        'custmer': 'customer',
        'adrs': 'address',
        'addr': 'address',
        'balnce': 'balance',
    }

    for line in lines:
        words = re.findall(r'\b[A-Za-z]+\b|\d+|[^\w\s]|\s+', line)
        line_out = []
        for token in words:
            # If purely alphabetic and length >= 3
            if token.isalpha() and len(token) >= 3:
                lower = token.lower()
                
                # Check direct mapping first
                if lower in DIRECT_CORRECTIONS:
                    fixed = match_capitalization(token, DIRECT_CORRECTIONS[lower])
                    changes.append({
                        'original': token,
                        'replacement': fixed,
                        'type': 'spelling_direct'
                    })
                    line_out.append(fixed)
                    continue

                # Check if word is known
                if lower in spell:
                    line_out.append(token)
                    continue

                # If word is unknown, attempt suggestion
                # Don't touch all-caps acronyms like USD, SKU, ISBN, etc.
                if token.isupper() and len(token) <= 4:
                    line_out.append(token)
                    continue

                suggestion = spell.correction(lower)
                if suggestion and suggestion != lower:
                    # Only accept if edit distance is small (<= 2)
                    fixed = match_capitalization(token, suggestion)
                    changes.append({
                        'original': token,
                        'replacement': fixed,
                        'type': 'spelling_suggested'
                    })
                    line_out.append(fixed)
                else:
                    line_out.append(token)
            else:
                line_out.append(token)

        corrected_lines.append(''.join(line_out))

    return '\n'.join(corrected_lines), changes


def autocorrect_text(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Execute complete OCR artifact cleaning followed by spelling correction."""
    if not text:
        return text, []

    cleaned_text, artifact_changes = clean_ocr_artifacts(text)
    final_text, spelling_changes = correct_spelling(cleaned_text)

    all_changes = artifact_changes + spelling_changes
    return final_text, all_changes
