from pathlib import Path

import cv2
from django.core.files.base import ContentFile

from .image_processing import (
    correct_perspective,
    find_document_corners,
    load_image,
)
from .image_enhancement import assess_quality, build_ocr_variants
from .ocr_service import OCR_LANGUAGES, run_ocr
from .document_representation import build_document_representation


# Benchmarks can include every variant. The upload path intentionally limits
# candidates to avoid making ordinary document processing unnecessarily slow.
# Normal uploads start with the best-performing baseline (colour). Recovery
# variants run only when that first OCR pass is too weak to trust.
PRODUCTION_OCR_VARIANTS = ('color',)
RECOVERY_OCR_VARIANTS = ('enhanced_color', 'deskewed_clahe')
RECOVERY_CONFIDENCE_THRESHOLD = 0.70


def _candidate_score(detections):
    """Score useful, confident text coverage without treating confidence as CER.

    A raw confidence sum unfairly rewards candidates that emit many tiny or
    low-confidence fragments. Character-weighted confidence better reflects
    whether a pass recovered readable document content. Final OCR quality is
    still measured only against verified ground truth with CER/WER.
    """
    useful = [
        item for item in detections
        if item['text'].strip() and item['confidence'] >= 0.25
    ]
    coverage = sum(min(len(item['text'].strip()), 80) for item in useful)
    weighted_confidence = sum(
        min(len(item['text'].strip()), 80) * item['confidence']
        for item in useful
    )
    weak_fragments = sum(
        1 for item in detections
        if item['text'].strip() and item['confidence'] < 0.25
    )
    return round(weighted_confidence + (coverage * 0.08) - (weak_fragments * 0.5), 6)


def select_ocr_candidate(image):
    """Use one fast pass, then recover only when its signal is weak."""
    candidates = []
    def add_candidates(strategy_names):
        for strategy, candidate_image in build_ocr_variants(image, strategy_names).items():
            detections, elapsed = run_ocr(candidate_image)
            confidences = [item['confidence'] for item in detections]
            candidates.append({
                'strategy': strategy,
                'image': candidate_image,
                'detections': detections,
                'elapsed_seconds': elapsed,
                'score': _candidate_score(detections),
                'average_confidence': sum(confidences) / len(confidences) if confidences else None,
            })

    add_candidates(PRODUCTION_OCR_VARIANTS)
    primary = candidates[0]
    if (
        not primary['detections']
        or primary['average_confidence'] is None
        or primary['average_confidence'] < RECOVERY_CONFIDENCE_THRESHOLD
    ):
        add_candidates(RECOVERY_OCR_VARIANTS)
    return max(candidates, key=lambda candidate: candidate['score']), candidates


def process_document(document):
    """Create the enhanced scan and OCR data for a saved document record.

    Boundary detection is best-effort: a valid image that has no detectable page
    is still enhanced and sent to OCR instead of being discarded.
    """
    source_image = load_image(document.uploaded_file.path)

    try:
        corners = find_document_corners(source_image)
        scan_image = correct_perspective(source_image, corners)
    except ValueError:
        scan_image = source_image

    selected, candidates = select_ocr_candidate(scan_image)
    processed_image = selected['image']
    encoded, data = cv2.imencode('.png', processed_image)
    if not encoded:
        raise ValueError('Could not create the processed document image.')

    original_stem = Path(document.uploaded_file.name).stem
    document.processed_file.save(
        f'{original_stem}_scan.png',
        ContentFile(data.tobytes()),
        save=False,
    )

    detections = selected['detections']
    document.ocr_results = detections
    document.extracted_text = '\n'.join(item['text'] for item in detections)
    document.average_confidence = (
        sum(item['confidence'] for item in detections) / len(detections)
        if detections else None
    )
    document.ocr_engine = f"easyocr:{','.join(OCR_LANGUAGES)}"
    document.processing_strategy = selected['strategy']
    document.boundary_detected = scan_image is not source_image
    document.quality_metrics = {
        **assess_quality(source_image),
        'ocr_candidates': [
            {
                'strategy': candidate['strategy'],
                'detection_count': len(candidate['detections']),
                'average_confidence': candidate['average_confidence'],
                'selection_score': candidate['score'],
                'processing_seconds': round(candidate['elapsed_seconds'], 3),
            }
            for candidate in candidates
        ],
        'low_confidence_regions': [
            {'text': item['text'], 'confidence': item['confidence'], 'bounding_box': item['bounding_box']}
            for item in detections if item['confidence'] < 0.70
        ],
    }
    document.processing_duration = round(sum(candidate['elapsed_seconds'] for candidate in candidates), 3)
    document.document_data = build_document_representation(
        detections,
        page_width=processed_image.shape[1],
        page_height=processed_image.shape[0],
    )
    document.document_type = document.document_data['document_type']['type']
    document.status = 'completed'
    document.save()
    return document
