# Build the React UI, then run a Python 3.13 OCR service in one reproducible image.
FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install runtime system libraries required by OpenCV / PyTorch / docTR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libx11-6 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-production.txt ./

# Install CPU-optimized PyTorch to minimize image size and stay within 512MB RAM,
# then install remaining production packages.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-production.txt

# Pre-download docTR deep learning OCR model weights during build time so
# runtime inference is instant and never needs to download weights over the web.
RUN python -c "from doctr.models import ocr_predictor; ocr_predictor(det_arch='db_mobilenet_v3_large', reco_arch='crnn_mobilenet_v3_large', pretrained=True)"

COPY backend ./backend
COPY --from=frontend /app/dist ./dist
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput || true
EXPOSE 8000
CMD sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -"
