# DocuScan AI architecture

## Processing flow

```text
Upload → validation → quality metrics → perspective correction → preprocessing
→ OCR router → normalized detections → layout analysis → document understanding
→ versioned representation → human correction → reconstruction → PDF/DOCX/TXT
```

## OCR adapters

`backend/documents/services/ocr/` is the model boundary.

- `easy_ocr.py` is the active, lazy-loaded local baseline.
- `paddle_ocr.py` is an optional PP-OCRv5 adapter boundary. It is disabled in
  this Windows/Python 3.14 environment because PaddleOCR does not publish
  support for this Python version.
- `trocr.py` is reserved for cropped handwritten text lines; it is not used for
  full-page recognition.
- `ocr_router.py` resolves `OCR_DEFAULT_ENGINE`, preserves a local EasyOCR
  fallback, and attaches explicit warnings when fallback occurs.
- `result_normalizer.py` provides the stable detection contract used by layout,
  understanding, and export services.

## Data ownership

`Document` preserves original OCR results separately from `corrected_text` and
human-verified fields in `document_data`. Corrections never overwrite the OCR
evidence that produced the original result.

## Known limits

The project has no verified benchmark labels yet, so it makes no comparative
accuracy claims for EasyOCR, PaddleOCR, or TrOCR. PaddleOCR and TrOCR must be
installed and evaluated in a supported environment before being selected as
production engines.
