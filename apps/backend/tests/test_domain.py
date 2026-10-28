from decimal import Decimal
import pytest
from pharmacy.domain.core import (
    Actor,
    DomainError,
    quantity,
    money,
    Line,
    PricingService,
    StandardDiscount,
    PromotionDiscount,
    Order,
    PostalCreator,
    OrderDraftBuilder,
    EventPublisher,
)


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "2"])
def test_quantity_rejects_invalid(value):
    with pytest.raises(DomainError):
        quantity(value)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", ".001"])
def test_money_rejects_invalid(value):
    with pytest.raises(DomainError):
        money(value)


def test_pricing_uses_best_discount_and_excludes_prescriptions():
    lines = [Line(1, "a", 2, Decimal("10")), Line(2, "rx", 1, Decimal("100"), True)]
    subtotal, discount = PricingService().calculate(
        lines, [StandardDiscount(Decimal(".1")), PromotionDiscount(Decimal(".2"))]
    )
    assert subtotal == 120 and discount == 4


@pytest.mark.parametrize("status", ["CANCELLED", "COMPLETED"])
def test_terminal_order_cannot_restart(status):
    order = Order(1, 1, 1, status, "PICKUP", Decimal("10"), "CARD")
    with pytest.raises(DomainError):
        order.transition("PROCESSING")


def test_factory_and_builder_enforce_prescription_pickup():
    line = Line(1, "rx", 1, Decimal("10"), True)
    with pytest.raises(DomainError):
        PostalCreator().create_handler().validate([line])
    with pytest.raises(DomainError):
        OrderDraftBuilder().add_line(line).build()


def test_observer_subscribe_unsubscribe():
    publisher = EventPublisher()
    seen = []
    handler = lambda payload: seen.append(payload)
    publisher.subscribe("x", handler)
    publisher.publish("x", 1)
    publisher.unsubscribe("x", handler)
    publisher.publish("x", 2)
    assert seen == [1]


def test_admin_does_not_gain_pharmacist_authority():
    assert not Actor(1, "ADMIN").pharmacist


def test_domain_and_application_have_no_framework_imports():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "pharmacy"
    for folder in ("domain", "application"):
        for path in (root / folder).glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [x.name for x in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                assert not any(
                    x.startswith(
                        (
                            "django",
                            "rest_framework",
                            "mysql",
                            "pharmacy.infrastructure",
                            "pharmacy.models",
                        )
                    )
                    for x in names
                ), path


def test_stock_balance_invariants_and_no_overselling():
    from pharmacy.domain.core import StockBalance

    stock = StockBalance(3, 0)
    stock.reserve(2)
    with pytest.raises(DomainError):
        stock.reserve(2)
    stock.release(2, consume=True)
    assert (stock.on_hand, stock.reserved, stock.available) == (1, 0, 1)
    with pytest.raises(DomainError):
        stock.release(1)
