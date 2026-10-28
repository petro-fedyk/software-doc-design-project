from decimal import Decimal
import pytest
from pharmacy.application.services import OrderApplicationService
from pharmacy.domain.core import Actor
from pharmacy.infrastructure.memory import ordering_store, MemoryOrderingUnitOfWork
from pharmacy.infrastructure.repositories import DjangoUnitOfWork


def checkout(pharmacy_id=1, product_id=1):
    return {
        "pharmacy_id": pharmacy_id,
        "fulfillment_method": "PICKUP",
        "payment_method": "CARD",
        "expected_total": "200.00",
        "items": [
            {"product_id": product_id, "quantity": 2, "expected_unit_price": "100.00"}
        ],
    }


def test_application_checkout_without_django_or_database():
    store = ordering_store()
    service = OrderApplicationService(lambda: MemoryOrderingUnitOfWork(store))
    result = service.place(Actor(1, "CUSTOMER"), checkout())
    assert result["total"] == Decimal("200.00")
    assert store["offers"][(1, 1)]["available"] == 8
    assert len(store["events"]) == 1


def test_application_rolls_back_if_outbox_write_fails():
    store = ordering_store()

    class BrokenUow(MemoryOrderingUnitOfWork):
        def __enter__(self):
            super().__enter__()

            def fail(*args):
                raise RuntimeError("Outbox unavailable")

            self.outbox.add = fail
            return self

    with pytest.raises(RuntimeError):
        OrderApplicationService(lambda: BrokenUow(store)).place(
            Actor(1, "CUSTOMER"), checkout()
        )
    assert store["orders"] == {} and store["offers"][(1, 1)]["available"] == 10


@pytest.fixture(params=["memory", "mysql"])
def adapter(request, records):
    r = records
    branch = r["branch"].id
    product = r["product"].id
    if request.param == "memory":
        store = ordering_store(branch, product)
        factory = lambda: MemoryOrderingUnitOfWork(store)
    else:
        factory = DjangoUnitOfWork
    return factory, Actor(r["customer"].id, "CUSTOMER"), checkout(branch, product)


def test_shared_order_repository_roundtrip_and_detached_entities(adapter):
    factory, actor, command = adapter
    result = OrderApplicationService(factory).place(actor, command)
    with factory() as uow:
        order = uow.orders.get(result["id"])
        assert order.total == Decimal("200.00") and order.status == "CONFIRMED"
        order.status = "PROCESSING"
        assert uow.orders.get(order.id).status == "CONFIRMED"
        uow.orders.save(order)
        uow.commit()
    with factory() as uow:
        assert uow.orders.get(order.id).status == "PROCESSING"


def test_shared_unit_of_work_rollback_and_inventory_contract(adapter):
    factory, actor, command = adapter
    result = OrderApplicationService(factory).place(actor, command)
    with factory() as uow:
        order = uow.orders.get(result["id"])
        order.status = "PROCESSING"
        uow.orders.save(order)
        uow.outbox.add("will.rollback", {})
    with factory() as uow:
        assert uow.orders.get(result["id"]).status == "CONFIRMED"
        assert (
            uow.inventory.offer(
                command["pharmacy_id"], command["items"][0]["product_id"]
            )["available"]
            == 8
        )
        uow.inventory.release(result["id"])
        uow.inventory.release(result["id"])
        uow.commit()
    with factory() as uow:
        assert (
            uow.inventory.offer(
                command["pharmacy_id"], command["items"][0]["product_id"]
            )["available"]
            == 10
        )
