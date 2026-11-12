
import cv2

from backend.documents.services.image_processing import (
    load_image,
    find_document_corners,
    correct_perspective,
    enhance_document
)

from backend.documents.services.ocr_service import extract_text


# 1. Load and scan the document
image = load_image("sample_documents/receipt.png")

corners = find_document_corners(image)
scanned = correct_perspective(image, corners)


# 2. Create CLAHE-enhanced grayscale image
gray = cv2.cvtColor(scanned, cv2.COLOR_BGR2GRAY)

denoised = cv2.medianBlur(gray, 3)

clahe = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8)
)

clahe_image = clahe.apply(denoised)


# 3. Create adaptive threshold image
threshold_image = enhance_document(scanned)


# 4. Compare OCR results
images = {
    "SCANNED IMAGE": scanned,
    "CLAHE IMAGE": clahe_image,
    "THRESHOLD IMAGE": threshold_image
}

for image_name, processed_image in images.items():

    print("\n" + "=" * 50)
    print(image_name)
    print("=" * 50)

    results = extract_text(processed_image)

    confidences = [
        item["confidence"] for item in results
    ]

    if confidences:
        average_confidence = sum(confidences) / len(confidences)

        print("Detected text regions:", len(results))
        print("Average confidence:", round(average_confidence, 3))

    print("\nExtracted text:")

    for item in results:
        print(
            f'{item["text"]} '
            f'| Confidence: {item["confidence"]:.3f}'
        )
