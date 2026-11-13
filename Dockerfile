# Build the React UI, then run a Python 3.13 OCR service in one reproducible image.
FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements-production.txt ./
RUN pip install --upgrade pip && pip install -r requirements-production.txt
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput || true
CMD sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 300"
