# ADR-003 — Five Required GoF Patterns, No Adapter

**Status:** Accepted for design; revisit when building Stage 05 class diagrams.

**Decision:** Strategy for discount policies; State for order actions/transitions; Observer for outbox event subscribers; Factory Method for mock delivery handler construction; Builder for validated order drafts. No Adapter without a genuine incompatible interface.

**Guardrail:** The scope and correctness of each pattern must be demonstrated in tests and class diagrams. DI and Repository are not claimed as GoF patterns. Avoid a generic abstract factory hierarchy beyond the minimal Factory Method participants.
