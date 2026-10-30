# 08 — Deployment

Two independent Node static/proxy processes serve Customer Portal at 4173 and Management Portal at 4174. Django/Gunicorn at 8000 and the management-command outbox worker share one backend image, one configuration and the original MySQL volume. The worker is not a separate business service.

Run the existing API/worker with `docker compose -f compose.yaml -f compose.backend.yaml up --build -d`, then `node apps/start-portals.mjs`. Each frontend may instead be started separately. Optional `compose.portals.yaml` adds the two frontend services to the same Compose deployment. Frontend containers use `API_ORIGIN=http://backend:8000`; host processes use `http://127.0.0.1:8000`.

Backend startup runs `bootstrap_admin` before Gunicorn. It uses the existing schema and skips creation if any ADMIN exists. Database migrations are explicit SQL migrations; no automatic migration, database cloning or reset is performed by frontend startup.

The frontend proxies provide same-origin browser access, so Django CORS wildcard configuration is unnecessary. Loopback bindings are the coursework default. Port separation does not replace RBAC. TLS, VPN/private networks and deployment allowlists are future production options.

See [exact start/stop commands](../portals/DEMONSTRATION.md) and the editable [portal diagrams](../diagrams/Internet_Pharmacy_Portals.drawio).
