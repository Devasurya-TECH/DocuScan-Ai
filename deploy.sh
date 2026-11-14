#!/usr/bin/env bash
set -e

echo "=============================================="
echo "  DocuScan AI - Production Deployment Script  "
echo "=============================================="

# 1. Verify .env file exists
if [ ! -f .env ]; then
    echo "[-] Error: .env file not found!"
    echo "[-] Please copy .env.production.example to .env and configure your secrets."
    exit 1
fi

# 2. Verify Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "[-] Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 3. Build and launch all services in background
echo "[+] Building and launching DocuScan AI services..."
docker compose build --pull
docker compose up -d

# 4. Wait for healthy services
echo "[+] Waiting for database and services to report healthy..."
sleep 10
docker compose ps

# 5. Execute migrations
echo "[+] Running database migrations..."
docker compose exec -T web python manage.py migrate --noinput

# 6. Verify Health Endpoint
echo "[+] Checking API health endpoint..."
docker compose exec -T web python -c "
import urllib.request, json
try:
    res = urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode()
    print('Health Check Status:', json.loads(res)['status'])
except Exception as e:
    print('Health Check Warning:', e)
"

echo "=============================================="
echo "  Deployment Complete! Access your app at:    "
echo "  http://<YOUR_SERVER_IP> or https://<DOMAIN> "
echo "=============================================="
