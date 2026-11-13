"""PaddleOCR adapter, activated only in a compatible worker environment."""

from importlib.util import find_spec

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection


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
        try:
            from paddleocr import PaddleOCR
            language = self.languages[0] if self.languages else 'en'
            reader = PaddleOCR(lang=language, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
            output = reader.predict(image) if hasattr(reader, 'predict') else reader.ocr(image, cls=False)
        except Exception as exc:
            raise OCRUnavailable(f'PaddleOCR could not process this image: {exc}') from exc
        return self._normalise(output, language)

    def _normalise(self, output, language):
        detections = []
        for page in output or []:
            payload = page if isinstance(page, dict) else None
            as_json = getattr(page, 'json', None)
            if callable(as_json):
                payload = as_json()
            if isinstance(payload, dict):
                payload = payload.get('res', payload)
            if isinstance(payload, dict) and 'rec_texts' in payload:
                boxes = payload.get('rec_boxes') or payload.get('dt_polys') or []
                for box, text, score in zip(boxes, payload.get('rec_texts', []), payload.get('rec_scores', [])):
                    box = box.tolist() if hasattr(box, 'tolist') else box
                    if len(box) == 4 and not isinstance(box[0], (list, tuple)):
                        x1, y1, x2, y2 = box
                        box = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    detections.append(normalize_detection(engine=self.name, model_name=self.model_name, text=str(text), confidence=score, bounding_box=box, language=language, raw_metadata={'adapter': 'paddleocr'}))
                continue
            for item in page or []:
                if len(item) >= 2 and isinstance(item[1], (list, tuple)):
                    detections.append(normalize_detection(engine=self.name, model_name=self.model_name, text=str(item[1][0]), confidence=item[1][1], bounding_box=item[0], language=language, raw_metadata={'adapter': 'paddleocr'}))
        return detections
