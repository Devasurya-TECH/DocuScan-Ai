# DocuScan AI — High-Performance Document OCR & Conversion Platform

DocuScan AI is an intuitive, production-grade document processing platform designed with a clean, focused workflow:

**Upload a document → Extract complete text → Allow text correction → Convert and download as TXT, DOCX, or PDF.**

---

## Key Highlights

- **docTR Deep Learning OCR:** Powered by Mindee docTR (`db_mobilenet_v3_large` detection + `crnn_mobilenet_v3_large` recognition) running PyTorch inference in **1.8–2.2 seconds** ($10\times$ faster than legacy EasyOCR) with zero C++ compilation dependencies and superior recognition of numbers, dates, and Latin text.
- **Intelligent Preprocessing:** Automatic dimension downscaling (bounds at 2048px to prevent CPU stalls), contrast-adaptive edge detection, CLAHE enhancement, and perspective correction.
- **Multi-Page & Scanned PDF Support:** Digital PDF direct stream extraction with intelligent fallback to raster rendering and docTR OCR for scanned pages.
- **Asynchronous Architecture:** Background processing powered by Celery 5.4 and Redis 7, with live stage tracking and polling.
- **Streamlined 4-Step User Workflow:**
  1. **Upload:** Clean file selector supporting PNG, JPG, JPEG, and PDF (up to 15 MB) with file metadata validation.
  2. **Processing:** Real background progress indicators with stage reporting (Upload → Boundary Detection → docTR Inference → Layout Processing).
  3. **Extracted Text Editor:** Large, distraction-free monospace text editor with character and word counters, 1-click Save Corrections, Copy to Clipboard, Select All, and Reprocess.
  4. **Convert & Download:** Instant 1-click downloads for plain text (`.txt`), Microsoft Word (`.docx` with native paragraph elements), and searchable digital PDF (`.pdf` via ReportLab).
- **Secure Architecture:** Multi-tenant JWT authentication (SimpleJWT), magic-byte file security validation, path-traversal guards, and tenant document isolation.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite 6, Tailwind CSS 3, Axios, Lucide Icons, React Router 7 |
| **Backend API** | Python 3.13/3.14, Django 5.1/6.1, Django REST Framework, SimpleJWT |
| **Primary OCR Engine** | Mindee docTR (PyTorch backend, MobileNetV3 DBNet + CRNN) |
| **Secondary/Specialized** | TrOCR (Hugging Face Transformers for handwriting), EasyOCR (fallback) |
| **Document Conversion** | python-docx (native Word DOCX), ReportLab (PDF), PyPDF |
| **Vision & Image** | OpenCV (headless), NumPy, Pillow |
| **Background Queues** | Celery 5.4, Redis 7 |
| **Containerization** | Docker, Docker Compose |

---

## Quick Start (Local Development)

### 1. Backend Setup

```powershell
# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements-production.txt

# Run migrations
python backend/manage.py migrate

# Start Django development server
python backend/manage.py runserver 127.0.0.1:8000
```

> **Default Demo Account:**
> - Username: `demo`
> - Password: `demo1234`

### 2. Celery Worker (Optional for Async Jobs)

```powershell
# In a separate terminal with Redis running:
celery -A config worker -l INFO --concurrency=2
```

### 3. Frontend Setup

```powershell
# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## Automated Verification

### Backend Test Suite
```powershell
$env:PYTHONPATH="backend"
$env:DJANGO_SETTINGS_MODULE="config.settings"
.\.venv\Scripts\python.exe backend\manage.py test documents
```
All 36 unit and integration tests execute and pass in under 2.5 seconds.

### Frontend Production Build
```powershell
npm run build
```
Vite production build transforms 1,665 modules and generates optimized production assets with zero errors.

---

## Production Deployment with Docker Compose

```bash
docker compose up -d --build
```

Services started:
- `web`: Gunicorn serving the Django API and static assets on port 8000.
- `celery_worker`: Celery background worker processing async OCR tasks.
- `redis`: Redis 7 Alpine cache and broker on port 6379.
- `postgres`: PostgreSQL 16 Alpine database.
