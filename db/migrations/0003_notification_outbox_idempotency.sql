-- Preserve existing notifications; only outbox-generated rows receive a source event.
ALTER TABLE notifications
  ADD COLUMN source_event_id CHAR(36) NULL AFTER body,
  ADD UNIQUE KEY uq_notifications_event_user_type (source_event_id, user_id, type);
