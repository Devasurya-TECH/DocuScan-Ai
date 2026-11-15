"""Modular, testable image variants used for OCR benchmarking and selection."""

import cv2
import numpy as np


def resize_for_ocr(image, max_dimension=2000):
    """Downsize only oversized inputs; preserve detail in typical phone captures."""
    height, width = image.shape[:2]
    largest = max(height, width)
    if largest <= max_dimension:
        return image.copy()
    scale = max_dimension / largest
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def upscale_for_ocr(image, minimum_dimension=1200, maximum_dimension=1600):
    """Increase small captures before OCR while never enlarging past a safe limit.

    Phone photos are normally already large enough. Small screenshots and low
    resolution scans, however, often lose character detail unless they are
    enlarged with a high-quality interpolation method.
    """
    height, width = image.shape[:2]
    largest = max(height, width)
    if largest >= minimum_dimension:
        return resize_for_ocr(image, maximum_dimension)
    scale = minimum_dimension / largest
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_CUBIC)


def grayscale(image):
    return image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def median_blur(image, kernel_size=3):
    return cv2.medianBlur(grayscale(image), kernel_size)


def gaussian_blur(image, kernel_size=5):
    return cv2.GaussianBlur(grayscale(image), (kernel_size, kernel_size), 0)


def clahe(image):
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(median_blur(image))


def adaptive_threshold(image):
    return cv2.adaptiveThreshold(
        clahe(image), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10,
    )


def otsu_threshold(image):
    _, thresholded = cv2.threshold(clahe(image), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresholded


def sharpen(image):
    source = grayscale(image)
    blurred = cv2.GaussianBlur(source, (0, 0), 2.0)
    return cv2.addWeighted(source, 1.5, blurred, -0.5, 0)


def morphological_open(image):
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(grayscale(image), cv2.MORPH_OPEN, kernel)


def enhanced_color(image):
    """Preserve colour evidence while improving uneven illumination and contrast."""
    source = upscale_for_ocr(image)
    if len(source.shape) == 2:
        return clahe(source)
    lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB)
    lightness, channel_a, channel_b = cv2.split(lab)
    lightness = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
    return cv2.cvtColor(cv2.merge((lightness, channel_a, channel_b)), cv2.COLOR_LAB2BGR)


def correct_uneven_illumination(image):
    """Reduce shadows and mild glare while preserving character strokes."""
    source = upscale_for_ocr(image)
    gray = grayscale(source)
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    normalised = cv2.divide(gray, background, scale=255)
    return cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(normalised)


def correct_small_skew(image, maximum_angle=15):
    """Correct small text-baseline skew without unexpectedly rotating a page."""
    source = grayscale(image)
    _, binary = cv2.threshold(source, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coordinates = np.column_stack(np.where(binary > 0))
    if len(coordinates) < 100:
        return image.copy(), 0.0

    angle = cv2.minAreaRect(coordinates)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) > maximum_angle:
        return image.copy(), 0.0

    height, width = source.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), round(float(angle), 3)


def assess_quality(image):
    """Return explainable, non-ML quality metrics for UI and routing decisions."""
    gray = grayscale(image)
    height, width = gray.shape[:2]
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(np.std(gray))
    return {
        'width': int(gray.shape[1]),
        'height': int(gray.shape[0]),
        'blur_variance': round(blur, 2),
        'brightness_mean': round(float(np.mean(gray)), 2),
        'contrast_stddev': round(contrast, 2),
        'possible_glare_ratio': round(float(np.mean(gray >= 245)), 4),
        'short_edge_pixels': int(min(width, height)),
        'low_resolution_risk': min(width, height) < 900,
        'blur_risk': blur < 60,
        'low_contrast_risk': contrast < 32,
    }


def recovery_strategies(quality):
    strategies = ['enhanced_color', 'deskewed_clahe']
    if quality.get('possible_glare_ratio', 0) > 0.08 or quality.get('low_contrast_risk'):
        strategies.append('illumination_corrected')
    if quality.get('blur_risk'):
        strategies.append('sharpened')
    return tuple(dict.fromkeys(strategies))


def build_ocr_variants(image, names=None):
    """Build only named candidate variants; no transformation is applied blindly."""
    source = upscale_for_ocr(image)
    deskewed = None

    def get_deskewed():
        nonlocal deskewed
        if deskewed is None:
            deskewed, _ = correct_small_skew(source)
        return deskewed

    available = {
        'color': lambda: source,
        'grayscale': lambda: grayscale(source),
        'gaussian_blur': lambda: gaussian_blur(source),
        'median_blur': lambda: median_blur(source),
        'clahe': lambda: clahe(source),
        'adaptive_threshold': lambda: adaptive_threshold(source),
        'otsu_threshold': lambda: otsu_threshold(source),
        'sharpened': lambda: sharpen(source),
        'morphological_open': lambda: morphological_open(source),
        'deskewed': get_deskewed,
        'enhanced_color': lambda: enhanced_color(source),
        'illumination_corrected': lambda: correct_uneven_illumination(source),
        'deskewed_clahe': lambda: clahe(get_deskewed()),
        'deskewed_adaptive_threshold': lambda: adaptive_threshold(get_deskewed()),
    }
    selected = names or available.keys()
    return {name: available[name]() for name in selected}
