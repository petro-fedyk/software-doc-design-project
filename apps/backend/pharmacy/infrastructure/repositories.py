from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from pharmacy import models as m
from pharmacy.domain.core import (
    DomainError,
    Order,
    StandardDiscount,
    SocialDiscount,
    PremiumDiscount,
    PromotionDiscount,
    StockBalance,
    earned_points,
    refund_points,
    delivery_allowed,
)


def dto(obj):
    return {f.attname: getattr(obj, f.attname) for f in obj._meta.concrete_fields}


def get_row(query, **kwargs):
    obj = query.filter(**kwargs).first()
    if obj is None:
        raise DomainError("NOT_FOUND", status=404)
    return obj


class DjangoOrderRepository:
    @staticmethod
    def domain(row):
        return Order(
            row.id,
            row.customer_id,
            row.pharmacy_id,
            row.status,
            row.fulfillment_method,
            row.grand_total,
            row.payment_method,
        )

    def get(self, order_id, lock=False):
        qs = m.Orders.objects.select_for_update() if lock else m.Orders.objects
        return self.domain(get_row(qs, id=order_id))

    def create(self, draft, payment_method, recipient):
        now = timezone.now()
        row = m.Orders.objects.create(
            order_number=str(uuid4()),
            customer_id=draft.customer_id,
            pharmacy_id=draft.pharmacy_id,
            status="PENDING_CONFIRMATION",
            fulfillment_method=draft.method,
            payment_method=payment_method,
            subtotal=draft.subtotal,
            discount_total=draft.discount,
            shipping_total=draft.shipping,
            grand_total=draft.total,
            currency="UAH",
            created_at=now,
            updated_at=now,
        )
        for line in draft.lines:
            m.OrderItems.objects.create(
                order=row,
                product_id=line.product_id,
                product_name_snapshot=line.name,
                unit_price_snapshot=line.price,
                quantity=line.quantity,
                line_total=line.total,
            )
        m.Deliveries.objects.create(
            order=row,
            method=draft.method,
            recipient_name=recipient.get("name"),
            recipient_phone=recipient.get("phone"),
            destination=recipient.get("destination"),
            provider="SIMULATED",
            status="CREATED",
            created_at=now,
        )
        return self.domain(row)

    def save(self, order):
        m.Orders.objects.filter(id=order.id).update(
            status=order.status, updated_at=timezone.now()
        )

    def product_ids(self, order_id):
        return list(
            m.OrderItems.objects.filter(order_id=order_id)
            .order_by("product_id")
            .values_list("product_id", flat=True)
        )

    def prescription_required(self, order_id):
        return m.OrderItems.objects.filter(
            order_id=order_id, product__prescription_required=True
        ).exists()

    def prescription_approved(self, order_id):
        row = (
            m.PrescriptionVerifications.objects.filter(order_id=order_id)
            .order_by("-checked_at", "-id")
            .first()
        )
        return bool(row and row.status == "APPROVED")

    def verify_prescription(self, order_id, actor_id, approved):
        m.PrescriptionVerifications.objects.create(
            order_id=order_id,
            checked_by_id=actor_id,
            status="APPROVED" if approved else "REJECTED",
            is_demo=True,
            checked_at=timezone.now(),
            note="Simulated in-person verification",
        )


