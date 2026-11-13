"""Optional PaddleOCR adapter boundary.

PaddleOCR is deliberately optional: the current Windows/Python 3.14 runtime is
outside its published Python support range, so routing falls back safely until
it is installed in a compatible environment.
"""

from importlib.util import find_spec

from .base import OCREngine, OCRUnavailable


class PaddleOCREngine(OCREngine):
    name = 'paddleocr'
    model_name = 'PP-OCRv5'

    def is_available(self):
        return find_spec('paddleocr') is not None and find_spec('paddle') is not None

    def extract(self, image):
        if not self.is_available():
            raise OCRUnavailable(
                'PaddleOCR is unavailable. Install PaddleOCR and PaddlePaddle in a supported Python environment.'
            )
        raise OCRUnavailable(
            'PaddleOCR is installed but its adapter requires a verified PP-OCRv5 integration run before it can be enabled.'
        )
