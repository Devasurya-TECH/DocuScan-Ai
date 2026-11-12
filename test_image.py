
import cv2
import matplotlib.pyplot as plt

from backend.documents.services.image_processing import (
    load_image,
    find_document_corners,
    correct_perspective,
    enhance_document
)

# Load original image
image = load_image("sample_documents/receipt.png")

# Detect document
corners = find_document_corners(image)

# Correct perspective
scanned = correct_perspective(
    image,
    corners
)

# Enhance document
enhanced = enhance_document(scanned)

# Display results
plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
plt.imshow(
    cv2.cvtColor(scanned, cv2.COLOR_BGR2RGB)
)
plt.title("Perspective Corrected")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(enhanced, cmap="gray")
plt.title("Enhanced Document")
plt.axis("off")

plt.tight_layout()
plt.show()
