# DocuScan AI OCR production profile

The application deliberately separates its API process from heavyweight OCR
workers. This avoids one slow model download or a damaged photo blocking every
web request.

## Recommended worker setup

Use Python 3.11-3.13 for the OCR worker. Install the base application
requirements plus `requirements-ocr-production.txt`. Then set:

```env
OCR_DEFAULT_ENGINE=paddleocr
OCR_LANGUAGES=en,hi
OCR_DEVICE=cpu
```

Use a GPU worker only after a benchmark proves a meaningful latency benefit.
PaddleOCR is the printed-document primary engine. EasyOCR remains a safe local
fallback. TrOCR is reserved for detected handwritten line crops, not a whole
page.

## Accuracy policy

Do not promote a model or preprocessing strategy because its confidence is
higher. Promote it only when the untouched holdout dataset improves CER/WER,
layout reading order, and p95 latency for the target document category.

## High-value benchmark slices

- Hindi newspapers and printed Devanagari documents
- English receipts, invoices, and forms
- Full-frame scans with no visible paper background
- Glare, shadow, blur, perspective, and low-resolution phone photos
- Multi-column pages and tables

Record the source language, model, preprocessing strategy, CER, WER, detection
count, processing time, and manual layout review result for every sample.
