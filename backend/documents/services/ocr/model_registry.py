"""Registry for local OCR adapters without importing optional heavy packages."""

from .doctr_engine import DocTREngine
from .easy_ocr import EasyOCREngine
from .paddle_ocr import PaddleOCREngine
from .trocr import TrOCREngine


ENGINE_TYPES = {
    'doctr': DocTREngine,
    'easyocr': EasyOCREngine,
    'paddleocr': PaddleOCREngine,
    'trocr': TrOCREngine,
}


def get_engine(name, languages=('en',), device='cpu'):
    try:
        return ENGINE_TYPES[name.lower()](languages=languages, device=device)
    except KeyError as exc:
        raise ValueError(f'Unknown OCR engine: {name}') from exc


def available_engines(languages=('en',), device='cpu'):
    return {
        name: get_engine(name, languages, device).is_available()
        for name in ENGINE_TYPES
    }
