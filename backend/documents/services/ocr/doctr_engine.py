"""
docTR OCR engine adapter using PyTorch and Mindee docTR.
Fast, accurate, single-instance deep learning document OCR.
"""

import logging
from importlib.util import find_spec
import numpy as np

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection

logger = logging.getLogger(__name__)


class DocTREngine(OCREngine):
    name = 'doctr'
    model_name = 'db_mobilenet_v3_large+crnn_mobilenet_v3_large'
    _predictor = None

    def is_available(self):
        return find_spec('doctr') is not None

    def _load_model(self):
        if not self.is_available():
            raise OCRUnavailable('python-doctr is not installed in this environment.')
        if DocTREngine._predictor is None:
            try:
                from doctr.models import ocr_predictor
                logger.info('Initializing docTR OCR predictor (loaded once per worker)...')
                DocTREngine._predictor = ocr_predictor(
                    det_arch='db_mobilenet_v3_large',
                    reco_arch='crnn_mobilenet_v3_large',
                    pretrained=True,
                )
                logger.info('docTR OCR predictor initialized successfully.')
            except Exception as exc:
                raise OCRUnavailable(f'Could not initialize docTR predictor: {exc}') from exc

    def extract(self, image):
        """
        Extract text from an image using docTR.
        image: numpy array (BGR or RGB) or file path.
        Returns:
            list of normalized detections (dict with text, confidence, bounding_box)
        """
        self._load_model()
        from doctr.io import DocumentFile
        import cv2

        if isinstance(image, str):
            doc = DocumentFile.from_images(image)
        elif isinstance(image, np.ndarray):
            # docTR expects 3-channel RGB numpy array
            if len(image.shape) == 2:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 4:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                rgb_image = image
            doc = [rgb_image]
        else:
            raise ValueError(f'Unsupported image input type for docTR: {type(image)}')

        # Perform inference
        result = DocTREngine._predictor(doc)
        export = result.export()

        detections = []
        if not export.get('pages'):
            return detections

        page = export['pages'][0]
        page_dim = page.get('dimensions', (1000, 1000))
        h, w = page_dim[0], page_dim[1]

        for block in page.get('blocks', []):
            for line in block.get('lines', []):
                line_words = [w['value'] for w in line.get('words', [])]
                line_text = ' '.join(line_words).strip()
                if not line_text:
                    continue

                # Calculate average line confidence
                confidences = [w.get('confidence', 0.9) for w in line.get('words', [])]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.9

                # Geometry: doctr returns normalized [[xmin, ymin], [xmax, ymax]]
                geom = line.get('geometry')
                if geom and len(geom) == 2:
                    (x0, y0), (x1, y1) = geom
                    bbox = [
                        [int(x0 * w), int(y0 * h)],
                        [int(x1 * w), int(y0 * h)],
                        [int(x1 * w), int(y1 * h)],
                        [int(x0 * w), int(y1 * h)],
                    ]
                else:
                    bbox = [[0, 0], [w, 0], [w, 20], [0, 20]]

                detections.append(
                    normalize_detection(
                        engine=self.name,
                        model_name=self.model_name,
                        text=line_text,
                        confidence=avg_conf,
                        bounding_box=bbox,
                        language='en',
                    )
                )

        return detections

    def extract_full_text(self, image):
        """
        Directly returns the complete rendered text preserving layout and line breaks.
        """
        self._load_model()
        from doctr.io import DocumentFile
        import cv2

        if isinstance(image, str):
            doc = DocumentFile.from_images(image)
        elif isinstance(image, np.ndarray):
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
            doc = [rgb_image]
        else:
            raise ValueError(f'Unsupported image type: {type(image)}')

        result = DocTREngine._predictor(doc)
        return result.render()
