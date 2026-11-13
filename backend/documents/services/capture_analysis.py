"""Safe document-photo decisions used before OCR."""

import cv2
import numpy as np

from .image_processing import find_document_corners


def _touches_frame(points, width, height, margin_ratio=0.025):
    margin = max(3, int(min(width, height) * margin_ratio))
    points = np.asarray(points)
    return bool(np.any(points[:, 0] <= margin) or np.any(points[:, 1] <= margin) or np.any(points[:, 0] >= width - margin) or np.any(points[:, 1] >= height - margin))


def find_safe_document_boundary(image):
    """Only warp a boundary that is demonstrably inside the photo frame."""
    height, width = image.shape[:2]
    try:
        corners = find_document_corners(image)
    except ValueError:
        return None, {'mode': 'full_frame_or_no_boundary', 'reason': 'no_quadrilateral'}
    coverage = abs(cv2.contourArea(np.asarray(corners, dtype=np.float32))) / float(width * height)
    if _touches_frame(corners, width, height) or coverage > 0.94:
        return None, {'mode': 'full_frame_document', 'reason': 'boundary_touches_image_edge', 'boundary_coverage': round(coverage, 4)}
    return corners, {'mode': 'perspective_corrected', 'boundary_coverage': round(coverage, 4)}