class DjangoInventoryRepository:
    def offer(self, pharmacy_id, product_id, lock=False):
        qs = m.PharmacyInventory.objects.select_related("product", "pharmacy")
        if lock:
            qs = qs.select_for_update()
        row = get_row(qs, pharmacy_id=pharmacy_id, product_id=product_id)
        if not row.pharmacy.is_active or not row.product.is_active or not row.is_listed:
            raise DomainError("OFFER_UNAVAILABLE")
        p = row.product
        return {
            "id": row.id,
            "name": p.name,
            "price": row.unit_price,
            "available": row.on_hand - row.reserved,
            "prescription": p.prescription_required,
            "cold": p.storage_max_c is not None and p.storage_max_c <= 8,
            "min_c": p.storage_min_c,
            "max_c": p.storage_max_c,
        }

    def reserve(self, order_id):
        order = m.Orders.objects.get(id=order_id)
        for item in m.OrderItems.objects.filter(order_id=order_id).order_by(
            "product_id"
        ):
            row = get_row(
                m.PharmacyInventory.objects.select_for_update(),
                pharmacy_id=order.pharmacy_id,
                product_id=item.product_id,
            )
            stock = StockBalance(row.on_hand, row.reserved, row.version)
            stock.reserve(item.quantity)
            m.PharmacyInventory.objects.filter(id=row.id).update(
                reserved=stock.reserved,
                version=stock.version,
                updated_at=timezone.now(),
            )
            m.Reservations.objects.create(
                order_item=item,
                inventory=row,
                quantity=item.quantity,
                status="ACTIVE",
                expires_at=timezone.now() + timedelta(hours=24),
                created_at=timezone.now(),
            )

    def release(self, order_id, consume=False):
        rows = (
            m.Reservations.objects.select_for_update()
            .filter(order_item__order_id=order_id)
            .order_by("inventory_id")
        )
        for reservation in rows:
            if reservation.status != "ACTIVE":
                continue
            if consume and reservation.expires_at <= timezone.now():
                raise DomainError("RESERVATION_EXPIRED")
            row = m.PharmacyInventory.objects.select_for_update().get(
                id=reservation.inventory_id
            )
            stock = StockBalance(row.on_hand, row.reserved, row.version)
            stock.release(reservation.quantity, consume)
            row.reserved = stock.reserved
            if consume:
                row.on_hand = stock.on_hand
                m.InventoryMovements.objects.create(
                    inventory=row,
                    delta_on_hand=-reservation.quantity,
                    reason="FULFILLMENT",
                    reference_type="ORDER",
                    reference_id=order_id,
                    created_at=timezone.now(),
                )
            row.version += 1
            row.updated_at = timezone.now()
            row.save()
            reservation.status = "FULFILLED" if consume else "CANCELLED"
            reservation.save(update_fields=["status"])

    def change(self, actor_id, pharmacy_id, product_id, changes):
        get_row(
            m.Pharmacies.objects.select_for_update(), id=pharmacy_id, is_active=True
        )
        get_row(m.Products.objects, id=product_id, is_active=True)
        row = (
            m.PharmacyInventory.objects.select_for_update()
            .filter(pharmacy_id=pharmacy_id, product_id=product_id)
            .first()
        )
        if row is None:
            if "unit_price" not in changes:
                raise DomainError("PRICE_REQUIRED", status=400)
            row = m.PharmacyInventory.objects.create(
                pharmacy_id=pharmacy_id,
                product_id=product_id,
                unit_price=changes["unit_price"],
                on_hand=0,
                reserved=0,
                is_listed=True,
                version=0,
                updated_at=timezone.now(),
            )
        if "quantity" in changes:
            row.on_hand += changes["quantity"]
            m.InventoryMovements.objects.create(
                inventory=row,
                delta_on_hand=changes["quantity"],
                reason="RECEIPT",
                performed_by_id=actor_id,
                created_at=timezone.now(),
            )
        if "adjustment" in changes:
            stock = StockBalance(
                row.on_hand + changes["adjustment"], row.reserved, row.version
            )
            row.on_hand = stock.on_hand
            m.InventoryMovements.objects.create(
                inventory=row,
                delta_on_hand=changes["adjustment"],
                reason="ADJUSTMENT",
                performed_by_id=actor_id,
                created_at=timezone.now(),
            )
        for key in ("unit_price", "is_listed"):
            if key in changes:
                setattr(row, key, changes[key])
        row.version += 1
        row.updated_at = timezone.now()
        row.save()
        return dto(row)


