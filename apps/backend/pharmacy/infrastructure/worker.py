"""Local simulated effects and event completion commit in one transaction.

SKIP LOCKED permits multiple workers. A crash rolls back the row lock and every
local effect. External delivery requires consumer idempotency before replacement.
"""

from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from pharmacy import models as m
from pharmacy.domain.core import Actor, DomainError


class OutboxWorker:
    def __init__(self, services):
        self.services = services

    def process_one(self):
        with transaction.atomic():
            event = (
                m.OutboxEvents.objects.select_for_update(skip_locked=True)
                .filter(
                    Q(status="PENDING", available_at__lte=timezone.now())
                    | Q(status="PROCESSING", locked_until__lte=timezone.now())
                )
                .order_by("id")
                .first()
            )
            if not event:
                return False
            try:
                with transaction.atomic():
                    self.services.events.handle(
                        event.event_type, event.payload, event.event_id
                    )
            except Exception as exc:
                event.attempts += 1
                event.status = "FAILED" if event.attempts >= 10 else "PENDING"
                event.available_at = timezone.now() + timedelta(
                    seconds=min(3600, 2**event.attempts)
                )
                event.last_error = getattr(exc, "code", type(exc).__name__)[:300]
            else:
                event.attempts += 1
                event.status = "DONE"
                event.last_error = None
            event.locked_until = None
            event.save()
            return True

    def maintenance(self):
        now = timezone.now()
        ids = list(
            m.Reservations.objects.filter(
                status="ACTIVE",
                expires_at__lte=now,
                order_item__order__status__in=[
                    "PENDING_CONFIRMATION",
                    "CONFIRMED",
                    "PROCESSING",
                    "READY_FOR_PICKUP",
                    "AWAITING_SHIPMENT",
                ],
            )
            .values_list("order_item__order_id", flat=True)
            .distinct()[:100]
        )
        for identifier in ids:
            try:
                with transaction.atomic():
                    self.services.orders.transition(
                        Actor(None, "ADMIN"), identifier, "CANCELLED"
                    )
                    m.Reservations.objects.filter(
                        order_item__order_id=identifier, status="CANCELLED"
                    ).update(status="EXPIRED")
            except DomainError:
                continue
        with transaction.atomic():
            reminders = list(
                m.Reminders.objects.select_for_update(skip_locked=True)
                .filter(is_active=True, next_run_at__lte=now)
                .order_by("id")[:100]
            )
            for reminder in reminders:
                if m.NotificationPreferences.objects.filter(
                    user_id=reminder.customer_id, reminders_enabled=True
                ).exists():
                    m.Notifications.objects.create(
                        user_id=reminder.customer_id,
                        type="REMINDER",
                        title="Your scheduled reminder",
                        body=f"Reminder for product {reminder.product_id}.",
                        created_at=now,
                    )
                reminder.next_run_at = now + timedelta(days=reminder.interval_days)
                reminder.save(update_fields=["next_run_at"])
