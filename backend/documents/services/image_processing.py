import cv2
import numpy as np


def load_image(image_path):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("Unable to load image")
    return image


def convert_to_grayscale(image):
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_gaussian_blur(image, kernel_size=5):
    return cv2.GaussianBlur(convert_to_grayscale(image), (kernel_size, kernel_size), 0)


def auto_canny(image, sigma=0.33):
    """
    Computes contrast-adaptive Canny edge thresholds based on image median.
    """
    gray = convert_to_grayscale(image)
    median_val = np.median(gray)
    lower = int(max(0, (1.0 - sigma) * median_val))
    upper = int(min(255, (1.0 + sigma) * median_val))
    return cv2.Canny(gray, lower, upper)


def apply_canny(image):
    return auto_canny(image)


def find_contours(edges):
    contours, hierarchy = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    return contours


def find_document_corners(image):
    """
    Robust 4-corner document boundary detection with multi-scale edge enhancement.
    Handles white documents on light/dark backgrounds, eliminating internal text noise.
    """
    gray = convert_to_grayscale(image)
    h, w = gray.shape[:2]
    image_area = h * w
    
    # Scale for consistent edge and contour detection without text interference
    scale = 600.0 / max(h, w)
    small_w, small_h = max(100, int(w * scale)), max(100, int(h * scale))
    small = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
    small_area = small_w * small_h
    
    # Large Gaussian blur to eliminate small black writing from internal edges
    blur = cv2.GaussianBlur(small, (15, 15), 0)
    
    candidates = []
    
    # Method 1: Adaptive Canny with morphological closing
    med = np.median(blur)
    lower = int(max(0, 0.66 * med))
    upper = int(min(255, 1.33 * med))
    canny = cv2.Canny(blur, lower, upper)
    kernel_c = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed_c = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel_c)
    cnts_c, _ = cv2.findContours(closed_c, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates.extend(cnts_c)
    
    # Method 2: Otsu thresholding (ideal for white paper with black writing)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # If the border is predominantly white, invert to isolate the page
    if np.mean(otsu[0:5, :]) > 128:
        otsu = cv2.bitwise_not(otsu)
    kernel_o = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    closed_o = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel_o)
    cnts_o, _ = cv2.findContours(closed_o, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates.extend(cnts_o)
    
    # Sort largest to smallest
    candidates = sorted(candidates, key=cv2.contourArea, reverse=True)
    
    for c in candidates:
        area = cv2.contourArea(c)
        if area < small_area * 0.12 or area > small_area * 0.98:
            continue
            
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        
        for eps in (0.02, 0.03, 0.04, 0.05, 0.06):
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                pts = approx.reshape(4, 2) / scale
                return np.int32(pts)
                
    raise ValueError("Document boundary not detected")


def order_points(points):
    """
    Orders 4 quadrilateral coordinates clockwise: [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
    Uses centroid polar angle sorting to avoid rotation and inversion artifacts.
    """
    pts = np.asarray(points, dtype="float32")
    if len(pts) != 4:
        raise ValueError("order_points expects exactly 4 coordinate points.")
        
    # Compute center of mass
    center = np.mean(pts, axis=0)
    
    # Sort points clockwise starting from top-left (angle relative to center)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    sort_order = np.argsort(angles)
    pts = pts[sort_order]
    
    # Identify the top-left point as the point with smallest x + y
    tl_idx = np.argmin(pts.sum(axis=1))
    rect = np.roll(pts, -tl_idx, axis=0)
    
    # Verify orientation: if width/height vector is inverted, re-order
    # [tl, tr, br, bl]
    tl, tr, br, bl = rect[0], rect[1], rect[2], rect[3]
    if tr[0] < bl[0] and tr[1] > bl[1]:
        rect = np.array([tl, bl, br, tr], dtype="float32")
        
    return rect


def correct_perspective(image, points):
    rect = order_points(points)
    (tl, tr, br, bl) = rect
    
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(100, int(max(width_a, width_b)))
    
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(100, int(max(height_a, height_b)))
    
    destination = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")
    
    matrix = cv2.getPerspectiveTransform(rect, destination)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height), flags=cv2.INTER_CUBIC)
    return warped


def enhance_document(image):
    gray = convert_to_grayscale(image)
    denoised = cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    threshold = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        10
    )
    return threshold
