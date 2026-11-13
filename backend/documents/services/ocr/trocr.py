"""Optional TrOCR boundary reserved for cropped handwritten text lines."""

from importlib.util import find_spec

from .base import OCREngine, OCRUnavailable


class TrOCREngine(OCREngine):
    name = 'trocr'
    model_name = 'microsoft/trocr-base-handwritten'

    def is_available(self):
        return find_spec('transformers') is not None

    def extract(self, image):
        if not self.is_available():
            raise OCRUnavailable(
                'TrOCR is unavailable. Install transformers and provide a handwritten line-detection pipeline.'
            )
        raise OCRUnavailable(
            'TrOCR requires text-line crops and has not been enabled for full-page document OCR.'
        )
