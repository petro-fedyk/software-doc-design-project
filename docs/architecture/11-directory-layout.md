> Current frontend architecture (2026-10-29): two independent portals, one Django API and one MySQL database. See [portal requirements, sessions and roles](../portals/ARCHITECTURE.md) and [page/API responsibility matrix](../portals/PAGE_API_MATRIX.md). Historical framework/database deployment assumptions below are superseded by that implementation.

# 11 — Proposed Django Module Layout

```text
apps/backend/
  manage.py
  config/                  # settings, urls, wsgi
  pharmacy/
    domain/                # pure Python entities, invariants, policies
    application/           # use cases, ports (Protocol), DTOs
    infrastructure/        # ORM models, Django repositories, mappers, UoW
    presentation/          # URLs, Django views/forms/admin
  ordering/                # same internal boundaries where needed
  inventory/
  payments/
  loyalty/
  notifications/
  composition.py          # builds concrete service dependencies
  templates/
  static/
  tests/
```

Feature packages may be collapsed when small. One Django app may own several related modules; do not generate dozens of directories without real use. Django model registration can re-export infrastructure models from an app `models.py` for autodiscovery/migrations; this is an intentional infrastructure integration, not a domain dependency.
