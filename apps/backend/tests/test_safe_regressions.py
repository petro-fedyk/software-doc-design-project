"""Focused regressions that do not open a database connection."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from pharmacy.api.views import CartView, GuestCartView
from pharmacy.api.serializers import CartChangeSerializer
from pharmacy.application.services import CustomerApplicationService, EventApplicationService
from pharmacy.infrastructure.repositories import DjangoEngagementRepository
from pharmacy import models as m


def test_guest_merge_accepts_unavailable_product_flag():
    serializer = CartChangeSerializer(data={
        "product_id": 2, "quantity": 1, "allow_unavailable": True,
    })
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["allow_unavailable"] is True


def test_guest_cart_removes_inactive_product_without_catalog_lookup():
    from django.core import signing

    request = APIRequestFactory().put(
        "/api/guest-cart/", {"product_id": 2, "quantity": 0}, format="json"
    )
    request.COOKIES["guest_cart"] = signing.dumps({"2": 1, "90": 3}, salt="guest-cart")
    with patch("pharmacy.api.views.get_object_or_404") as lookup:
        response = GuestCartView.as_view()(request)
    assert response.status_code == 200
    assert response.data == {"items": {"90": 3}}
    assert signing.loads(response.cookies["guest_cart"].value, salt="guest-cart") == {"90": 3}
    lookup.assert_not_called()


def test_guest_cart_still_rejects_adding_inactive_product():
    from django.http import Http404

    request = APIRequestFactory().put(
        "/api/guest-cart/", {"product_id": 2, "quantity": 1}, format="json"
    )
    with patch("pharmacy.api.views.get_object_or_404", side_effect=Http404) as lookup:
        response = GuestCartView.as_view()(request)
    assert response.status_code == 404
    lookup.assert_called_once_with(m.Products, id=2, is_active=True)


@pytest.mark.parametrize("root", [[], ["unexpected"], None, "text", 7])
def test_cart_rejects_non_object_json_root_with_400(root):
    if root is None:
        request = APIRequestFactory().put(
            "/api/cart/", "null", content_type="application/json"
        )
    else:
        request = APIRequestFactory().put("/api/cart/", root, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))

    response = CartView.as_view()(request)

    assert response.status_code == 400
    if root is None:
        assert "non_field_errors" in response.data
    else:
        assert response.data == {"non_field_errors": ["Expected a JSON object."]}


def test_outbox_notification_replay_uses_stable_deduplication_key():
    repository = DjangoEngagementRepository()
    order = SimpleNamespace(customer_id=22, id=81, status="PROCESSING")
    rows = {}

    def get_or_create(**kwargs):
        identity = (
            kwargs["source_event_id"],
            kwargs["user_id"],
            kwargs["type"],
        )
        if identity in rows:
            return rows[identity], False
        rows[identity] = kwargs["defaults"]
        return rows[identity], True

    with patch.object(m.Notifications.objects, "get_or_create", side_effect=get_or_create) as create:
        repository.notify_order(order, "event-123")
        repository.notify_order(order, "event-123")

    assert create.call_count == 2
    assert len(rows) == 1
    assert create.call_args_list[0].args == create.call_args_list[1].args == ()
    for call in create.call_args_list:
        assert call.kwargs["source_event_id"] == "event-123"
        assert call.kwargs["user_id"] == 22
        assert call.kwargs["type"] == "ORDER"
    assert [call.kwargs["defaults"]["body"] for call in create.call_args_list] == [
        "Order 81: PROCESSING",
        "Order 81: PROCESSING",
    ]


def test_outbox_event_id_reaches_notification_subscriber():
    notified = []
    order = SimpleNamespace(customer_id=22, id=81, status="CONFIRMED")

    class Uow:
        orders = SimpleNamespace(get=lambda _identifier: order)
        engagement = SimpleNamespace(
            notify_order=lambda row, event_id: notified.append((row.id, event_id))
        )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def commit(self):
            pass

    service = EventApplicationService(lambda: Uow(), MockGateway(), object())

    service.handle("order.confirmed", {"order_id": 81, "status": "CONFIRMED"}, "evt-81")

    assert notified == [(81, "evt-81")]


def test_customer_operation_restarts_whole_transaction_after_mysql_deadlock():
    state = {"commits": 0, "staged": [], "saved": []}

    class Uow:
        committed = False

        def __enter__(self):
            self.staged = []
            self.carts = SimpleNamespace(
                set_item=lambda customer_id, product_id, count: (
                    self.staged.append((customer_id, product_id, count))
                    or {"product_id": product_id, "quantity": count}
                )
            )
            return self

        def __exit__(self, exc_type, exc, traceback):
            if exc_type is None and self.committed:
                state["commits"] += 1
                if state["commits"] == 1:
                    raise Exception(1213, "Deadlock found when trying to get lock")
                state["saved"].extend(self.staged)
            return False

        def commit(self):
            self.committed = True

    actor = SimpleNamespace(customer=lambda: None, id=5)
    service = CustomerApplicationService(Uow)

    response = service.cart(actor, 9, 2)

    assert response == {"product_id": 9, "quantity": 2}
    assert state == {"commits": 2, "staged": [], "saved": [(5, 9, 2)]}


def test_personal_update_retry_preserves_consumed_input_fields():
    attempts = []
    commits = []

    class Uow:
        def __enter__(self):
            def save_personal(_customer_id, _kind, data):
                attempts.append(data.get("id"))
                data.pop("id", None)
                return {"id": 7}

            self.engagement = SimpleNamespace(save_personal=save_personal)
            return self

        def __exit__(self, exc_type, exc, traceback):
            if exc_type is None and self.committed:
                commits.append(True)
                if len(commits) == 1:
                    raise Exception(1213, "Deadlock")
            return False

        def commit(self):
            self.committed = True

    actor = SimpleNamespace(customer=lambda: None, id=5)
    service = CustomerApplicationService(Uow)
    request_data = {"id": 7, "product_id": 9, "interval_days": 30}

    service.personal(actor, "reminder", request_data)

    assert attempts == [7, 7]
    assert request_data["id"] == 7


def test_customer_operation_does_not_retry_non_deadlock_error():
    calls = []

    class FailingUow:
        def __enter__(self):
            self.carts = SimpleNamespace(
                set_item=lambda customer_id, product_id, count: {"quantity": count}
            )
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def commit(self):
            calls.append("commit")
            raise Exception(1205, "Lock wait timeout")

    actor = SimpleNamespace(customer=lambda: None, id=5)
    service = CustomerApplicationService(FailingUow)

    with pytest.raises(Exception) as error:
        service.cart(actor, 9, 2)

    assert error.value.args[0] == 1205
    assert calls == ["commit"]


def test_customer_operation_stops_after_three_deadlock_retries():
    attempts = []

    class DeadlockingUow:
        def __enter__(self):
            self.carts = SimpleNamespace(set_item=lambda *_: {"quantity": 2})
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def commit(self):
            attempts.append("commit")
            raise Exception(1213, "Deadlock")

    service = CustomerApplicationService(DeadlockingUow)
    actor = SimpleNamespace(customer=lambda: None, id=5)

    with pytest.raises(Exception) as error:
        service.cart(actor, 9, 2)

    assert error.value.args[0] == 1213
    assert len(attempts) == 4


def test_event_consumer_does_not_retry_external_gateway_effects():
    gateway_calls = []

    class Uow:
        orders = SimpleNamespace(
            get=lambda *_args, **_kwargs: SimpleNamespace(
                id=81, status="CONFIRMED", payment_method="CARD"
            )
        )
        payments = SimpleNamespace(
            get=lambda *_: {
                "status": "PENDING",
                "amount": "10.00",
                "idempotency_key": "key-12345",
            },
            settle=lambda *_: None,
        )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def commit(self):
            pass

    class Gateway:
        def authorize(self, *args):
            gateway_calls.append(args)
            raise Exception(1213, "Simulated downstream deadlock response")

    service = EventApplicationService(lambda: Uow(), Gateway(), object())

    with pytest.raises(Exception) as error:
        service.handle("payment.requested", {"order_id": 81, "payment_id": 9})

    assert error.value.args[0] == 1213
    assert len(gateway_calls) == 1


class MockGateway:
    def authorize(self, *args):
        raise AssertionError("Unexpected external gateway call")
