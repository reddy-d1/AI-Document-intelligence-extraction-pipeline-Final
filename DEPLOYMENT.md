# Document Intelligence Pipeline: Production Deployment Guide

Complete instructions for deploying the AI Document Intelligence & Extraction Pipeline to production environments.

---

## 1. Production Architecture Overview

The system runs as a containerized microservices stack managed via Docker Compose:

```
                  ┌────────────────────────┐
                  │   Nginx (Port 80/443)  │
                  └───────────┬────────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
    ┌──────────▼──────────┐       ┌──────────▼──────────┐
    │  React SPA Assets   │       │ FastAPI Backend (x4)│
    └─────────────────────┘       └──────────┬──────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
               ┌──────────▼──────────┐ ┌─────▼─────┐ ┌──────────▼──────────┐
               │  Celery Worker (x4) │ │ PostgreSQL│ │  Redis Queue/Cache │
               └─────────────────────┘ └───────────┘ └────────────────────┘
```

---

## 2. Environment Configuration

Create `.env.production` in the root directory:

```env
POSTGRES_USER=docintel_admin
POSTGRES_PASSWORD=your_secure_db_password_here
POSTGRES_DB=doc_intelligence_prod

REDIS_PASSWORD=your_secure_redis_password_here

ANTHROPIC_API_KEY=sk-ant-api03-...

JWT_SECRET_KEY=your_secure_random_jwt_secret_key_here
STORAGE_DIR=/app/storage
```

---

## 3. Deployment Steps

### Step 1: Clone Repository & Build Containers
```bash
git clone https://github.com/your-org/document-intelligence.git
cd document-intelligence

# Build and start containers in detached mode
docker-compose -f docker-compose.prod.yml up -d --build
```

### Step 2: Apply Database Migrations
```bash
docker exec -it doc_intel_backend_prod alembic upgrade head
```

### Step 3: Verify Deep System Health
```bash
curl http://localhost/health/deep
```
Expected Output:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "storage": "healthy",
  "disk_free_gb": 45.2
}
```

---

## 4. Security & Rate Limiting Enforcement

- **Rate Limits**:
  - `/api/v1/documents/upload`: Limited to 10 requests / second.
  - `/api/`: Limited to 30 requests / second.
- **Security Headers**: HSTS, CSP, X-Frame-Options (`SAMEORIGIN`), X-Content-Type-Options (`nosniff`).
- **File Validation**: Header Magic Bytes signature inspection (`%PDF`, `\x89PNG`, `\xFF\xD8\xFF`, `PK\x03\x04`).

---

## 5. SSL / TLS Certificate Setup (Certbot)

To configure HTTPS with Let's Encrypt:

```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d docintel.yourdomain.com
```
