# 08 — Docker Deployment Plan (Django)

## Runtime
Single Django application image, deployed as **two Compose services built from that same image**: `web` (Gunicorn WSGI) and `worker` (Django management command `process_outbox`). The worker is a process, not a microservice and not a separate codebase. This avoids fragile server-startup threads and double-dispatch across WSGI workers.

## Data
Initially SQLite stored in a named local Docker volume, shared between `web` and `worker`; both services must run on **the same Docker host**, not two independent machines. Configure SQLite WAL and busy timeout; short transactions. If write contention proves significant, migrate to PostgreSQL and introduce a `db` Compose service; domain code remains unchanged.

## Illustrative Compose design (not yet runnable)
```yaml
services:
  web:
    build: ./apps/backend
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4
    ports: ["${APP_PORT:-8000}:8000"]
    env_file: .env
    volumes: [pharmacy_data:/app/data]
  worker:
    build: ./apps/backend
    command: python manage.py process_outbox
    env_file: .env
    volumes: [pharmacy_data:/app/data]
    restart: unless-stopped
volumes:
  pharmacy_data:
```

## Setup and safety
Apply Django migrations explicitly before serving traffic; do not run concurrently in both services. Keep `SECRET_KEY` in `.env`, `DEBUG=False`, explicit `ALLOWED_HOSTS` and CSRF configuration. Never commit `.env` or real patient data. `docker compose up --build` must start the stack after setup; verify volume persistence and restart processing. Gunicorn is Linux-specific; use Docker on Windows/macOS.

## Portability claims
Moving to another host preserves source and schema through Docker, but copying a live SQLite volume requires a proper SQLite backup or stopped service. PostgreSQL migration needs DB configuration, schema migrations, data export/import, and transaction/locking tests.
