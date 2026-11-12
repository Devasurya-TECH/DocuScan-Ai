
import time

import easyocr


# ==========================================
# 1. INITIALIZE EASYOCR
# ==========================================

reader = easyocr.Reader(
    ['en'],
    gpu=False
)


# ==========================================
# 2. EXTRACT TEXT
# ==========================================

def extract_text(image):
    """Use a balanced OCR configuration suitable for synchronous uploads.

    The pipeline can selectively try a recovery image when the first pass is
    weak. Greedy decoding keeps ordinary uploads responsive; exhaustive model
    comparisons belong in the offline CER/WER benchmark instead.
    """
    results = reader.readtext(
        image,
        decoder='greedy',
        canvas_size=2048,
        mag_ratio=1.0,
        contrast_ths=0.08,
        adjust_contrast=0.7,
        text_threshold=0.55,
        low_text=0.25,
        link_threshold=0.35,
    )

    extracted_data = []

    for result in results:

        bounding_box = result[0]
        text = result[1]
        confidence = result[2]

        extracted_data.append({

            "text": text,

            "confidence": float(confidence),

            "bounding_box": [
                [int(point[0]), int(point[1])]
                for point in bounding_box
            ]

        })

    return extracted_data


def run_ocr(image):
    """Run the current OCR engine and return results plus measured elapsed time."""
    started = time.perf_counter()
    detections = extract_text(image)
    return detections, time.perf_counter() - started
