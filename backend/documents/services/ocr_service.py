"""Backward-compatible entry points for the modular OCR architecture."""

from .ocr.ocr_router import configured_languages, run


OCR_LANGUAGES = configured_languages()


def extract_text(image, languages=None):
    """Return normalized detections using the configured OCR engine."""
    detections, _, _, _ = run(image, languages=languages)
    return detections


def run_ocr(image, languages=None, engine_name=None):
    """Preserve the legacy `(detections, elapsed_seconds)` OCR contract."""
    detections, elapsed, _, _ = run(image, engine_name=engine_name, languages=languages)
    return detections, elapsed


def run_ocr_detailed(image, engine_name=None):
    """Return detections, timing, selected engine identity, and router warnings."""
    return run(image, engine_name)
