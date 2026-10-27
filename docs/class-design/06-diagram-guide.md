# 06 — Diagram rendering and editing conventions

All six native, editable pages are in [`Internet_Pharmacy_Class_Diagrams.drawio`](../diagrams/Internet_Pharmacy_Class_Diagrams.drawio), alongside the existing use-case file. The pages are System Class Overview, Strategy — Discounts, State — Order, Observer — Domain Events, Factory Method — Delivery, and Builder — Order Draft. The overview is intentionally high-level; the other five show pattern participants.

## Style
- Domain entities: white, dark border.
- Application services: pale blue.
- Port interfaces: pale teal; use `<<interface>>`.
- Infrastructure/ORM: light gray.
- GoF participants: Strategy blue, State green, Observer purple, Factory Method orange, Builder yellow. When a class spans multiple patterns, favor stereotypes over multiple fills.
- Use standard UML: attributes `-private: Type`, operations `+public(arg: Type): Return`; solid association vs dashed dependency; hollow realization triangles; filled composition diamonds; cardinalities near association ends.

## Editing steps (draw.io)
1. Open `Internet_Pharmacy_Class_Diagrams.drawio` in diagrams.net and use its page tabs to switch between the overview and pattern views.
2. Compare each pattern page to `04-pattern-realizations.md`; ensure connectors reach the intended class or interface and labels remain readable.
3. Keep diagram names, class names and IDs consistent across pages; do not invent REST method bodies or SQL schema here.
4. If the report requires images, export them from diagrams.net after manual corrections so they match the editable source.

No generated diagram is evidence of implemented code. Update after actual code structure is finalized.
