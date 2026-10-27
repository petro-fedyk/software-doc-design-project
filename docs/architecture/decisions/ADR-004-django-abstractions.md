# ADR-004 — Django with Pure Domain and Ports

**Status:** Accepted (architecture proposal).

**Context:** The earlier Flask plan required custom auth/admin/ORM wiring. We need a lightweight UI, branch access control and easily testable database-independent business logic.

**Decision:** Django templates, Django Auth/Admin and ORM; pure Python domain objects; use-case services with constructor DI; focused ports/repositories/UoW and ORM mappers; SQLite initially; Docker Compose web + one management-command worker.

**Consequences:** Some additional mapping code for critical workflows, but no dependency on SQL/Django in business rules. Django Admin/read-only pages may use ORM directly. PostgreSQL transition still requires transaction and migration testing.
