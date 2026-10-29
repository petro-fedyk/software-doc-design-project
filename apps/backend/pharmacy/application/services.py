from pharmacy.application.subscribers import NotificationSubscriber, LoyaltySubscriber
from typing import Callable
from pharmacy.application.ports import UnitOfWork, PaymentGateway, ShipmentProvider
from dataclasses import asdict
from uuid import uuid5, NAMESPACE_URL
from pharmacy.domain.core import (
    DomainError,
    Line,
    OrderDraftBuilder,
    PricingService,
    PickupCreator,
    CourierCreator,
    PostalCreator,
    money,
    quantity,
    EventPublisher,
)
from functools import wraps
import time


def retry_mysql_deadlock(max_retries=3, delay=0.05, sleep=time.sleep):
    """Retry the complete application operation after a MySQL deadlock rollback."""
    def decorate(operation):
        @wraps(operation)
        def wrapped(*args, **kwargs):
            attempts = 0
            while True:
                try:
                    return operation(*args, **kwargs)
                except Exception as exc:
                    code = exc.args[0] if exc.args else None
                    if code != 1213 or attempts >= max_retries:
                        raise
                    attempts += 1
                    sleep(delay * attempts)
        return wrapped
    return decorate

CREATORS = {
    "PICKUP": PickupCreator(),
    "COURIER": CourierCreator(),
    "POSTAL": PostalCreator(),
}
METHODS = {"CARD", "BANK_TRANSFER", "CASH_ON_DELIVERY", "ONLINE_GATEWAY"}
PROVIDERS = {
    "CARD": "CARD_PROCESSOR",
    "BANK_TRANSFER": "BANK_TRANSFER",
    "CASH_ON_DELIVERY": "CASH_ON_DELIVERY",
    "ONLINE_GATEWAY": "PAYMENT_GATEWAY",
}


