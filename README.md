# DocuScan AI

DocuScan AI converts photographed documents into searchable, editable digital
records. It combines image enhancement, adaptive OCR selection, document layout
analysis, structured field extraction, and export to PDF or editable DOCX.

## What it does

- Upload JPG or PNG documents up to 10 MB.
- Detect document boundaries and correct perspective when a page is visible.
- Improve scans with resizing, contrast enhancement, deskewing, and adaptive
  thresholding.
- Extract text with EasyOCR and retain word-level bounding boxes and confidence.
- Start with a fast colour OCR pass; use recovery preprocessing only when the
  initial result is weak.
- Analyse reading order, headings, paragraphs, candidate tables, and document
  type.
- Extract receipt/invoice details such as vendor, date, invoice number, subtotal,
  tax, currency, and total without inventing missing values.
- Preserve document history, OCR metadata, confidence, processing duration, and
  quality metrics.
- Export two reconstruction modes:
  - **Original layout:** approximate the detected geometry while preserving
    editable text.
  - **Clean layout:** produce a readable semantic document with structured
    sections and financial summary.
- Download reconstructed documents as PDF or editable DOCX.

## Tech stack

| Layer | Tools |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS, Axios, Lucide |
| Backend | Django, Django REST Framework |
| OCR and vision | EasyOCR, PyTorch, OpenCV, Pillow |
| Document processing | NumPy, ReportLab, python-docx |
| Storage | Django media storage and SQLite for local development |

## Architecture

```text
React dashboard
      |
      v
Django REST API
      |
      +--> upload validation --> perspective correction --> OCR candidate selection
      |                                              |
      |                                              v
      |                                layout + document understanding
      |                                              |
      +--> document history <-----------------------+
      |
      +--> clean/original reconstruction --> PDF / DOCX export
```

## Run locally

### 1. Backend

```powershell
cd "C:\DocuScan AI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\backend\manage.py migrate
python .\backend\manage.py runserver
```

The API starts at `http://127.0.0.1:8000`.

### 2. Frontend

Open a second terminal:

```powershell
cd "C:\DocuScan AI"
npm install
npm run dev
```

Vite starts the web app and proxies `/api` and `/media` to Django.

### 3. Environment variables for deployment

Copy `.env.example` and set the values in your hosting platform. Never commit
the production value of `DJANGO_SECRET_KEY`.

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-production-secret
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your-domain.example.com
```

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health/` | API health check |
| `POST` | `/api/documents/upload/` | Upload and process a document |
| `GET` | `/api/documents/` | List document history |
| `GET` | `/api/documents/<id>/` | Read document details and OCR data |
| `DELETE` | `/api/documents/<id>/` | Delete a document record |
| `POST` | `/api/documents/<id>/export/` | Create a PDF or DOCX export |

Example export request:

```json
{
  "format": "docx",
  "reconstruction_mode": "clean"
}
```

## Measuring OCR accuracy

Model confidence is not proof of correctness. The project includes a printed
document benchmark for retail receipts, invoices/bills, forms, and printed
pages. Each image must have a manually verified transcription before it is used
for evaluation.

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py benchmark_ocr --split development
.\.venv\Scripts\python.exe .\backend\manage.py benchmark_ocr --split holdout
```

The benchmark reports Character Error Rate (CER), Word Error Rate (WER), OCR
processing time, detection count, confidence, and preprocessing strategy.
See [the dataset guide](backend/documents/evaluation/README.md) for the required
40-sample development/holdout protocol.

## Quality checks

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py test documents
npm run build
```

## Resume-ready project description

> Built DocuScan AI, a full-stack intelligent document scanning platform using
> React, Django, OpenCV, and EasyOCR. Implemented perspective correction,
> adaptive OCR candidate selection, layout-aware document understanding,
> confidence and quality telemetry, verified CER/WER benchmarking, and PDF/DOCX
> reconstruction exports for photographed receipts, invoices, forms, and pages.

## Future improvements

- Add a verified 40+ image benchmark dataset and compare OCR engines on holdout
  CER/WER.
- Process long-running OCR jobs asynchronously with a queue and worker.
- Support PDFs, multi-page documents, authenticated private history, and cloud
  storage.
- Integrate a cloud document-recognition provider as an optional higher-accuracy
  backend for difficult handwriting and complex forms.
