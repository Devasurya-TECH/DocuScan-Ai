import os
import logging
import tempfile
from pathlib import Path

import cv2
import numpy as np
from django.core.files.base import ContentFile
from django.db import close_old_connections, connections as db_connections

from .image_processing import correct_perspective, load_image
from .image_enhancement import assess_quality, build_ocr_variants, recovery_strategies
from .ocr_service import run_ocr
from .document_representation import build_document_representation
from .capture_analysis import find_safe_document_boundary
from .script_detection import annotate_detection_languages
from documents.models import Document

logger = logging.getLogger(__name__)


# Benchmarks can include every variant. The upload path intentionally limits
# candidates to avoid making ordinary document processing unnecessarily slow.
# Normal uploads start with the best-performing baseline (colour). Recovery
# variants run only when that first OCR pass is too weak to trust.
PRODUCTION_OCR_VARIANTS = ('color',)
RECOVERY_OCR_VARIANTS = ('enhanced_color',)
RECOVERY_CONFIDENCE_THRESHOLD = 0.50


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


def safe_open_image(field_file):
    """
    Safely load an image from a Django FieldFile whether stored locally, in S3,
    or in memory, returning a numpy BGR image array.
    """
    try:
        if hasattr(field_file, 'path') and os.path.exists(field_file.path):
            img = cv2.imread(field_file.path)
            if img is not None:
                return img
    except (NotImplementedError, AttributeError, ValueError):
        pass

    try:
        field_file.open('rb')
        content = field_file.read()
        if not content:
            raise FileNotFoundError("Uploaded file content is empty or missing from storage.")
        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from uploaded file bytes.")
        return img
    except Exception as exc:
        raise FileNotFoundError(f"Source file could not be read from storage: {exc}") from exc
    finally:
        try:
            field_file.close()
        except Exception:
            pass


def safe_get_pdf_path(field_file):
    """
    Ensure PDF file is accessible via local path for pypdf / pypdfium2.
    Returns (path_str, is_temporary_bool).
    """
    try:
        if hasattr(field_file, 'path') and os.path.exists(field_file.path):
            return field_file.path, False
    except (NotImplementedError, AttributeError, ValueError):
        pass

    try:
        field_file.open('rb')
        content = field_file.read()
        if not content:
            raise FileNotFoundError("PDF file content is empty or missing from storage.")
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.write(content)
        tmp.flush()
        tmp.close()
        return tmp.name, True
    finally:
        try:
            field_file.close()
        except Exception:
            pass


def process_document(document, languages=None):
    """Create the enhanced scan and OCR data for a saved document record.

    Boundary detection is best-effort: a valid image that has no detectable page
    is still enhanced and sent to OCR instead of being discarded.
    """
    if not document.uploaded_file:
        raise ValueError("Document has no uploaded file associated.")

    # Determine if the file is a PDF
    file_name = document.uploaded_file.name.lower() if document.uploaded_file.name else ''
    is_pdf_file = file_name.endswith('.pdf')

    # Handle multi-page PDF documents
    if is_pdf_file:
        document.progress_stage = 'pdf_extraction'
        document.progress_percent = 20
        document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])

        pdf_path, is_temp = safe_get_pdf_path(document.uploaded_file)
        try:
            db_connections.close_all()
            total_pages, pages = extract_pdf_data(pdf_path)
            close_old_connections()
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
                # Check status before final save
                if document.id:
                    current = Document.objects.filter(pk=document.id).values('status', 'job_id').first()
                    if current and current['status'] != 'processing':
                        logger.warning(
                            "Document %s status was modified to '%s' externally; preserving status.",
                            document.id, current['status'],
                        )
                        document.status = current['status']
                        return document
                document.save()
                return document
        finally:
            if is_temp and os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except OSError:
                    pass

    # Standard image / photographed document pipeline
    document.progress_stage = 'boundary_detection'
    document.progress_percent = 25
    document.save(update_fields=['progress_stage', 'progress_percent', 'updated_at'])

    source_image = safe_open_image(document.uploaded_file)
    # Downsample high-res inputs to 1280 max dimension upfront to save memory and acceleration
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

    # Explicitly release database connection before the compute-heavy OCR candidate selection.
    # Tesseract and OCR variant evaluation run without needing an open DB socket.
    db_connections.close_all()
    selected, candidates = select_ocr_candidate(scan_image, languages=languages)
    close_old_connections()
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

    # Optimistic concurrency check before marking completed:
    # Ensure the document was not marked failed, cancelled, or superseded by a newer retry
    close_old_connections()
    if document.id:
        current_state = Document.objects.filter(pk=document.id).values('status', 'job_id').first()
        if current_state:
            if current_state['status'] != 'processing':
                logger.warning(
                    "Document %s status was externally modified to '%s'; preserving state, not completing.",
                    document.id, current_state['status'],
                )
                document.status = current_state['status']
                return document
            if document.job_id and current_state['job_id'] != document.job_id:
                logger.warning(
                    "Document %s job_id was superseded (%s -> %s); discarding results.",
                    document.id, document.job_id, current_state['job_id'],
                )
                return document

    document.status = 'completed'
    document.progress_stage = 'completed'
    document.progress_percent = 100
    document.save()
    return document
