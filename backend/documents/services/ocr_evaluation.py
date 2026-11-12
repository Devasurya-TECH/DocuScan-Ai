"""Ground-truth OCR evaluation utilities.

Confidence is a model signal, not a measure of transcription accuracy. These
functions intentionally require a supplied reference transcription before
reporting Character Error Rate (CER) or Word Error Rate (WER).
"""

import re


def normalize_text(value):
    """Normalise whitespace and case for repeatable OCR benchmark comparisons."""
    return re.sub(r'\s+', ' ', value or '').strip().lower()


def levenshtein_distance(reference, hypothesis):
    """Return the edit distance without requiring an additional package."""
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference

    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_item in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
            current.append(min(
                current[-1] + 1,
                previous[hypothesis_index] + 1,
                previous[hypothesis_index - 1] + (reference_item != hypothesis_item),
            ))
        previous = current
    return previous[-1]


def error_rate(reference, hypothesis, unit='character'):
    """Calculate CER or WER from known ground truth, returning ``None`` if absent."""
    reference_text = normalize_text(reference)
    hypothesis_text = normalize_text(hypothesis)
    if not reference_text:
        return None

    if unit == 'word':
        reference_units = reference_text.split()
        hypothesis_units = hypothesis_text.split()
    elif unit == 'character':
        reference_units = list(reference_text)
        hypothesis_units = list(hypothesis_text)
    else:
        raise ValueError("unit must be 'character' or 'word'")

    return levenshtein_distance(reference_units, hypothesis_units) / len(reference_units)


def evaluate_ocr(reference_text, detections, elapsed_seconds=None):
    """Build an accuracy report for a single OCR run against a reference text."""
    extracted_text = '\n'.join(item['text'] for item in detections)
    confidences = [item['confidence'] for item in detections]
    return {
        'character_error_rate': error_rate(reference_text, extracted_text, 'character'),
        'word_error_rate': error_rate(reference_text, extracted_text, 'word'),
        'average_confidence': sum(confidences) / len(confidences) if confidences else None,
        'detection_count': len(detections),
        'processing_seconds': elapsed_seconds,
    }


def benchmark_easyocr_variants(image, reference_text, strategy_names=None):
    """Evaluate EasyOCR variants against labelled ground truth.

    This is intentionally a benchmarking helper, not the upload-time selection
    mechanism. It lets the team compare CER/WER, coverage, confidence and time
    on a labelled dataset before changing production defaults.
    """
    from .image_enhancement import build_ocr_variants
    from .ocr_service import run_ocr

    report = []
    for strategy, candidate_image in build_ocr_variants(image, strategy_names).items():
        detections, elapsed_seconds = run_ocr(candidate_image)
        report.append({
            'engine': 'easyocr',
            'strategy': strategy,
            **evaluate_ocr(reference_text, detections, elapsed_seconds),
        })
    return sorted(report, key=lambda item: (item['word_error_rate'], item['character_error_rate']))