class OrderApplicationService:
    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], pricing=None, enabled_methods=None
    ):
        self.uow_factory = uow_factory
        self.pricing = pricing or PricingService()
        self.enabled_methods = METHODS if enabled_methods is None else enabled_methods

    def _draft(self, uow, actor, command, lock=False):
        actor.customer()
        method = command["fulfillment_method"]
        if method not in CREATORS:
            raise DomainError("INVALID_DELIVERY", status=400)
        builder = (
            OrderDraftBuilder()
            .with_customer(actor.id)
            .with_branch(command["pharmacy_id"])
            .with_delivery(method)
        )
        lines = []
        for requested in sorted(command["items"], key=lambda x: x["product_id"]):
            count = quantity(requested["quantity"])
            offer = uow.inventory.offer(
                command["pharmacy_id"], requested["product_id"], lock
            )
            if not uow.delivery.allowed(method, offer):
                raise DomainError("DELIVERY_NOT_ALLOWED")
            if lock and money(requested["expected_unit_price"]) != offer["price"]:
                raise DomainError("PRICE_CHANGED")
            if count > offer["available"]:
                raise DomainError("OUT_OF_STOCK")
            line = Line(
                requested["product_id"],
                offer["name"],
                count,
                offer["price"],
                offer["prescription"],
                offer["cold"],
            )
            lines.append(line)
            builder.add_line(line)
        handler = CREATORS[method].create_handler()
        handler.validate(lines)
        subtotal, discount = self.pricing.calculate(
            lines, uow.loyalty.policies(actor.id, command.get("promotion"))
        )
        return builder.with_total(subtotal, discount, handler.fee).build()

    def quote(self, actor, command):
        with self.uow_factory() as uow:
            draft = self._draft(uow, actor, command)
            return {**asdict(draft), "grand_total": draft.total}

    @retry_mysql_deadlock()
    def place(self, actor, command):
        if command["payment_method"] not in self.enabled_methods:
            raise DomainError("INVALID_PAYMENT_METHOD", status=400)
        recipient = command.get("recipient", {})
        if command["fulfillment_method"] != "PICKUP" and not all(
            recipient.get(x) for x in ("name", "phone", "destination")
        ):
            raise DomainError("RECIPIENT_REQUIRED", status=400)
        with self.uow_factory() as uow:
            draft = self._draft(uow, actor, command, lock=True)
            if money(command["expected_total"]) != draft.total:
                raise DomainError("PRICE_CHANGED")
            order = uow.orders.create(draft, command["payment_method"], recipient)
            uow.inventory.reserve(order.id)
            order.transition("CONFIRMED")
            uow.orders.save(order)
            uow.outbox.add(
                "order.confirmed", {"order_id": order.id, "status": "CONFIRMED"}
            )
            uow.audit(actor.id, "ORDER_PLACED", order.id, {})
            uow.commit()
            return asdict(order)

    @retry_mysql_deadlock()
    def transition(self, actor, order_id, target):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id, lock=True)
            actor.access(order)
            if target != "CANCELLED":
                actor.branch(order.pharmacy_id)
            if target == order.status:
                return asdict(order)
            if target in {"SHIPPED", "COMPLETED"}:
                if order.payment_method != "CASH_ON_DELIVERY" and not uow.payments.paid(
                    order.id
                ):
                    raise DomainError("PAYMENT_REQUIRED")
                if uow.orders.prescription_required(
                    order.id
                ) and not uow.orders.prescription_approved(order.id):
                    raise DomainError("PRESCRIPTION_VERIFICATION_REQUIRED")
            if target == "SHIPPED":
                raise DomainError("USE_SHIPMENT_ACTION", status=400)
            order.transition(target)
            if target == "CANCELLED":
                uow.inventory.release(order.id)
                uow.payments.cancel_pending(order.id)
                for payment in uow.payments.captured(order.id):
                    amount = uow.payments.refundable(payment["id"])
                    if amount > 0:
                        refund = uow.payments.refund(
                            order, amount, "Order cancellation"
                        )
                        uow.outbox.add(
                            "refund.requested",
                            {"refund_id": refund["id"], "order_id": order.id},
                        )
            if target == "COMPLETED":
                uow.inventory.release(order.id, consume=True)
                if order.payment_method == "CASH_ON_DELIVERY" and not uow.payments.paid(
                    order.id
                ):
                    payment = uow.payments.request(
                        order, f"cash-order-{order.id}", "CASH_ON_DELIVERY"
                    )
                    uow.payments.settle(
                        payment["id"],
                        {"status": "SUCCEEDED", "reference": f"CASH-{order.id}"},
                    )
                uow.delivery.update(
                    order.id, "PICKED_UP" if order.method == "PICKUP" else "DELIVERED"
                )
            uow.orders.save(order)
            payload = {"order_id": order.id, "status": target}
            if target == "COMPLETED":
                payload["loyalty_points"] = uow.loyalty.calculate_points(order)
            uow.outbox.add("order." + target.lower(), payload)
            uow.audit(actor.id, "ORDER_" + target, order.id, {})
            uow.commit()
            return asdict(order)

    @retry_mysql_deadlock()
    def verify(self, actor, order_id, approved):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id, lock=True)
            if (
                actor.role != "STAFF"
                or not actor.pharmacist
                or order.pharmacy_id not in actor.pharmacies
            ):
                raise DomainError("PHARMACIST_AUTHORITY_REQUIRED", status=403)
            if order.status in {"CANCELLED", "COMPLETED", "SHIPPED"}:
                raise DomainError("ORDER_NOT_VERIFIABLE")
            if not uow.orders.prescription_required(order.id):
                raise DomainError("PRESCRIPTION_NOT_REQUIRED")
            uow.orders.verify_prescription(order.id, actor.id, approved)
            uow.audit(
                actor.id, "PRESCRIPTION_CHECKED", order.id, {"approved": approved}
            )
            uow.commit()
            return {"status": "APPROVED" if approved else "REJECTED", "simulated": True}

    @retry_mysql_deadlock()
    def ship(self, actor, order_id):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id, lock=True)
            actor.branch(order.pharmacy_id)
            if order.status != "AWAITING_SHIPMENT":
                raise DomainError("NOT_AWAITING_SHIPMENT")
            if order.payment_method != "CASH_ON_DELIVERY" and not uow.payments.paid(
                order.id
            ):
                raise DomainError("PAYMENT_REQUIRED")
            event_id = str(uuid5(NAMESPACE_URL, f"shipment:{order.id}"))
            if not uow.outbox.find(event_id):
                uow.outbox.add("shipment.requested", {"order_id": order.id}, event_id)
            uow.commit()
            return {"status": "QUEUED", "order_id": order.id}


