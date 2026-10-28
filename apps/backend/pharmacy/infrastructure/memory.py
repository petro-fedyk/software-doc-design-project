"""In-memory ordering adapters for application tests, without Django or a database."""

from copy import deepcopy
from decimal import Decimal
from uuid import uuid4
from pharmacy.domain.core import DomainError, Order


class MemoryOrderRepository:
    def __init__(self, state):
        self.state = state

    def get(self, order_id, lock=False):
        if order_id not in self.state["orders"]:
            raise DomainError("NOT_FOUND", status=404)
        return deepcopy(self.state["orders"][order_id])

    def save(self, order):
        self.state["orders"][order.id] = deepcopy(order)

    def create(self, draft, payment_method, recipient):
        identifier = max(self.state["orders"], default=0) + 1
        order = Order(
            identifier,
            draft.customer_id,
            draft.pharmacy_id,
            "PENDING_CONFIRMATION",
            draft.method,
            draft.total,
            payment_method,
        )
        self.save(order)
        self.state["lines"][identifier] = draft.lines
        return order

    def prescription_required(self, order_id):
        return any(x.prescription for x in self.state["lines"][order_id])

    def prescription_approved(self, order_id):
        return self.state["verifications"].get(order_id, False)

    def verify_prescription(self, order_id, actor_id, approved):
        self.state["verifications"][order_id] = approved


class MemoryInventoryRepository:
    def __init__(self, state):
        self.state = state

    def offer(self, pharmacy_id, product_id, lock=False):
        offer = self.state["offers"].get((pharmacy_id, product_id))
        if offer is None:
            raise DomainError("NOT_FOUND", status=404)
        return deepcopy(offer)

    def reserve(self, order_id):
        order = self.state["orders"][order_id]
        for line in self.state["lines"][order_id]:
            offer = self.state["offers"][(order.pharmacy_id, line.product_id)]
            if offer["available"] < line.quantity:
                raise DomainError("OUT_OF_STOCK")
            offer["available"] -= line.quantity
        self.state["reservations"][order_id] = "ACTIVE"

    def release(self, order_id, consume=False):
        if self.state["reservations"].get(order_id) != "ACTIVE":
            return
        order = self.state["orders"][order_id]
        if not consume:
            for line in self.state["lines"][order_id]:
                self.state["offers"][(order.pharmacy_id, line.product_id)][
                    "available"
                ] += line.quantity
        self.state["reservations"][order_id] = "FULFILLED" if consume else "CANCELLED"


class MemoryOutboxRepository:
    def __init__(self, state):
        self.state = state

    def add(self, event_type, payload, event_id=None):
        identifier = event_id or str(uuid4())
        self.state["events"][identifier] = (event_type, deepcopy(payload))
        return identifier

    def find(self, event_id):
        event = self.state["events"].get(event_id)
        return deepcopy(event[1]) if event else None


class MemoryLoyaltyRepository:
    def policies(self, customer_id, promotion):
        if promotion:
            raise DomainError("INVALID_PROMOTION")
        return []


class MemoryDeliveryRepository:
    def allowed(self, method, offer):
        return method == "PICKUP" or not (offer["prescription"] or offer["cold"])


class MemoryOrderingUnitOfWork:
    """Implements the checkout subset of UnitOfWork; writes publish only on commit."""

    def __init__(self, state):
        self.store = state

    def __enter__(self):
        self.state = deepcopy(self.store)
        self.committed = False
        self.orders = MemoryOrderRepository(self.state)
        self.inventory = MemoryInventoryRepository(self.state)
        self.outbox = MemoryOutboxRepository(self.state)
        self.loyalty = MemoryLoyaltyRepository()
        self.delivery = MemoryDeliveryRepository()
        return self

    def commit(self):
        self.committed = True

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None and self.committed:
            self.store.clear()
            self.store.update(self.state)

    def audit(self, *args):
        self.state["audit"].append(args)


def ordering_store(pharmacy_id=1, product_id=1):
    return {
        "orders": {},
        "lines": {},
        "reservations": {},
        "events": {},
        "audit": [],
        "verifications": {},
        "offers": {
            (pharmacy_id, product_id): {
                "id": 1,
                "name": "Catalogue fixture",
                "price": Decimal("100.00"),
                "available": 10,
                "prescription": False,
                "cold": False,
                "min_c": None,
                "max_c": None,
            }
        },
    }
