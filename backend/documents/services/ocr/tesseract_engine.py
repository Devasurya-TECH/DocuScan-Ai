"""
Tesseract OCR engine adapter using pytesseract.
Lightweight, fast CPU document OCR with minimal memory footprint (~40MB RAM).
"""

import logging
import os
import shutil
import cv2
import numpy as np
from importlib.util import find_spec

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection

logger = logging.getLogger(__name__)

# Map common ISO 639-1 / 639-2 codes to Tesseract traineddata names
TESSERACT_LANG_MAP = {
    'en': 'eng',
    'hi': 'hin',
    'ta': 'tam',
    'te': 'tel',
    'bn': 'ben',
    'kn': 'kan',
    'ml': 'mal',
    'gu': 'guj',
    'mr': 'mar',
    'ur': 'urd',
    'pa': 'pan',
    'es': 'spa',
    'fr': 'fra',
    'de': 'deu',
}


class TesseractEngine(OCREngine):
    name = 'tesseract'
    model_name = 'tesseract-ocr-v5'

    def is_available(self):
        """Check whether pytesseract is installed and tesseract executable is accessible."""
        if find_spec('pytesseract') is None:
            return False
        tesseract_cmd = os.environ.get('TESSERACT_CMD')
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            return True
        return shutil.which('tesseract') is not None

    def _get_tesseract_languages(self):
        langs = []
        for l in self.languages:
            code = l.strip().lower()
            mapped = TESSERACT_LANG_MAP.get(code, code)
            if mapped not in langs:
                langs.append(mapped)
        return '+'.join(langs) if langs else 'eng'

    def extract(self, image):
        """
        Extract text from an image using Tesseract OCR.
        image: numpy array (BGR or RGB) or file path.
        Returns:
            list of normalized detections (dict with text, confidence, bounding_box)
        """
        if not self.is_available():
            raise OCRUnavailable('Tesseract OCR binary or pytesseract library is not installed in this environment.')

        import pytesseract

        tesseract_cmd = os.environ.get('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        if isinstance(image, str):
            rgb_image = cv2.imread(image)
            if rgb_image is None:
                raise ValueError(f"Unable to read image from path: {image}")
            rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 4:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                rgb_image = image
        else:
            raise ValueError(f"Unsupported image input type for Tesseract: {type(image)}")

        lang_str = self._get_tesseract_languages()

        # Optimize Tesseract for fast CPU document OCR:
        # --oem 1: Neural nets LSTM engine only (fastest & most accurate for modern Tesseract)
        # --psm 3: Fully automatic page segmentation without OSD (avoids expensive orientation search)
        fast_config = os.environ.get('TESSERACT_CONFIG', '--oem 1 --psm 3')

        try:
            data = pytesseract.image_to_data(
                rgb_image,
                lang=lang_str,
                config=fast_config,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            # If multi-language failed (e.g. missing hin.traineddata), fall back to eng
            if lang_str != 'eng':
                logger.warning(f"Tesseract failed with language '{lang_str}': {exc}. Retrying with 'eng'...")
                try:
                    data = pytesseract.image_to_data(
                        rgb_image,
                        lang='eng',
                        config=fast_config,
                        output_type=pytesseract.Output.DICT,
                    )
                except Exception as inner_exc:
                    raise OCRUnavailable(f"Tesseract OCR failed: {inner_exc}") from inner_exc
            else:
                raise OCRUnavailable(f"Tesseract OCR failed: {exc}") from exc

        detections = []
        n_boxes = len(data.get('text', []))

        for i in range(n_boxes):
            word_text = str(data['text'][i]).strip()
            conf_val = data.get('conf', [0])[i]

            try:
                conf = float(conf_val)
            except (ValueError, TypeError):
                conf = -1.0

            # conf < 0 represents structural blocks/lines without text
            if conf < 0 or not word_text:
                continue

            x = int(data['left'][i])
            y = int(data['top'][i])
            w = int(data['width'][i])
            h = int(data['height'][i])

            if w <= 0 or h <= 0:
                continue

            bbox = [
                [x, y],
                [x + w, y],
                [x + w, y + h],
                [x, y + h],
            ]
            normalized_conf = max(0.0, min(1.0, conf / 100.0))

            detections.append(
                normalize_detection(
                    engine=self.name,
                    model_name=self.model_name,
                    text=word_text,
                    confidence=normalized_conf,
                    bounding_box=bbox,
                    language=self.languages[0] if self.languages else 'en',
                    region_type='printed_text',
                    raw_metadata={
                        'block_num': data.get('block_num', [0])[i],
                        'line_num': data.get('line_num', [0])[i],
                        'word_num': data.get('word_num', [0])[i],
                    }
                )
            )

        return detections
