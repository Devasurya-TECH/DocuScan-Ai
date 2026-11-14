"""
TrOCR handwriting recognition adapter with line segmentation.
Specialized for handwritten English notes, letters, and forms.
"""

import logging
from importlib.util import find_spec
import cv2
import numpy as np

from .base import OCREngine, OCRUnavailable
from .result_normalizer import normalize_detection

logger = logging.getLogger(__name__)


class TrOCREngine(OCREngine):
    name = 'trocr'
    model_name = 'microsoft/trocr-base-handwritten'
    _processor = None
    _model = None

    def is_available(self):
        return find_spec('transformers') is not None and find_spec('torch') is not None

    def _load_model(self):
        if not self.is_available():
            raise OCRUnavailable('Transformers or PyTorch is not installed in this environment.')
        if self._processor is None or self._model is None:
            try:
                import torch
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                
                device = 'cuda' if (self.device == 'gpu' and torch.cuda.is_available()) else 'cpu'
                self._processor = TrOCRProcessor.from_pretrained(self.model_name)
                self._model = VisionEncoderDecoderModel.from_pretrained(self.model_name).to(device)
                self._model.eval()
            except Exception as exc:
                raise OCRUnavailable(f'Could not initialize TrOCR model: {exc}') from exc

    def _segment_handwritten_lines(self, image):
        """
        Segment a document image into individual horizontal text lines
        using morphological operations and connected component analysis.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        height, width = gray.shape[:2]
        
        # Binarize with Otsu
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Morphological horizontal dilation to bridge letters into solid text lines
        kernel_width = max(15, int(width * 0.04))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        # Find contours of lines
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        line_boxes = []
        min_line_width = int(width * 0.08)
        min_line_height = max(8, int(height * 0.01))
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter noise and extremely tiny fragments
            if w >= min_line_width and h >= min_line_height:
                # Add padding
                pad_x = int(w * 0.02)
                pad_y = int(h * 0.1)
                x0 = max(0, x - pad_x)
                y0 = max(0, y - pad_y)
                x1 = min(width, x + w + pad_x)
                y1 = min(height, y + h + pad_y)
                line_boxes.append((x0, y0, x1 - x0, y1 - y0))
                
        # Sort lines top-to-bottom
        line_boxes.sort(key=lambda b: b[1])
        return line_boxes if line_boxes else [(0, 0, width, height)]

    def extract(self, image):
        self._load_model()
        import torch
        from PIL import Image

        device = 'cuda' if (self.device == 'gpu' and torch.cuda.is_available()) else 'cpu'
        line_boxes = self._segment_handwritten_lines(image)
        detections = []
        
        for x, y, w, h in line_boxes:
            crop = image[y:y+h, x:x+w]
            if crop.size == 0:
                continue
                
            # Convert to RGB PIL Image
            if len(crop.shape) == 2:
                pil_crop = Image.fromarray(crop).convert('RGB')
            else:
                pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                
            try:
                pixel_values = self._processor(pil_crop, return_tensors="pt").pixel_values.to(device)
                with torch.no_grad():
                    generated_ids = self._model.generate(pixel_values, max_new_tokens=64)
                generated_text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            except Exception as exc:
                logger.warning(f"TrOCR line recognition error: {exc}")
                generated_text = ""
                
            if not generated_text:
                continue
                
            box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            detections.append(
                normalize_detection(
                    engine=self.name,
                    model_name=self.model_name,
                    text=generated_text,
                    confidence=0.88,  # TrOCR generative decoder
                    bounding_box=box,
                    language='en',
                    region_type='handwritten_text',
                    warnings=['TrOCR checkpoint is specialized for Latin-script/English handwriting. Indic handwriting is unsupported by this model.']
                )
            )
            
        return detections
