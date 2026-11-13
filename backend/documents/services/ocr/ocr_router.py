"""Select a configured OCR adapter and provide safe local fallback behavior."""

import os
import time

from .base import OCRUnavailable
from .model_registry import get_engine


def configured_languages():
    return tuple(language.strip() for language in os.environ.get('OCR_LANGUAGES', 'en,hi').split(',') if language.strip()) or ('en',)


def configured_device():
    return os.environ.get('OCR_DEVICE', 'cpu').lower()


def configured_engine_name():
    return os.environ.get('OCR_DEFAULT_ENGINE', 'easyocr').lower()


def resolve_engine(name=None, languages=None, device=None):
    requested = name or configured_engine_name()
    languages = tuple(languages or configured_languages())
    device = device or configured_device()
    engine = get_engine(requested, languages, device)
    if engine.is_available():
        return engine, []
    fallback = get_engine('easyocr', languages, device)
    if not fallback.is_available():
        raise OCRUnavailable(f'{requested} is unavailable and EasyOCR fallback is unavailable.')
    return fallback, [f'Requested OCR engine {requested} is unavailable; using EasyOCR fallback.']


def run(image, engine_name=None, languages=None, device=None):
    engine, warnings = resolve_engine(engine_name, languages, device)
    started = time.perf_counter()
    detections = engine.extract(image)
    elapsed = time.perf_counter() - started
    for detection in detections:
        detection['warnings'] = [*warnings, *detection.get('warnings', [])]
    return detections, elapsed, engine.identifier, warnings
