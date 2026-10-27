# ADR-001 — Modular Monolith and Minimal Tooling

**Status:** Accepted for design; not yet implemented.

**Context:** Coursework requires web UI, REST, persistent DB, GoF patterns, Git history, and documented architecture.

**Decision:** Django apps, Python backend, Django Templates/HTML/CSS/vanilla JS, SQLite and two Docker Compose processes (`web` and `worker`) using one image. Keep one deployable monolith; route -> service -> domain -> repository port -> SQLite implementation.

**Consequences:** Fast to implement and deploy; no distributed network complexity. SQLite single-writer and single dedicated background worker are acceptable for demo but not a general high-scale production architecture. Additional infrastructure requires demonstrated necessity.