class DjangoPaymentRepository:
    def request(self, order, key, provider):
        existing = m.Payments.objects.filter(idempotency_key=key).first()
        if existing:
            if (
                existing.order_id != order.id
                or existing.provider != provider
                or existing.amount != order.total
            ):
                raise DomainError("IDEMPOTENCY_CONFLICT")
            return dto(existing)
        if m.Payments.objects.filter(
            order_id=order.id,
            status__in=["SUCCEEDED", "PENDING", "UNKNOWN", "REFUNDED"],
        ).exists():
            raise DomainError("PAYMENT_ALREADY_EXISTS")
        return dto(
            m.Payments.objects.create(
                order_id=order.id,
                provider=provider,
                status="PENDING",
                amount=order.total,
                currency="UAH",
                idempotency_key=key,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
        )

    def get(self, payment_id):
        return dto(get_row(m.Payments.objects, id=payment_id))

    def settle(self, payment_id, result):
        m.Payments.objects.filter(id=payment_id, status="PENDING").update(
            status=result["status"],
            provider_reference=result.get("reference"),
            failure_code=result.get("failure_code"),
            updated_at=timezone.now(),
        )

    def paid(self, order_id):
        return m.Payments.objects.filter(order_id=order_id, status="SUCCEEDED").exists()

    def captured(self, order_id):
        return list(
            m.Payments.objects.filter(order_id=order_id, status="SUCCEEDED").values()
        )

    def cancel_pending(self, order_id):
        m.Payments.objects.filter(order_id=order_id, status="PENDING").update(
            status="FAILED", failure_code="ORDER_CANCELLED", updated_at=timezone.now()
        )

    def refundable(self, payment_id):
        payment = m.Payments.objects.get(id=payment_id)
        total = m.Refunds.objects.filter(
            payment_id=payment_id, status__in=["PENDING", "SUCCEEDED"]
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return payment.amount - total

    def refund(self, order, amount, reason):
        payment = (
            m.Payments.objects.select_for_update()
            .filter(order_id=order.id, status="SUCCEEDED")
            .first()
        )
        if not payment or amount > self.refundable(payment.id):
            raise DomainError("REFUND_EXCEEDS_BALANCE")
        return dto(
            m.Refunds.objects.create(
                payment=payment,
                amount=amount,
                status="PENDING",
                reason=reason,
                created_at=timezone.now(),
            )
        )

    def get_refund(self, refund_id):
        return dto(get_row(m.Refunds.objects, id=refund_id))

    def settle_refund(self, refund_id, result):
        row = get_row(m.Refunds.objects.select_for_update(), id=refund_id)
        if row.status != "PENDING":
            return
        row.status = result["status"]
        row.save(update_fields=["status"])
        total = m.Refunds.objects.filter(
            payment_id=row.payment_id, status="SUCCEEDED"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if total == row.payment.amount:
            m.Payments.objects.filter(id=row.payment_id).update(
                status="REFUNDED", updated_at=timezone.now()
            )


class DjangoLoyaltyRepository:
    def policies(self, customer_id, promotion):
        policies = []
        account = (
            m.LoyaltyAccounts.objects.select_related("tier")
            .filter(customer_id=customer_id)
            .first()
        )
        if account:
            strategy = {
                "STANDARD": StandardDiscount,
                "SOCIAL": SocialDiscount,
                "PREMIUM": PremiumDiscount,
            }[account.tier.code]
            policies.append(strategy(account.tier.discount_rate))
        if promotion:
            row = m.Promotions.objects.filter(
                code=promotion,
                is_active=True,
                starts_at__lte=timezone.now(),
                ends_at__gt=timezone.now(),
            ).first()
            if not row:
                raise DomainError("INVALID_PROMOTION")
            products = frozenset(
                m.PromotionProducts.objects.filter(promotion=row).values_list(
                    "product_id", flat=True
                )
            )
            policies.append(PromotionDiscount(row.discount_rate, products))
        return policies

    def calculate_points(self, order):
        account = (
            m.LoyaltyAccounts.objects.select_related("tier")
            .filter(customer_id=order.customer_id)
            .first()
        )
        if not account:
            return 0
        items = m.OrderItems.objects.filter(
            order_id=order.id, product__prescription_required=False
        )
        eligible = items.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
        stored = m.Orders.objects.get(id=order.id)
        return earned_points(eligible, stored.discount_total, account.tier.bonus_rate)

    def accrue(self, order, points=None):
        account = (
            m.LoyaltyAccounts.objects.select_for_update()
            .select_related("tier")
            .filter(customer_id=order.customer_id)
            .first()
        )
        if not account:
            return
        event_key = f"completion:{order.id}"
        if m.LoyaltyTransactions.objects.filter(event_key=event_key).exists():
            return
        points = self.calculate_points(order) if points is None else points
        if points:
            m.LoyaltyTransactions.objects.create(
                account=account,
                order_id=order.id,
                points_delta=points,
                type="EARN",
                event_key=event_key,
                created_at=timezone.now(),
            )
            account.balance += points
            account.save(update_fields=["balance"])
        self.reverse(order)

    def reverse(self, order):
        earned = m.LoyaltyTransactions.objects.filter(
            event_key=f"completion:{order.id}"
        ).first()
        if not earned:
            return
        account = m.LoyaltyAccounts.objects.select_for_update().get(
            id=earned.account_id
        )
        refunded = m.Refunds.objects.filter(
            payment__order_id=order.id, status="SUCCEEDED"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        previous = -(
            m.LoyaltyTransactions.objects.filter(
                order_id=order.id, type="ADJUST"
            ).aggregate(total=Sum("points_delta"))["total"]
            or 0
        )
        delta, desired = refund_points(
            earned.points_delta, refunded, order.total, previous, account.balance
        )
        if delta > 0:
            m.LoyaltyTransactions.objects.create(
                account=account,
                order_id=order.id,
                points_delta=-delta,
                type="ADJUST",
                event_key=f"refund-adjust:{order.id}:{desired}",
                created_at=timezone.now(),
            )
            account.balance -= delta
            account.save(update_fields=["balance"])


class DjangoDeliveryRepository:
    def allowed(self, method, offer):
        rules = list(
            m.DeliveryRules.objects.filter(
                method=method, enabled=True, requires_cold_chain=offer["cold"]
            ).values()
        )
        return delivery_allowed(method, offer, rules)

    def update(self, order_id, status, tracking=None):
        values = {"status": status}
        if tracking:
            values["tracking_reference"] = tracking
        m.Deliveries.objects.filter(order_id=order_id).update(**values)


class DjangoOutboxRepository:
    def add(self, event_type, payload, event_id=None):
        identifier = event_id or str(uuid4())
        m.OutboxEvents.objects.create(
            event_id=identifier,
            event_type=event_type,
            payload=payload,
            status="PENDING",
            attempts=0,
            available_at=timezone.now(),
            created_at=timezone.now(),
        )
        return identifier

    def find(self, event_id):
        row = m.OutboxEvents.objects.filter(event_id=event_id).first()
        return row.payload if row else None


class DjangoCartRepository:
    def set_item(self, customer_id, product_id, quantity):
        m.Users.objects.select_for_update().get(id=customer_id)
        get_row(m.Products.objects, id=product_id, is_active=True)
        cart, _ = m.Carts.objects.get_or_create(
            customer_id=customer_id, defaults={"updated_at": timezone.now()}
        )
        if quantity == 0:
            m.CartItems.objects.filter(cart=cart, product_id=product_id).delete()
        else:
            m.CartItems.objects.update_or_create(
                cart=cart, product_id=product_id, defaults={"quantity": quantity}
            )
        cart.updated_at = timezone.now()
        cart.save(update_fields=["updated_at"])
        return {
            "id": cart.id,
            "items": list(
                m.CartItems.objects.filter(cart=cart).values("product_id", "quantity")
            ),
        }


class DjangoEngagementRepository:
    def notify_order(self, order):
        m.Notifications.objects.create(
            user_id=order.customer_id,
            type="ORDER",
            title="Order update",
            body=f"Order {order.id}: {order.status}",
            created_at=timezone.now(),
        )

    def notify_availability(self, product_id, pharmacy_id):
        for watch in m.AvailabilitySubscriptions.objects.select_for_update().filter(
            product_id=product_id, pharmacy_id=pharmacy_id, is_active=True
        ):
            m.Notifications.objects.create(
                user_id=watch.customer_id,
                type="AVAILABILITY",
                title="Product available",
                body=f"Product {product_id} is available at pharmacy {pharmacy_id}.",
                created_at=timezone.now(),
            )
            watch.is_active = False
            watch.save(update_fields=["is_active"])

    def notify_promotion(self, promotion_id):
        promotion = m.Promotions.objects.filter(
            id=promotion_id,
            is_active=True,
            starts_at__lte=timezone.now(),
            ends_at__gt=timezone.now(),
        ).first()
        if not promotion:
            return
        recipients = m.NotificationPreferences.objects.filter(
            promotions_enabled=True, user__is_active=True
        ).values_list("user_id", flat=True)
        for identifier in recipients:
            m.Notifications.objects.create(
                user_id=identifier,
                type="PROMOTION",
                title="Pharmacy promotion",
                body=promotion.code,
                created_at=timezone.now(),
            )

    def save_personal(self, customer_id, kind, data):
        m.Users.objects.select_for_update().get(id=customer_id)
        if kind == "preferences":
            row, _ = m.NotificationPreferences.objects.update_or_create(
                user_id=customer_id, defaults=data
            )
        elif kind == "watch":
            get_row(m.Products.objects, id=data["product_id"], is_active=True)
            get_row(m.Pharmacies.objects, id=data["pharmacy_id"], is_active=True)
            row, _ = m.AvailabilitySubscriptions.objects.update_or_create(
                customer_id=customer_id,
                product_id=data["product_id"],
                pharmacy_id=data["pharmacy_id"],
                defaults={"is_active": data["is_active"]},
            )
        elif kind == "reminder":
            get_row(m.Products.objects, id=data["product_id"], is_active=True)
            if (
                data.get("is_active", True)
                and not m.NotificationPreferences.objects.filter(
                    user_id=customer_id, reminders_enabled=True
                ).exists()
            ):
                raise DomainError("REMINDER_OPT_IN_REQUIRED")
            identifier = data.pop("id", None)
            if identifier:
                row = get_row(
                    m.Reminders.objects, id=identifier, customer_id=customer_id
                )
                for k, v in data.items():
                    setattr(row, k, v)
                row.save()
            else:
                row = m.Reminders.objects.create(customer_id=customer_id, **data)
        else:
            raise DomainError("INVALID_PERSONAL_RESOURCE", status=400)
        return dto(row)


class DjangoUnitOfWork:
    def __enter__(self):
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.committed = False
        self.orders = DjangoOrderRepository()
        self.inventory = DjangoInventoryRepository()
        self.payments = DjangoPaymentRepository()
        self.loyalty = DjangoLoyaltyRepository()
        self.delivery = DjangoDeliveryRepository()
        self.outbox = DjangoOutboxRepository()
        self.engagement = DjangoEngagementRepository()
        self.carts = DjangoCartRepository()
        return self

    def commit(self):
        self.committed = True

    def rollback(self):
        self.committed = False
        transaction.set_rollback(True)

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None and not self.committed:
            transaction.set_rollback(True)
        return self.atomic.__exit__(exc_type, exc, tb)

    def audit(self, actor_id, action, target_id, details):
        m.AuditEntries.objects.create(
            actor_id=actor_id,
            action=action,
            target_type="order"
            if action.startswith(("ORDER", "REFUND", "PRESCRIPTION"))
            else "inventory",
            target_id=target_id,
            details=details,
            occurred_at=timezone.now(),
        )
