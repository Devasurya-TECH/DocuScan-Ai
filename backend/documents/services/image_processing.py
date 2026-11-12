
import cv2
import numpy as np


# ==========================================
# 1. LOAD IMAGE
# ==========================================

def load_image(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to load image")

    return image


# ==========================================
# 2. GRAYSCALE CONVERSION
# ==========================================

def convert_to_grayscale(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return gray


# ==========================================
# 3. GAUSSIAN BLUR
# ==========================================

def apply_gaussian_blur(image):

    blurred = cv2.GaussianBlur(
        image,
        (5, 5),
        0
    )

    return blurred


# ==========================================
# 4. CANNY EDGE DETECTION
# ==========================================

def apply_canny(image):

    edges = cv2.Canny(
        image,
        50,
        150
    )

    return edges


# ==========================================
# 5. CONTOUR DETECTION
# ==========================================

def find_contours(edges):

    contours, hierarchy = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    return contours


# ==========================================
# 6. DOCUMENT CORNER DETECTION
# ==========================================


def find_document_corners(image):

    # 1. Convert image to grayscale
    gray = convert_to_grayscale(image)

    # 2. Reduce noise
    blurred = apply_gaussian_blur(gray)

    # 3. Detect edges
    edges = cv2.Canny(blurred, 75, 200)

    # 4. Connect nearby edge segments
    kernel = np.ones((5, 5), np.uint8)

    closed_edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel
    )

    # 5. Find contours
    contours, hierarchy = cv2.findContours(
        closed_edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # 6. Sort contours by area
    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True
    )

    image_area = image.shape[0] * image.shape[1]

    # 7. Examine the largest 30 contours
    for contour in contours[:30]:

        area = cv2.contourArea(contour)

        # Reject contours that are too small
        if area < image_area * 0.10:
            continue

        # Calculate perimeter
        perimeter = cv2.arcLength(
            contour,
            True
        )

        # Approximate polygon
        approx = cv2.approxPolyDP(
            contour,
            0.02 * perimeter,
            True
        )

        # Document candidate must have four corners
        if len(approx) == 4 and cv2.isContourConvex(approx):

            print("Document candidate area:", area)

            return approx.reshape(4, 2)

    raise ValueError("Document boundary not detected")


# ==========================================
# 7. ORDER FOUR CORNER POINTS
# ==========================================

def order_points(points):

    rect = np.zeros(
        (4, 2),
        dtype="float32"
    )

    # Sum of coordinates
    s = points.sum(axis=1)

    # Difference of coordinates
    diff = np.diff(
        points,
        axis=1
    )

    rect[0] = points[np.argmin(s)]       # Top-left
    rect[2] = points[np.argmax(s)]       # Bottom-right
    rect[1] = points[np.argmin(diff)]    # Top-right
    rect[3] = points[np.argmax(diff)]    # Bottom-left

    return rect


# ==========================================
# 8. PERSPECTIVE CORRECTION
# ==========================================

def correct_perspective(image, points):

    rect = order_points(points)

    (tl, tr, br, bl) = rect

    # Calculate output width
    width_a = np.linalg.norm(br - bl)

    width_b = np.linalg.norm(tr - tl)

    max_width = int(
        max(width_a, width_b)
    )

    # Calculate output height
    height_a = np.linalg.norm(tr - br)

    height_b = np.linalg.norm(tl - bl)

    max_height = int(
        max(height_a, height_b)
    )

    # Destination coordinates
    destination = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    # Calculate transformation matrix
    matrix = cv2.getPerspectiveTransform(
        rect,
        destination
    )

    # Apply perspective transformation
    warped = cv2.warpPerspective(
        image,
        matrix,
        (max_width, max_height)
    )

    return warped
# ==========================================
# 8. image enhancing
# ==========================================

def enhance_document(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    denoised=cv2.medianBlur(gray,3)
    clahe=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8))
    enhanced=clahe.apply(denoised)

    threshold=cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,15,
        10
    )
    return threshold