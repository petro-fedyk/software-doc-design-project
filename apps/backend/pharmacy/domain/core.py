"""Business rules; imports only the Python standard library."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Protocol


class DomainError(Exception):
    def __init__(self, code, message=None, status=409):
        self.code, self.status = code, status
        super().__init__(message or code)


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > Decimal("9999999999.99"):
            raise ValueError()
        if result != result.quantize(Decimal(".01")):
            raise ValueError()
        return result.quantize(Decimal(".01"))
    except (ValueError, InvalidOperation):
        raise DomainError("INVALID_MONEY", status=400)


def quantity(value):
    if type(value) is not int or value < 1 or value > 10000:
        raise DomainError("INVALID_QUANTITY", status=400)
    return value


@dataclass(frozen=True)
class Actor:
    id: int
    role: str
    pharmacies: frozenset = frozenset()
    pharmacist: bool = False

    def customer(self):
        if self.role != "CUSTOMER":
            raise DomainError("CUSTOMER_REQUIRED", status=403)

    def admin(self):
        if self.role != "ADMIN":
            raise DomainError("ADMIN_REQUIRED", status=403)

    def branch(self, branch_id):
        if self.role == "ADMIN":
            return
        if self.role != "STAFF" or branch_id not in self.pharmacies:
            raise DomainError("PHARMACY_ASSIGNMENT_REQUIRED", status=403)

    def access(self, order):
        if self.role == "CUSTOMER":
            if order.customer_id != self.id:
                raise DomainError("NOT_YOUR_ORDER", status=403)
        else:
            self.branch(order.pharmacy_id)


@dataclass(frozen=True)
class Line:
    product_id: int
    name: str
    quantity: int
    price: Decimal
    prescription: bool = False
    cold: bool = False

    @property
    def total(self):
        return self.price * self.quantity


class DiscountPolicy(Protocol):
    def discount(self, line: Line) -> Decimal: ...


@dataclass(frozen=True)
class RateDiscount:
    rate: Decimal
    products: frozenset | None = None

    def discount(self, line):
        if not ProductEligibility.is_discount_allowed(line) or (
            self.products is not None and line.product_id not in self.products
        ):
            return Decimal("0.00")
        return (line.total * self.rate).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


class StandardDiscount(RateDiscount):
    pass


class SocialDiscount(RateDiscount):
    pass


class PremiumDiscount(RateDiscount):
    pass


class PromotionDiscount(RateDiscount):
    pass


class PricingService:
    def calculate(self, lines, policies):
        subtotal = sum((x.total for x in lines), Decimal("0.00"))
        discount = sum(
            (
                max((p.discount(x) for p in policies), default=Decimal("0.00"))
                for x in lines
            ),
            Decimal("0.00"),
        )
        return money(subtotal), money(discount)


class DeliveryHandler:
    method = "PICKUP"
    fee = Decimal("0.00")

    def fulfill(self, provider, order_id):
        return provider.prepare(order_id, self.method)

    def validate(self, lines):
        if self.method != "PICKUP" and any(x.prescription for x in lines):
            raise DomainError("PRESCRIPTION_PICKUP_ONLY")


class PickupHandler(DeliveryHandler):
    pass


class CourierHandler(DeliveryHandler):
    method = "COURIER"
    fee = Decimal("55.00")


class PostalHandler(DeliveryHandler):
    method = "POSTAL"
    fee = Decimal("75.00")


class DeliveryHandlerCreator:
    def create_handler(self):
        raise NotImplementedError


class PickupCreator(DeliveryHandlerCreator):
    def create_handler(self):
        return PickupHandler()


class CourierCreator(DeliveryHandlerCreator):
    def create_handler(self):
        return CourierHandler()


class PostalCreator(DeliveryHandlerCreator):
    def create_handler(self):
        return PostalHandler()


@dataclass(frozen=True)
class OrderDraft:
    customer_id: int
    pharmacy_id: int
    lines: tuple[Line, ...]
    method: str
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal

    @property
    def total(self):
        return money(self.subtotal - self.discount + self.shipping)


class OrderDraftBuilder:
    def __init__(self):
        self.fields = {}
        self.lines = []

    def with_customer(self, value):
        self.fields["customer_id"] = value
        return self

    def with_branch(self, value):
        self.fields["pharmacy_id"] = value
        return self

    def add_line(self, line):
        quantity(line.quantity)
        money(line.price)
        self.lines.append(line)
        return self

    def with_delivery(self, method):
        self.fields["method"] = method
        return self

    def with_total(self, subtotal, discount, shipping):
        self.fields.update(subtotal=subtotal, discount=discount, shipping=shipping)
        return self

    def build(self):
        if not self.lines or len(self.lines) != len({x.product_id for x in self.lines}):
            raise DomainError("INVALID_CART", status=400)
        if set(self.fields) != {
            "customer_id",
            "pharmacy_id",
            "method",
            "subtotal",
            "discount",
            "shipping",
        }:
            raise DomainError("INCOMPLETE_DRAFT", status=400)
        return OrderDraft(lines=tuple(self.lines), **self.fields)


class OrderState:
    targets = frozenset()

    def transition(self, order, target):
        if target not in self.targets:
            raise DomainError("INVALID_ORDER_TRANSITION")
        if target == "READY_FOR_PICKUP" and order.method != "PICKUP":
            raise DomainError("NOT_PICKUP")
        if target == "AWAITING_SHIPMENT" and order.method == "PICKUP":
            raise DomainError("NOT_SHIPPING")
        order.status = target


class PendingState(OrderState):
    targets = {"CONFIRMED", "CANCELLED"}


class ConfirmedState(OrderState):
    targets = {"PROCESSING", "CANCELLED"}


class ProcessingState(OrderState):
    targets = {"READY_FOR_PICKUP", "AWAITING_SHIPMENT", "CANCELLED"}


class ReadyState(OrderState):
    targets = {"COMPLETED", "CANCELLED"}


class AwaitingShipmentState(OrderState):
    targets = {"SHIPPED", "CANCELLED"}


class ShippedState(OrderState):
    targets = {"COMPLETED"}


class TerminalState(OrderState):
    pass


STATES = {
    "PENDING_CONFIRMATION": PendingState(),
    "CONFIRMED": ConfirmedState(),
    "PROCESSING": ProcessingState(),
    "READY_FOR_PICKUP": ReadyState(),
    "AWAITING_SHIPMENT": AwaitingShipmentState(),
    "SHIPPED": ShippedState(),
    "COMPLETED": TerminalState(),
    "CANCELLED": TerminalState(),
}


@dataclass
class Order:
    id: int
    customer_id: int
    pharmacy_id: int
    status: str
    method: str
    total: Decimal
    payment_method: str

    def transition(self, target):
        STATES[self.status].transition(self, target)


class EventPublisher:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, handler):
        self.subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type, handler):
        self.subscribers.get(event_type, []).remove(handler)

    def publish(self, event_type, payload):
        for handler in tuple(self.subscribers.get(event_type, [])):
            handler(payload)


@dataclass
class StockBalance:
    on_hand: int
    reserved: int
    version: int = 0

    def __post_init__(self):
        if self.on_hand < 0 or not 0 <= self.reserved <= self.on_hand:
            raise DomainError("INVENTORY_INVARIANT")

    @property
    def available(self):
        return self.on_hand - self.reserved

    def reserve(self, count):
        quantity(count)
        if count > self.available:
            raise DomainError("OUT_OF_STOCK")
        self.reserved += count
        self.version += 1

    def release(self, count, consume=False):
        quantity(count)
        if count > self.reserved:
            raise DomainError("INVENTORY_INVARIANT")
        self.reserved -= count
        if consume:
            self.on_hand -= count
        self.version += 1


class ProductEligibility:
    @staticmethod
    def is_discount_allowed(line):
        return not line.prescription


def earned_points(eligible_total, discount, rate):
    return int(max(Decimal("0"), eligible_total - discount) * rate)


def refund_points(earned, refunded, total, previous, balance):
    desired = min(earned, int(Decimal(earned) * refunded / total)) if total else 0
    delta = desired - previous
    if delta > balance:
        raise DomainError("LOYALTY_REVERSAL_REQUIRES_REVIEW")
    return max(0, delta), desired


def delivery_allowed(method, offer, rules):
    if method == "PICKUP":
        return True
    if offer["prescription"]:
        return False
    if not offer["cold"]:
        return bool(rules)
    if offer["min_c"] is None or offer["max_c"] is None:
        return False
    return any(
        r["cold_chain_supported"]
        and r["max_storage_min_c"] is not None
        and r["min_storage_max_c"] is not None
        and r["max_storage_min_c"] <= offer["min_c"]
        and r["min_storage_max_c"] >= offer["max_c"]
        for r in rules
    )