class PaymentApplicationService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.uow_factory = uow_factory

    @retry_mysql_deadlock()
    def request(self, actor, order_id, key):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id, lock=True)
            actor.access(order)
            if order.status in {"CANCELLED", "COMPLETED"}:
                raise DomainError("ORDER_NOT_PAYABLE")
            if order.payment_method == "CASH_ON_DELIVERY":
                raise DomainError("CASH_RECORDED_AT_HANDOVER")
            payment = uow.payments.request(order, key, PROVIDERS[order.payment_method])
            event_id = str(uuid5(NAMESPACE_URL, f"payment:{payment['id']}"))
            if not uow.outbox.find(event_id):
                uow.outbox.add(
                    "payment.requested",
                    {"payment_id": payment["id"], "order_id": order.id},
                    event_id,
                )
            uow.commit()
            return payment

    @retry_mysql_deadlock()
    def refund(self, actor, order_id, amount, reason, key):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id, lock=True)
            actor.branch(order.pharmacy_id)
            amount = money(amount)
            if amount <= 0:
                raise DomainError("INVALID_REFUND", status=400)
            event_id = str(uuid5(NAMESPACE_URL, f"refund:{order.id}:{key}"))
            existing = uow.outbox.find(event_id)
            if existing:
                if existing["amount"] != str(amount):
                    raise DomainError("IDEMPOTENCY_CONFLICT")
                return existing
            refund = uow.payments.refund(order, amount, reason)
            payload = {
                "refund_id": refund["id"],
                "order_id": order.id,
                "amount": str(amount),
            }
            uow.outbox.add("refund.requested", payload, event_id)
            uow.audit(actor.id, "REFUND_REQUESTED", order.id, {"amount": str(amount)})
            uow.commit()
            return payload


class InventoryApplicationService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.uow_factory = uow_factory

    @retry_mysql_deadlock()
    def change(self, actor, pharmacy_id, product_id, changes):
        actor.branch(pharmacy_id)
        if "quantity" in changes:
            quantity(changes["quantity"])
        if "adjustment" in changes and (
            type(changes["adjustment"]) is not int
            or changes["adjustment"] == 0
            or "quantity" in changes
        ):
            raise DomainError("INVALID_ADJUSTMENT", status=400)
        if "unit_price" in changes:
            changes = {**changes, "unit_price": money(changes["unit_price"])}
        with self.uow_factory() as uow:
            result = uow.inventory.change(actor.id, pharmacy_id, product_id, changes)
            uow.audit(
                actor.id,
                "INVENTORY_CHANGED",
                result["id"],
                {k: str(v) for k, v in changes.items()},
            )
            if changes.get("quantity"):
                uow.outbox.add(
                    "inventory.received",
                    {"product_id": product_id, "pharmacy_id": pharmacy_id},
                )
            uow.commit()
            return result


class CustomerApplicationService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.uow_factory = uow_factory

    @retry_mysql_deadlock()
    def cart(self, actor, product_id, count):
        actor.customer()
        if count != 0:
            quantity(count)
        with self.uow_factory() as uow:
            result = uow.carts.set_item(actor.id, product_id, count)
            uow.commit()
            return result

    @retry_mysql_deadlock()
    def personal(self, actor, kind, data):
        actor.customer()
        # Repository adapters may consume optional fields; keep retry input immutable.
        data = dict(data)
        with self.uow_factory() as uow:
            result = uow.engagement.save_personal(actor.id, kind, data)
            uow.commit()
            return result


