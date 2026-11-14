from pathlib import Path

import cv2
from django.core.files.base import ContentFile

from .image_processing import correct_perspective, load_image
from .image_enhancement import assess_quality, build_ocr_variants, recovery_strategies
from .ocr_service import run_ocr
from .document_representation import build_document_representation
from .capture_analysis import find_safe_document_boundary
from .script_detection import annotate_detection_languages


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


def _resize_if_oversized(image, max_dim=1280):
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image


def select_ocr_candidate(image, languages=None):
    """Use one fast pass with docTR/primary engine, then recover only when its signal is weak."""
    resized = _resize_if_oversized(image, max_dim=1280)
    candidates = []

    def add_candidates(strategy_names):
        for strategy, candidate_image in build_ocr_variants(resized, strategy_names).items():
            detections, elapsed = run_ocr(candidate_image, languages=languages)
            confidences = [item['confidence'] for item in detections]
            candidates.append({
                'strategy': strategy,
                'image': candidate_image,
                'detections': detections,
                'elapsed_seconds': elapsed,
                'score': _candidate_score(detections),
                'average_confidence': (
                    sum(confidences) / len(confidences) if confidences else None
                ),
            })

    add_candidates(PRODUCTION_OCR_VARIANTS)
    primary = candidates[0]
    if (
        primary['score'] <= 0
        or primary['average_confidence'] is None
        or primary['average_confidence'] < RECOVERY_CONFIDENCE_THRESHOLD
    ):
        add_candidates(recovery_strategies(assess_quality(resized)))

    return max(candidates, key=lambda candidate: candidate['score']), candidates


from .pdf_ingestion import is_pdf, extract_pdf_data


def process_document(document, languages=None):
    """Create the enhanced scan and OCR data for a saved document record.

    Boundary detection is best-effort: a valid image that has no detectable page
    is still enhanced and sent to OCR instead of being discarded.
    """
    file_path = document.uploaded_file.path
    
    # Handle multi-page PDF documents
    if is_pdf(file_path):
        document.progress_stage = 'pdf_extraction'
        document.progress_percent = 20
        document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])
        
        total_pages, pages = extract_pdf_data(file_path)
        document.is_multipage = total_pages > 1
        document.page_count = total_pages
        document.pages_data = pages
        
        # If PDF has extractable text, combine
        combined_pdf_text = '\n\n'.join(p['text'] for p in pages if p.get('text'))
        if combined_pdf_text.strip():
            document.extracted_text = combined_pdf_text
            document.ocr_engine = 'pypdf:digital_pdf'
            document.status = 'completed'
            document.progress_stage = 'completed'
            document.progress_percent = 100
            document.document_type = 'general_printed_document'
            document.save()
            return document

    # Standard image / photographed document pipeline
    document.progress_stage = 'boundary_detection'
    document.progress_percent = 25
    document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])
    
    source_image = load_image(file_path)
    source_image = _resize_if_oversized(source_image, max_dim=1280)

    corners, capture = find_safe_document_boundary(source_image)
    try:
        if corners is None:
            raise ValueError('No safe perspective boundary')
        scan_image = correct_perspective(source_image, corners)
    except ValueError:
        scan_image = source_image

    document.progress_stage = 'ocr_inference'
    document.progress_percent = 50
    document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])

    selected, candidates = select_ocr_candidate(scan_image, languages=languages)
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

    document.progress_stage = 'layout_analysis'
    document.progress_percent = 75
    document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])

    detections = selected['detections']
    script_metadata = annotate_detection_languages(detections)
    document.ocr_results = detections
    document.extracted_text = '\n'.join(item['text'] for item in detections)
    document.average_confidence = (
        sum(item['confidence'] for item in detections) / len(detections)
        if detections else None
    )
    if detections:
        document.ocr_engine = f"{detections[0].get('engine', 'unknown')}:{detections[0].get('model_name', 'unknown')}"
    else:
        document.ocr_engine = 'unknown'
    document.processing_strategy = selected['strategy']
    document.boundary_detected = corners is not None
    document.quality_metrics = {
        **assess_quality(source_image),
        'capture': capture,
        'script_detection': script_metadata,
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
    
    document.progress_stage = 'document_understanding'
    document.progress_percent = 90
    document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])
    
    document.document_data = build_document_representation(
        detections,
        page_width=processed_image.shape[1],
        page_height=processed_image.shape[0],
    )
    document.document_type = document.document_data['document_type']['type']
    document.status = 'completed'
    document.progress_stage = 'completed'
    document.progress_percent = 100
    document.save()
    return document
