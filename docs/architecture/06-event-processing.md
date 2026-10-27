# 06 — Asynchronous Internal Events

## Decision
Use a durable SQLite outbox/jobs table and a **single background dispatcher** running as a separate Django management command in a second Compose service built from the same image. The HTTP request commits domain changes plus queued events, then returns. A dispatcher polls the DB on a short interval, finds due jobs, invokes registered observers, records success, retries transient failures.

## Why not ThreadPoolExecutor-only?
An in-memory queue loses pending events when a container restarts. A durable outbox adds one small table but avoids silent loss for important notices and bonus updates.

## Proposed `outbox_events` fields
`id`, `event_type`, `aggregate_id`, `payload_json`, `status` (PENDING/PROCESSING/DONE/FAILED), `attempts`, `available_at`, `created_at`, `processed_at`, `last_error`.

## Algorithm
1. Within checkout transaction persist aggregate and outbox event.
2. Commit; HTTP returns.
3. Worker polls PENDING due rows, claims one in a short transaction.
4. Invoke registered handlers outside the transaction.
5. Record outcome; retry with bounded backoff, record permanent failure.
6. Each handler uses an idempotency key (`event_id`, `handler_name`) to avoid duplicate bonus transactions or notifications after retries. For multi-handler events track outcomes per handler or fan out one job per handler.

## Critical constraints
- SQLite allows one writer at a time. Keep transactions short and configure a reasonable busy timeout; consider WAL mode for local disk.
- Avoid multiple process replicas with independent dispatchers. Use one `process_outbox` worker process; the web process never starts a dispatcher.
- Do not put SQLite WAL data on an NFS/network share. Persist `/app/data` via Docker named volume on local host.
- Worker must not rely on request context; the management command initializes Django normally.
- Job execution may occur later, at least once (not exactly once). Test crash/retry/duplicate scenarios.
- On graceful shutdown stop acquiring new jobs; unfinished jobs are recovered after restart.
- For non-essential reminders, use same dispatcher with `available_at`; no separate cron or Celery.

## No unnecessary complexity
Do not build a general distributed scheduler, Kafka protocol, pub/sub server, dynamic plugin loader, or multiple worker containers. If this lightweight queue proves beyond the time budget, synchronous local Observer may be used only after explicitly revising the asynchronous requirement and documenting its limitations.
