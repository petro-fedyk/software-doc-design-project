# software-doc-design-project

## Domain analysis (Stage 03)

See the [Stage 03 domain analysis](docs/domain/README-stage-03.md) and its [conceptual domain model](docs/diagrams/domain/source/domain-model.mmd).

## Architecture (Stage 04)

See the [Stage 04 architecture overview](docs/architecture/01-overview.md).

## UML class design (Stage 05)

See the [Stage 05 class design guide](docs/class-design/README.md) and the six-page editable [UML class diagram file](docs/diagrams/Internet_Pharmacy_Class_Diagrams.drawio).

## Запуск проєкту

Повна покрокова інструкція для запуску з нуля: [docs/RUN_FROM_ZERO.md](docs/RUN_FROM_ZERO.md).

## Django backend (Phase 2)

See the [backend setup and API guide](docs/backend/README.md), [use-case traceability](docs/backend/architecture-and-traceability.md), and [schema proposals](docs/backend/schema-proposals.md). Start the API and asynchronous worker with `docker compose -f compose.yaml -f compose.backend.yaml up --build -d`. API documentation is served at `http://127.0.0.1:8000/api/docs/`.
