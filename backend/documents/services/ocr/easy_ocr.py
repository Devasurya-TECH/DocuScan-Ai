"""Lazy EasyOCR adapter retained as the verified local baseline."""

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection


class EasyOCREngine(OCREngine):
    name = 'easyocr'
    model_name = 'easyocr-1.7.2'
    _readers = {}

    def is_available(self):
        try:
            import easyocr  # noqa: F401
            return True
        except ImportError:
            return False

    def _reader(self):
        if not self.is_available():
            raise OCRUnavailable('EasyOCR is not installed. Install the easyocr package to use this engine.')
        key = (self.languages, self.device)
        if key not in self._readers:
            import easyocr
            self._readers[key] = easyocr.Reader(
                list(self.languages),
                gpu=self.device == 'gpu',
                verbose=False,
            )
        return self._readers[key]

    def extract(self, image):
        results = self._reader().readtext(
            image,
            decoder='greedy',
            canvas_size=2048,
            mag_ratio=1.0,
            contrast_ths=0.08,
            adjust_contrast=0.7,
            text_threshold=0.55,
            low_text=0.25,
            link_threshold=0.35,
        )
        language = self.languages[0]
        return [
            normalize_detection(
                engine=self.name,
                model_name=self.model_name,
                text=text,
                confidence=confidence,
                bounding_box=bounding_box,
                language=language,
                raw_metadata={'adapter': 'easyocr'},
            )
            for bounding_box, text, confidence in results
        ]
