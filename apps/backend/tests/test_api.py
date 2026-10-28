import pytest
from datetime import timedelta
import jwt
from django.conf import settings
from django.utils import timezone
from pharmacy import models as m
from pharmacy.composition import Services
from pharmacy.infrastructure.worker import OutboxWorker
from pharmacy.infrastructure.providers import SimulatedPaymentGateway


def command(r, rx=False, method="PICKUP", payment="CARD"):
    return {
        "pharmacy_id": r["branch"].id,
        "fulfillment_method": method,
        "payment_method": payment,
        "items": [
            {
                "product_id": r["rx" if rx else "product"].id,
                "quantity": 2,
                "expected_unit_price": "100.00",
            }
        ],
        "expected_total": "200.00" if method == "PICKUP" else "255.00",
        **(
            {
                "recipient": {
                    "name": "Student",
                    "phone": "000",
                    "destination": "Test address",
                }
            }
            if method != "PICKUP"
            else {}
        ),
    }


def create(client, r, **kwargs):
    response = client.post("/api/orders/", command(r, **kwargs), format="json")
    assert response.status_code == 201, response.data
    return response.data["id"]


def drain(services=None):
    worker = OutboxWorker(services or Services())
    for _ in range(100):
        if not worker.process_one():
            break


def test_complete_checkout_payment_loyalty_and_replay(records, client_for):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    identifier = create(customer, r)
    inventory = m.PharmacyInventory.objects.get(product=r["product"])
    assert inventory.reserved == 2
    response = customer.post(
        f"/api/orders/{identifier}/pay/",
        {"idempotency_key": "payment-key-123"},
        format="json",
    )
    assert response.status_code == 202, response.data
    assert m.Payments.objects.get(order_id=identifier).status == "PENDING"
    drain()
    assert m.Payments.objects.get(order_id=identifier).status == "SUCCEEDED"
    for status in ("PROCESSING", "READY_FOR_PICKUP", "COMPLETED"):
        response = staff.post(
            f"/api/orders/{identifier}/transition/", {"status": status}, format="json"
        )
        assert response.status_code == 200, response.data
    drain()
    inventory.refresh_from_db()
    assert (inventory.on_hand, inventory.reserved) == (8, 0)
    account = m.LoyaltyAccounts.objects.get(customer=r["customer"])
    assert account.balance == 10
    for _ in range(2):
        Services().events.order_changed({"order_id": identifier})
    account.refresh_from_db()
    assert account.balance == 10
    assert (
        m.LoyaltyTransactions.objects.filter(order_id=identifier, type="EARN").count()
        == 1
    )
    assert (
        staff.post(
            f"/api/orders/{identifier}/transition/",
            {"status": "CANCELLED"},
            format="json",
        ).status_code
        == 409
    )


def test_cancellation_releases_once_and_refunds(records, client_for):
    r = records
    client = client_for(r["customer"])
    identifier = create(client, r)
    assert (
        client.post(
            f"/api/orders/{identifier}/pay/",
            {"idempotency_key": "cancel-payment"},
            format="json",
        ).status_code
        == 202
    )
    drain()
    for _ in range(2):
        assert (
            client.post(
                f"/api/orders/{identifier}/transition/",
                {"status": "CANCELLED"},
                format="json",
            ).status_code
            == 200
        )
    drain()
    inventory = m.PharmacyInventory.objects.get(product=r["product"])
    assert (inventory.reserved, inventory.on_hand) == (0, 10)
    assert (
        m.Refunds.objects.filter(
            payment__order_id=identifier, status="SUCCEEDED"
        ).count()
        == 1
    )


def test_roles_assignment_ownership_and_prefixes(records, client_for):
    r = records
    identifier = create(client_for(r["customer"]), r)
    for user in ("other", "outsider"):
        assert client_for(r[user]).get(f"/api/orders/{identifier}/").status_code == 404
    assert (
        client_for(r["customer"])
        .post("/api/admin/promotions/", {}, format="json")
        .status_code
        == 403
    )
    assert (
        client_for(r["outsider"])
        .patch(
            f"/api/pharmacies/{r['branch'].id}/inventory/{r['product'].id}/",
            {"quantity": 5},
            format="json",
        )
        .status_code
        == 403
    )
    assert (
        client_for(r["customer"])
        .post(
            f"/api/orders/{identifier}/transition/",
            {"status": "PROCESSING"},
            format="json",
        )
        .status_code
        == 403
    )