class EventApplicationService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        payment_gateway: PaymentGateway,
        shipment_provider: ShipmentProvider,
    ):
        self.uow_factory, self.gateway, self.shipment = (
            uow_factory,
            payment_gateway,
            shipment_provider,
        )
        self.publisher = EventPublisher()
        self.notification_subscriber = NotificationSubscriber(uow_factory)
        self.loyalty_subscriber = LoyaltySubscriber(uow_factory)
        for event in (
            "order.confirmed",
            "order.processing",
            "order.ready_for_pickup",
            "order.awaiting_shipment",
            "order.shipped",
            "order.completed",
            "order.cancelled",
        ):
            self.publisher.subscribe(event, self.notification_subscriber.handle)
        self.publisher.subscribe("order.completed", self.loyalty_subscriber.handle)
        self.publisher.subscribe("payment.requested", self.payment)
        self.publisher.subscribe("refund.requested", self.refund)
        self.publisher.subscribe("shipment.requested", self.prepare_shipment)
        self.publisher.subscribe("inventory.received", self.availability)
        self.publisher.subscribe("promotion.published", self.promotion)

    def handle(self, event_type, payload, event_id=None):
        if event_type not in self.publisher.subscribers:
            raise DomainError("UNKNOWN_EVENT_TYPE")
        event_payload = {**payload, "_outbox_event_id": event_id} if event_id else payload
        self.publisher.publish(event_type, event_payload)

    def order_changed(self, payload):
        self.notification_subscriber.handle(payload)
        self.loyalty_subscriber.handle(payload)

    def payment(self, payload):
        with self.uow_factory() as uow:
            order = uow.orders.get(payload["order_id"], lock=True)
            payment = uow.payments.get(payload["payment_id"])
            if payment["status"] != "PENDING":
                return
            if order.status == "CANCELLED":
                uow.payments.cancel_pending(order.id)
            else:
                result = self.gateway.authorize(
                    str(order.id), payment["amount"], payment["idempotency_key"]
                )
                uow.payments.settle(payment["id"], result)
            uow.commit()

    def refund(self, payload):
        with self.uow_factory() as uow:
            order = uow.orders.get(payload["order_id"], lock=True)
            refund = uow.payments.get_refund(payload["refund_id"])
            if refund["status"] != "PENDING":
                return
            result = self.gateway.refund(
                str(order.id), refund["amount"], f"refund-{refund['id']}"
            )
            uow.payments.settle_refund(refund["id"], result)
            if result["status"] == "SUCCEEDED":
                uow.loyalty.reverse(order)
            uow.commit()

    def prepare_shipment(self, payload):
        with self.uow_factory() as uow:
            order = uow.orders.get(payload["order_id"], lock=True)
            if order.status != "AWAITING_SHIPMENT":
                return
            if order.payment_method != "CASH_ON_DELIVERY" and not uow.payments.paid(
                order.id
            ):
                raise DomainError("PAYMENT_REQUIRED")
            for product_id in uow.orders.product_ids(order.id):
                offer = uow.inventory.offer(order.pharmacy_id, product_id, lock=True)
                if not uow.delivery.allowed(order.method, offer):
                    raise DomainError("DELIVERY_NOT_ALLOWED")
            tracking = (
                CREATORS[order.method].create_handler().fulfill(self.shipment, order.id)
            )
            order.transition("SHIPPED")
            uow.inventory.release(order.id, consume=True)
            uow.delivery.update(order.id, "SHIPPED", tracking)
            uow.orders.save(order)
            uow.outbox.add("order.shipped", {"order_id": order.id, "status": "SHIPPED"})
            uow.commit()

    def availability(self, payload):
        with self.uow_factory() as uow:
            uow.engagement.notify_availability(
                payload["product_id"], payload["pharmacy_id"], payload.get("_outbox_event_id")
            )
            uow.commit()

    def promotion(self, payload):
        with self.uow_factory() as uow:
            uow.engagement.notify_promotion(
                payload["promotion_id"], payload.get("_outbox_event_id")
            )
            uow.commit()
