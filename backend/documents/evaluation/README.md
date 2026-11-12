# Printed-document OCR benchmark

This is DocuScan AI's evidence set for improving OCR. It is deliberately
separate from upload-time processing: a preprocessing change is only an
improvement when it lowers CER/WER on the untouched holdout images.

## Target corpus

| Category | Development | Holdout | Total |
| --- | ---: | ---: | ---: |
| `retail_receipts` | 7 | 3 | 10 |
| `invoices_bills` | 7 | 3 | 10 |
| `printed_forms` | 7 | 3 | 10 |
| `printed_pages` | 7 | 3 | 10 |
| **Total** | **28** | **12** | **40** |

Place each source image in `dataset/<category>/images/` and a manually checked
UTF-8 transcription with the same basename in `ground_truth/`.

```text
dataset/retail_receipts/
  images/receipt_001.jpg
  ground_truth/receipt_001.txt
```

The transcription must reproduce visible text, meaningful line breaks,
punctuation, quantities, dates, and currency. It must not be copied from an
OCR result without a person checking it against the source image. Redact or
use consented documents only.

## Manifest

After verifying a pair, add it to `dataset_manifest.json`:

```json
{
  "id": "receipt_001",
  "category": "retail_receipts",
  "split": "development"
}
```

Use exactly 7 development and 3 holdout examples per category. Never tune a
strategy using a holdout image.

## Running the benchmark

From `C:\DocuScan AI`:

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py benchmark_ocr --split development
.\.venv\Scripts\python.exe .\backend\manage.py benchmark_ocr --split holdout
```

The runner validates every manifest pair and writes JSON results under
`evaluation/results/`. It reports per-sample and per-category CER, WER,
processing time, detection count, and average confidence for each strategy.

Confidence helps select a candidate but is not accuracy. Only CER/WER against
these verified labels can establish an improvement.

`handwritten_notes/` remains available for a later, separately reported
handwriting benchmark; it is intentionally excluded from this printed-first
milestone.
