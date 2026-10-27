# 07 — Security and Code Quality

## Essential safeguards
- Server-side authorization for every privileged action; worker can only edit assigned pharmacy, network admin manages branches/accounts.
- Password hashes using an appropriate proven library; session cookies Secure/HttpOnly/SameSite for HTTPS deployments.
- CSRF protection for cookie-authenticated state-changing actions (HTML forms and fetch requests).
- Parameterized SQL/ORM, context-aware template escaping, validation of user inputs and file uploads.
- Use fake prescription identifiers and fake users in demo. Store minimum information; no real government medical integrations.
- Never collect or store full payment card details; simulate payment outcomes.
- Audit significant inventory, staff assignment and order-status changes.
- Payment and bonus processing idempotent; inventory reservation atomic.
- Avoid exposing development debug mode beyond local development.

## Quality rules
- Business logic stays out of Django routes and Django Templates templates.
- Favor straightforward Python classes/functions; create interfaces only at real boundaries.
- Use clear naming, type hints where valuable, explicit exceptions and concise docstrings.
- Avoid generic base repositories or enormous domain superclass trees.
- Cover order state transitions, permission restrictions, stock races, discount eligibility, delivery restrictions, payment failures, job retries and five patterns with tests.
- Do not overpromise legal compliance or use the mock implementation for actual medicine commerce.