def test_prescription_authority_and_handover(records, client_for, settings):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    identifier = create(customer, r, rx=True, payment="CASH_ON_DELIVERY")
    path = f"/api/orders/{identifier}/verify-prescription/"
    assert (
        client_for(r["admin"]).post(path, {"approved": True}, format="json").status_code
        == 403
    )
    assert staff.post(path, {"approved": True}, format="json").status_code == 403
    for status in ("PROCESSING", "READY_FOR_PICKUP"):
        assert (
            staff.post(
                f"/api/orders/{identifier}/transition/",
                {"status": status},
                format="json",
            ).status_code
            == 200
        )
    assert (
        staff.post(
            f"/api/orders/{identifier}/transition/",
            {"status": "COMPLETED"},
            format="json",
        ).status_code
        == 409
    )
    settings.PHARMACIST_IDS = frozenset([r["staff"].id])
    assert staff.post(path, {"approved": True}, format="json").status_code == 200
    assert (
        staff.post(
            f"/api/orders/{identifier}/transition/",
            {"status": "COMPLETED"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        customer.post(
            "/api/orders/", command(r, rx=True, method="COURIER"), format="json"
        ).status_code
        == 409
    )


def test_stale_price_and_partial_stock_failure_rollback(records, client_for):
    r = records
    client = client_for(r["customer"])
    data = command(r)
    data["items"][0]["expected_unit_price"] = "99"
    assert client.post("/api/orders/", data, format="json").status_code == 409
    assert not m.Orders.objects.exists()
    data = command(r)
    data["items"].append(
        {"product_id": r["rx"].id, "quantity": 100, "expected_unit_price": "100"}
    )
    assert client.post("/api/orders/", data, format="json").status_code == 409
    assert not m.Orders.objects.exists()
    assert not m.OutboxEvents.objects.exists()
    assert all(
        x == 0 for x in m.PharmacyInventory.objects.values_list("reserved", flat=True)
    )


def test_jwt_registration_expiry_tampering_and_no_role_escalation(records, client_for):
    r = records
    anonymous = client_for()
    login = anonymous.post(
        "/api/auth/token/",
        {"username": r["customer"].username, "password": "Long-Test-Password-123"},
        format="json",
    )
    assert login.status_code == 200, login.data
    token = login.data["access"]
    anonymous.credentials(HTTP_AUTHORIZATION="Bearer " + token)
    assert anonymous.get("/api/me/").data["role"] == "CUSTOMER"
    data = jwt.decode(
        token, settings.SECRET_KEY, algorithms=["HS256"], audience="pharmacy-api"
    )
    data["exp"] = 0
    anonymous.credentials(
        HTTP_AUTHORIZATION="Bearer "
        + jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")
    )
    assert anonymous.get("/api/me/").status_code == 401
    anonymous.credentials(HTTP_AUTHORIZATION="Bearer " + token[:-5] + "wrong")
    assert anonymous.get("/api/me/").status_code == 401
    anonymous.credentials()
    registration = {
        "username": "SS_new",
        "email": "new@example.test",
        "password": "Long-Test-Password-123",
        "full_name": "New User",
        "role": "ADMIN",
    }
    assert (
        anonymous.post("/api/auth/register/", registration, format="json").status_code
        == 400
    )
    registration.pop("role")
    response = anonymous.post("/api/auth/register/", registration, format="json")
    assert response.status_code == 201, response.data
    assert m.Users.objects.get(username="SS_new").role == "CUSTOMER"


def test_payment_failure_replay_and_no_secrets(records, client_for):
    r = records
    client = client_for(r["customer"])
    identifier = create(client, r)
    path = f"/api/orders/{identifier}/pay/"
    assert (
        client.post(
            path, {"idempotency_key": "unique-key", "cvv": "123"}, format="json"
        ).status_code
        == 400
    )
    for _ in range(2):
        assert (
            client.post(
                path, {"idempotency_key": "unique-key"}, format="json"
            ).status_code
            == 202
        )
    assert m.Payments.objects.count() == 1
    drain(Services(payment_gateway=SimulatedPaymentGateway(False)))
    assert m.Payments.objects.get().status == "FAILED"


def test_shipping_worker_and_refund_limit(records, client_for):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    identifier = create(customer, r, method="COURIER")
    assert (
        customer.post(
            f"/api/orders/{identifier}/pay/",
            {"idempotency_key": "ship-payment"},
            format="json",
        ).status_code
        == 202
    )
    drain()
    for status in ("PROCESSING", "AWAITING_SHIPMENT"):
        assert (
            staff.post(
                f"/api/orders/{identifier}/transition/",
                {"status": status},
                format="json",
            ).status_code
            == 200
        )
    assert (
        staff.post(f"/api/orders/{identifier}/ship/", {}, format="json").status_code
        == 202
    )
    drain()
    assert m.Orders.objects.get(id=identifier).status == "SHIPPED"
    assert (
        staff.post(
            f"/api/orders/{identifier}/transition/",
            {"status": "COMPLETED"},
            format="json",
        ).status_code
        == 200
    )
    drain()
    path = f"/api/orders/{identifier}/refund/"
    body = {"amount": "50.00", "reason": "Return", "idempotency_key": "refund-key-123"}
    for _ in range(2):
        assert staff.post(path, body, format="json").status_code == 202
    drain()
    assert m.Refunds.objects.count() == 1
    body.update(amount="255.00", idempotency_key="refund-key-456")
    assert staff.post(path, body, format="json").status_code == 409


def test_outbox_retry_rollback_and_dead_letter(records):
    from pharmacy.infrastructure.repositories import DjangoUnitOfWork

    with DjangoUnitOfWork() as uow:
        uow.outbox.add("unknown", {})
        uow.commit()
    worker = OutboxWorker(Services())
    assert worker.process_one()
    row = m.OutboxEvents.objects.get()
    assert row.status == "PENDING" and row.attempts == 1
    row.attempts = 9
    row.available_at = timezone.now() - timedelta(seconds=1)
    row.save()
    assert worker.process_one()
    row.refresh_from_db()
    assert row.status == "FAILED"


def test_inventory_cart_preferences_reminders_and_expiry(records, client_for):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    assert (
        customer.put(
            "/api/cart/", {"product_id": r["product"].id, "quantity": 2}, format="json"
        ).status_code
        == 200
    )
    assert (
        customer.post(
            "/api/preferences/",
            {"promotions_enabled": False, "reminders_enabled": True},
            format="json",
        ).status_code
        == 200
    )
    assert (
        customer.post(
            "/api/reminders/",
            {
                "product_id": r["product"].id,
                "interval_days": 5,
                "next_run_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        ).status_code
        == 200
    )
    assert (
        customer.post(
            "/api/availability-watches/",
            {"product_id": r["product"].id, "pharmacy_id": r["branch"].id},
            format="json",
        ).status_code
        == 200
    )
    assert (
        staff.patch(
            f"/api/pharmacies/{r['branch'].id}/inventory/{r['product'].id}/",
            {"quantity": 5},
            format="json",
        ).status_code
        == 200
    )
    drain()
    assert m.Notifications.objects.filter(type="AVAILABILITY").count() == 1
    identifier = create(customer, r)
    m.Reservations.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    OutboxWorker(Services()).maintenance()
    assert m.Orders.objects.get(id=identifier).status == "CANCELLED"
    assert m.Reservations.objects.get().status == "EXPIRED"
    assert customer.get("/api/notifications/").status_code == 200


def test_schema_mapping_does_not_create_django_tables(db):
    from django.db import connection
    from django.apps import apps

    names = set(connection.introspection.table_names())
    models = list(apps.get_app_config("pharmacy").get_models())
    assert len(models) == 31
    assert all(not model._meta.managed for model in models)
    assert not any(x.startswith(("auth_", "django_")) for x in names)
    for model in models:
        with connection.cursor() as cursor:
            actual = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, model._meta.db_table
                )
            }
        assert {f.column for f in model._meta.fields} == actual


def test_remaining_customer_and_admin_usecases(records, client_for):
    r = records
    customer = client_for(r["customer"])
    admin = client_for(r["admin"])
    guest = client_for()
    assert (
        guest.put(
            "/api/guest-cart/",
            {"product_id": r["product"].id, "quantity": 3},
            format="json",
        ).status_code
        == 200
    )
    assert guest.get("/api/guest-cart/").data["items"][str(r["product"].id)] == 3
    assert (
        customer.patch(
            "/api/profile/",
            {"full_name": "Updated Student", "preferred_pharmacy_id": r["branch"].id},
            format="json",
        ).status_code
        == 200
    )
    rx = customer.post(
        "/api/prescriptions/", {"display_label": "Course reference"}, format="json"
    )
    assert rx.status_code == 201 and rx.data["is_demo"]
    assert (
        client_for(r["other"])
        .delete(f"/api/prescriptions/{rx.data['id']}/")
        .status_code
        == 404
    )
    assert customer.delete(f"/api/prescriptions/{rx.data['id']}/").status_code == 204
    order_id = create(customer, r)
    assert (
        customer.post(f"/api/orders/{order_id}/reorder/", {}, format="json").status_code
        == 200
    )
    assert customer.get("/api/cart/").data["items"][0]["quantity"] == 2
    assert customer.get("/api/admin/statistics/").status_code == 403
    assert admin.get("/api/admin/statistics/").status_code == 200
    assert admin.get("/api/admin/audit/").status_code == 200
    assert (
        client_for(r["outsider"])
        .get(f"/api/pharmacies/{r['branch'].id}/statistics/")
        .status_code
        == 403
    )
    assert (
        client_for(r["staff"])
        .get(f"/api/pharmacies/{r['branch'].id}/audit/")
        .status_code
        == 200
    )
    assert guest.get("/api/payment-methods/").data["simulated"]
    staff = admin.post(
        "/api/admin/users/",
        {
            "username": "not-prefixed",
            "email": "newstaff@example.test",
            "password": "Safe-Staff-Password-123",
            "role": "STAFF",
            "is_active": True,
        },
        format="json",
    )
    assert staff.status_code == 201 and "password" not in staff.data
    assignment = admin.post(
        "/api/admin/assignments/",
        {"user": staff.data["id"], "pharmacy": r["branch"].id, "is_active": True},
        format="json",
    )
    assert assignment.status_code == 201, assignment.data
    assert guest.get("/api/schema/").status_code == 200
    assert guest.get("/api/docs/").status_code == 200


def test_cold_chain_delivery_rule_is_enforced(records, client_for):
    r = records
    r["product"].storage_min_c = 2
    r["product"].storage_max_c = 8
    r["product"].save()
    customer = client_for(r["customer"])
    body = command(r, method="COURIER")
    assert customer.post("/api/orders/", body, format="json").status_code == 409
    m.DeliveryRules.objects.create(
        method="COURIER",
        requires_cold_chain=True,
        cold_chain_supported=True,
        enabled=True,
        max_storage_min_c=2,
        min_storage_max_c=8,
    )
    assert customer.post("/api/orders/", body, format="json").status_code == 201


def test_deactivated_user_and_changed_role_are_checked_per_request(records, client_for):
    r = records
    client = client_for(r["admin"])
    r["admin"].role = "CUSTOMER"
    r["admin"].save()
    assert client.get("/api/admin/users/").status_code == 403
    r["admin"].is_active = False
    r["admin"].save()
    assert client.get("/api/me/").status_code == 401


def test_worker_rolls_back_partial_handler_effect_before_retry(records):
    from pharmacy.infrastructure.repositories import DjangoUnitOfWork

    r = records
    with DjangoUnitOfWork() as uow:
        uow.outbox.add("test.failure", {})
        uow.commit()

    class BrokenEvents:
        def handle(self, *args):
            m.Notifications.objects.create(
                user=r["customer"],
                type="ORDER",
                title="Transient",
                body="Must roll back",
                created_at=timezone.now(),
            )
            raise RuntimeError("Simulated crash after local side effect")

    class BrokenServices:
        events = BrokenEvents()

    assert OutboxWorker(BrokenServices()).process_one()
    assert not m.Notifications.objects.exists()
    assert m.OutboxEvents.objects.get().attempts == 1


def test_actual_mysql_transaction_rolls_back_on_outbox_failure(records):
    from pharmacy.application.services import OrderApplicationService
    from pharmacy.api.auth import actor
    from pharmacy.infrastructure.repositories import DjangoUnitOfWork

    r = records

    class BrokenUow(DjangoUnitOfWork):
        def __enter__(self):
            super().__enter__()

            def fail(*args, **kwargs):
                raise RuntimeError("Simulated outbox storage failure")

            self.outbox.add = fail
            return self

    with pytest.raises(RuntimeError):
        OrderApplicationService(BrokenUow).place(actor(r["customer"]), command(r))
    assert not m.Orders.objects.exists() and not m.Reservations.objects.exists()
    assert m.PharmacyInventory.objects.get(product=r["product"]).reserved == 0


def test_loyalty_snapshot_survives_rate_change_and_restrictions_are_locked(
    records, client_for
):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    admin = client_for(r["admin"])
    identifier = create(customer, r, payment="CASH_ON_DELIVERY")
    response = admin.patch(
        f"/api/products/{r['product'].id}/",
        {"prescription_required": True},
        format="json",
    )
    assert response.status_code == 409
    for status in ("PROCESSING", "READY_FOR_PICKUP", "COMPLETED"):
        assert (
            staff.post(
                f"/api/orders/{identifier}/transition/",
                {"status": status},
                format="json",
            ).status_code
            == 200
        )
    r["tier"].bonus_rate = ".99"
    r["tier"].save()
    drain()
    assert m.LoyaltyAccounts.objects.get(customer=r["customer"]).balance == 10
    assert (
        client_for().get(f"/api/products/{r['product'].id}/availability/").status_code
        == 200
    )


def test_inventory_adjustment_cannot_consume_reserved_stock(records, client_for):
    r = records
    customer = client_for(r["customer"])
    staff = client_for(r["staff"])
    create(customer, r)
    path = f"/api/pharmacies/{r['branch'].id}/inventory/{r['product'].id}/"
    assert staff.patch(path, {"adjustment": -9}, format="json").status_code == 409
    inventory = m.PharmacyInventory.objects.get(product=r["product"])
    assert (inventory.on_hand, inventory.reserved) == (10, 2)
    assert staff.patch(path, {"adjustment": -3}, format="json").status_code == 200
    inventory.refresh_from_db()
    assert (inventory.on_hand, inventory.reserved) == (7, 2)
    assert m.InventoryMovements.objects.get(inventory=inventory).reason == "ADJUSTMENT"


def test_promotion_notifications_require_opt_in(records, client_for):
    r = records
    admin = client_for(r["admin"])
    m.NotificationPreferences.objects.create(
        user=r["customer"], promotions_enabled=True, reminders_enabled=False
    )
    m.NotificationPreferences.objects.create(
        user=r["other"], promotions_enabled=False, reminders_enabled=False
    )
    response = admin.post(
        "/api/admin/promotions/",
        {
            "code": "COURSE5",
            "description": "Course offer",
            "discount_rate": ".05",
            "starts_at": (timezone.now() - timedelta(days=1)).isoformat(),
            "ends_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "is_active": True,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    drain()
    assert list(
        m.Notifications.objects.filter(type="PROMOTION").values_list(
            "user_id", flat=True
        )
    ) == [r["customer"].id]
