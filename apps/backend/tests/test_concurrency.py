"""Real connections and committed transactions; never run against the learning DB."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from django.conf import settings
from django.db import connections, transaction
from django.utils import timezone
from pharmacy import models as m
from pharmacy.application.services import (
    OrderApplicationService,
    PaymentApplicationService,
)
from pharmacy.domain.core import Actor, DomainError
from pharmacy.infrastructure.repositories import DjangoUnitOfWork
from pharmacy.infrastructure.worker import OutboxWorker
from pharmacy.composition import Services


def test_concurrent_backend_checkout_payment_and_worker(django_db_blocker):
    assert settings.DATABASES["default"]["NAME"].endswith("_test")
    with django_db_blocker.unblock():
        tag = uuid4().hex[:10]
        now = timezone.now()
        with transaction.atomic():
            user = m.Users.objects.create(
                username=tag,
                email=tag + "@example.test",
                password="!",
                role="CUSTOMER",
                is_active=True,
                is_staff=False,
                created_at=now,
            )
            branch = m.Pharmacies.objects.create(
                code=tag, name=tag, address="Test", city="Test", is_active=True
            )
            category = m.Categories.objects.create(name=tag)
            maker = m.Manufacturers.objects.create(name=tag)
            product = m.Products.objects.create(
                sku=tag,
                name=tag,
                category=category,
                manufacturer=maker,
                prescription_required=False,
                is_active=True,
            )
            inventory = m.PharmacyInventory.objects.create(
                pharmacy=branch,
                product=product,
                unit_price=100,
                on_hand=3,
                reserved=0,
                is_listed=True,
                version=0,
                updated_at=now,
            )
        principal = Actor(user.id, "CUSTOMER")
        command = {
            "pharmacy_id": branch.id,
            "fulfillment_method": "PICKUP",
            "payment_method": "CARD",
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                    "expected_unit_price": "100.00",
                }
            ],
            "expected_total": "200.00",
        }

        def run_two(operation):
            barrier = Barrier(2)

            def task():
                try:
                    barrier.wait(timeout=10)
                    return operation()
                except DomainError as exc:
                    return exc.code
                finally:
                    connections.close_all()

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(task) for _ in range(2)]
                return [f.result(timeout=20) for f in futures]

        try:
            results = run_two(
                lambda: OrderApplicationService(DjangoUnitOfWork).place(
                    principal, command
                )
            )
            assert sum(isinstance(x, dict) for x in results) == 1, results
            assert "OUT_OF_STOCK" in results
            order_id = next(x["id"] for x in results if isinstance(x, dict))
            inventory.refresh_from_db()
            assert inventory.reserved == 2 and inventory.on_hand == 3
            payments = run_two(
                lambda: PaymentApplicationService(DjangoUnitOfWork).request(
                    principal, order_id, "concurrent-" + tag
                )
            )
            assert payments[0]["id"] == payments[1]["id"]
            assert m.Payments.objects.filter(order_id=order_id).count() == 1
            # Two independent consumers claim distinct pending rows, with no duplicate effects.
            run_two(lambda: OutboxWorker(Services()).process_one())
            while OutboxWorker(Services()).process_one():
                pass
            assert m.Payments.objects.get(order_id=order_id).status == "SUCCEEDED"
            assert m.Notifications.objects.filter(user=user).count() == 1
            assert (
                m.OutboxEvents.objects.filter(
                    payload__order_id=order_id, status="DONE"
                ).count()
                == 2
            )
        finally:
            with transaction.atomic():
                orders = m.Orders.objects.filter(customer=user)
                order_ids = list(orders.values_list("id", flat=True))
                m.OutboxEvents.objects.filter(payload__order_id__in=order_ids).delete()
                m.AuditEntries.objects.filter(actor=user).delete()
                m.Notifications.objects.filter(user=user).delete()
                m.Reservations.objects.filter(order_item__order__in=orders).delete()
                m.OrderItems.objects.filter(order__in=orders).delete()
                m.Deliveries.objects.filter(order__in=orders).delete()
                m.Payments.objects.filter(order__in=orders).delete()
                orders.delete()
                inventory.delete()
                product.delete()
                category.delete()
                maker.delete()
                branch.delete()
                user.delete()
