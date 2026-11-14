"""Safe document-photo decisions used before OCR."""

import cv2
import numpy as np

from .image_processing import find_document_corners


def _touches_frame(points, width, height, margin_ratio=0.015):
    """Check if the detected quadrilateral touches 3 or more outer frame edges."""
    margin = max(3, int(min(width, height) * margin_ratio))
    pts = np.asarray(points)
    touches_left = np.any(pts[:, 0] <= margin)
    touches_top = np.any(pts[:, 1] <= margin)
    touches_right = np.any(pts[:, 0] >= width - margin)
    touches_bottom = np.any(pts[:, 1] >= height - margin)
    edge_touch_count = sum([touches_left, touches_top, touches_right, touches_bottom])
    return edge_touch_count >= 3


def find_safe_document_boundary(image):
    """Only warp a boundary that is demonstrably inside the photo frame."""
    height, width = image.shape[:2]
    try:
        corners = find_document_corners(image)
    except ValueError:
        return None, {'mode': 'full_frame_or_no_boundary', 'reason': 'no_quadrilateral'}
    coverage = abs(cv2.contourArea(np.asarray(corners, dtype=np.float32))) / float(width * height)
    if _touches_frame(corners, width, height) and coverage > 0.94:
        return None, {'mode': 'full_frame_document', 'reason': 'boundary_touches_image_edge', 'boundary_coverage': round(coverage, 4)}
    return corners, {'mode': 'perspective_corrected', 'boundary_coverage': round(coverage, 4)}
