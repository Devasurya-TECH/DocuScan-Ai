"""
docTR OCR engine adapter using PyTorch and Mindee docTR.
Fast, accurate, single-instance deep learning document OCR.
"""

import logging
import threading
from importlib.util import find_spec
import numpy as np

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection

logger = logging.getLogger(__name__)


class DocTREngine(OCREngine):
    name = 'doctr'
    model_name = 'db_mobilenet_v3_large+crnn_mobilenet_v3_large'
    _predictor = None
    _lock = threading.Lock()

    @classmethod
    def is_model_loaded(cls):
        """Check if the OCR predictor has been loaded into memory."""
        return cls._predictor is not None

    @classmethod
    def reset_model(cls):
        """Reset the cached predictor (primarily used for testing)."""
        with cls._lock:
            cls._predictor = None

    def is_available(self):
        """Check availability without loading PyTorch or model weights."""
        return find_spec('doctr') is not None

    def _load_model(self):
        """
        Thread-safe lazy initialization for the docTR predictor.
        Ensures the model is loaded only when an OCR request actually arrives,
        cached in worker process memory, and protected against race conditions.
        """
        if not self.is_available():
            raise OCRUnavailable('python-doctr is not installed in this environment.')

        if DocTREngine._predictor is not None:
            return DocTREngine._predictor

        with DocTREngine._lock:
            # Double-checked locking pattern
            if DocTREngine._predictor is not None:
                return DocTREngine._predictor

            try:
                import torch
                torch.set_num_threads(2)
                from doctr.models import ocr_predictor

                logger.info('Initializing docTR OCR predictor (thread-safe lazy load)...')
                predictor = ocr_predictor(
                    det_arch='db_mobilenet_v3_large',
                    reco_arch='crnn_mobilenet_v3_large',
                    pretrained=True,
                )
                DocTREngine._predictor = predictor
                logger.info('docTR OCR predictor initialized and cached successfully.')
                return DocTREngine._predictor
            except Exception as exc:
                logger.exception('Failed to initialize docTR predictor: %s', exc)
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

        orig_h, orig_w = 1000, 1000
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

            orig_h, orig_w = rgb_image.shape[:2]
            # Downscale oversized images (e.g. 12MP phone photos) to prevent crossing Render's 512MB RAM ceiling
            MAX_DIM = 1280
            if max(orig_h, orig_w) > MAX_DIM:
                scale = MAX_DIM / float(max(orig_h, orig_w))
                new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                rgb_image = cv2.resize(rgb_image, (new_w, new_h), interpolation=cv2.INTER_AREA)

            doc = [rgb_image]
        else:
            raise ValueError(f'Unsupported image input type for docTR: {type(image)}')

        # Perform inference with zero gradient memory retention
        import torch
        with torch.inference_mode():
            result = DocTREngine._predictor(doc)
        export = result.export()

        import gc
        del doc
        gc.collect()

        detections = []
        if not export.get('pages'):
            return detections

        page = export['pages'][0]
        # Map normalized coordinates back to the original image dimensions
        h, w = orig_h, orig_w

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
