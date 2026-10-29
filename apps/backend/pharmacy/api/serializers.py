from collections.abc import Mapping
from decimal import Decimal
from rest_framework import serializers as s
from django.utils import timezone
from pharmacy import models as m


class StrictSerializer(s.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise s.ValidationError({"non_field_errors": ["Expected a JSON object."]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise s.ValidationError(
                {"fields": "Unsupported fields: " + ", ".join(sorted(unknown))}
            )
        return super().to_internal_value(data)


class LoginSerializer(StrictSerializer):
    username = s.CharField(max_length=150)
    password = s.CharField(write_only=True, max_length=128, trim_whitespace=False)


class RegisterSerializer(LoginSerializer):
    email = s.EmailField(max_length=254)
    full_name = s.CharField(max_length=200)

    def validate_password(self, value):
        if len(value) < 12:
            raise s.ValidationError("Use at least 12 characters.")
        return value


class TokenSerializer(s.Serializer):
    access = s.CharField()
    expires_in = s.IntegerField()


class LineSerializer(StrictSerializer):
    product_id = s.IntegerField(min_value=1)
    quantity = s.IntegerField(min_value=1, max_value=10000)
    expected_unit_price = s.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )


class RecipientSerializer(StrictSerializer):
    name = s.CharField(max_length=200)
    phone = s.CharField(max_length=32)
    destination = s.CharField(max_length=300)


class QuoteSerializer(StrictSerializer):
    pharmacy_id = s.IntegerField(min_value=1)
    fulfillment_method = s.ChoiceField(choices=["PICKUP", "COURIER", "POSTAL"])
    items = LineSerializer(many=True, allow_empty=False, max_length=100)
    promotion = s.CharField(max_length=50, required=False)


class PlaceSerializer(QuoteSerializer):
    payment_method = s.ChoiceField(
        choices=["CARD", "BANK_TRANSFER", "CASH_ON_DELIVERY", "ONLINE_GATEWAY"]
    )
    expected_total = s.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    recipient = RecipientSerializer(required=False)

    def validate_items(self, value):
        if any("expected_unit_price" not in x for x in value):
            raise s.ValidationError("Every line requires expected_unit_price.")
        return value


class TransitionSerializer(StrictSerializer):
    status = s.ChoiceField(
        choices=[
            "PROCESSING",
            "READY_FOR_PICKUP",
            "AWAITING_SHIPMENT",
            "COMPLETED",
            "CANCELLED",
        ]
    )


class PaymentSerializer(StrictSerializer):
    idempotency_key = s.CharField(max_length=80, min_length=8)


class RefundSerializer(PaymentSerializer):
    amount = s.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reason = s.CharField(max_length=200)


class VerificationSerializer(StrictSerializer):
    approved = s.BooleanField()


class InventoryChangeSerializer(StrictSerializer):
    adjustment = s.IntegerField(min_value=-1000000, max_value=1000000, required=False)
    quantity = s.IntegerField(min_value=1, max_value=1000000, required=False)
    unit_price = s.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    is_listed = s.BooleanField(required=False)

    def validate(self, data):
        if not data:
            raise s.ValidationError("At least one change is required.")
        if "adjustment" in data and (data["adjustment"] == 0 or "quantity" in data):
            raise s.ValidationError(
                "Use a nonzero adjustment or a receipt quantity, not both."
            )
        return data


class CartChangeSerializer(StrictSerializer):
    product_id = s.IntegerField(min_value=1)
    quantity = s.IntegerField(min_value=0, max_value=10000)


class PreferencesSerializer(StrictSerializer):
    promotions_enabled = s.BooleanField()
    reminders_enabled = s.BooleanField()


class WatchSerializer(StrictSerializer):
    product_id = s.IntegerField(min_value=1)
    pharmacy_id = s.IntegerField(min_value=1)
    is_active = s.BooleanField(default=True)


class ReminderSerializer(StrictSerializer):
    id = s.IntegerField(min_value=1, required=False)
    product_id = s.IntegerField(min_value=1)
    interval_days = s.IntegerField(min_value=1, max_value=3650)
    next_run_at = s.DateTimeField()
    is_active = s.BooleanField(default=True)

    def validate_next_run_at(self, value):
        if value <= timezone.now():
            raise s.ValidationError("The next run must be in the future.")
        return value


class ObjectSerializer(s.Serializer):
    """Flexible row shape for permission-dependent inventory projections."""

    id = s.IntegerField(required=False)
    product_id = s.IntegerField(required=False)
    product__name = s.CharField(required=False)
    unit_price = s.DecimalField(max_digits=12, decimal_places=2, required=False)
    on_hand = s.IntegerField(required=False)
    reserved = s.IntegerField(required=False)
    is_listed = s.BooleanField(required=False)
    available = s.IntegerField(required=False)
class ProductAvailabilitySerializer(s.Serializer):
    pharmacy_id = s.IntegerField()
    pharmacy__name = s.CharField()
    unit_price = s.DecimalField(max_digits=12, decimal_places=2)
    available = s.IntegerField()


class PreferenceRowSerializer(s.Serializer):
    id = s.IntegerField()
    user_id = s.IntegerField()
    promotions_enabled = s.BooleanField()
    reminders_enabled = s.BooleanField()


class WatchRowSerializer(s.Serializer):
    id = s.IntegerField()
    customer_id = s.IntegerField()
    product_id = s.IntegerField()
    pharmacy_id = s.IntegerField()
    is_active = s.BooleanField()


class ReminderRowSerializer(s.Serializer):
    id = s.IntegerField()
    customer_id = s.IntegerField()
    product_id = s.IntegerField()
    interval_days = s.IntegerField()
    next_run_at = s.DateTimeField()
    is_active = s.BooleanField()


class NotificationRowSerializer(s.Serializer):
    id = s.IntegerField()
    user_id = s.IntegerField()
    type = s.CharField()
    title = s.CharField()
    body = s.CharField()
    read_at = s.DateTimeField(allow_null=True)
    created_at = s.DateTimeField()


class SavedPrescriptionRowSerializer(s.Serializer):
    id = s.IntegerField()
    customer_id = s.IntegerField()
    display_label = s.CharField()
    masked_reference = s.CharField(allow_null=True)
    is_demo = s.BooleanField()
    created_at = s.DateTimeField()


class AuditRowSerializer(s.Serializer):
    id = s.IntegerField()
    actor_id = s.IntegerField(allow_null=True)
    action = s.CharField()
    target_type = s.CharField()
    target_id = s.IntegerField(allow_null=True)
    occurred_at = s.DateTimeField()
    details = s.JSONField(allow_null=True)


class ErrorSerializer(s.Serializer):
    code = s.CharField(required=False)
    detail = s.CharField(required=False)


class ProductSerializer(s.ModelSerializer):
    class Meta:
        model = m.Products
        fields = [
            "id",
            "sku",
            "name",
            "description",
            "category",
            "manufacturer",
            "prescription_required",
            "storage_min_c",
            "storage_max_c",
            "is_active",
        ]

    def validate(self, data):
        low = data.get("storage_min_c", getattr(self.instance, "storage_min_c", None))
        high = data.get("storage_max_c", getattr(self.instance, "storage_max_c", None))
        if low is not None and high is not None and low > high:
            raise s.ValidationError("Invalid storage range.")
        return data


class ProductPageSerializer(s.Serializer):
    count = s.IntegerField()
    next = s.URLField(allow_null=True)
    previous = s.URLField(allow_null=True)
    results = ProductSerializer(many=True)


class PharmacySerializer(s.ModelSerializer):
    class Meta:
        model = m.Pharmacies
        fields = ["id", "code", "name", "address", "city", "phone", "is_active"]


class OrderSerializer(s.ModelSerializer):
    items = s.SerializerMethodField()

    class Meta:
        model = m.Orders
        fields = [
            "id",
            "order_number",
            "customer_id",
            "pharmacy_id",
            "status",
            "fulfillment_method",
            "payment_method",
            "subtotal",
            "discount_total",
            "shipping_total",
            "grand_total",
            "currency",
            "created_at",
            "items",
        ]

    def get_items(self, obj) -> list[dict]:
        return list(
            m.OrderItems.objects.filter(order=obj).values(
                "product_id",
                "product_name_snapshot",
                "unit_price_snapshot",
                "quantity",
                "line_total",
            )
        )


class AssignmentSerializer(s.ModelSerializer):
    class Meta:
        model = m.EmployeeAssignments
        fields = ["id", "user", "pharmacy", "is_active"]

    def validate_user(self, user):
        if not user.is_active or user.role != "STAFF":
            raise s.ValidationError("An active staff user is required.")
        return user


class PromotionSerializer(s.ModelSerializer):
    class Meta:
        model = m.Promotions
        fields = [
            "id",
            "code",
            "description",
            "discount_rate",
            "starts_at",
            "ends_at",
            "is_active",
        ]

    def validate(self, data):
        start = data.get("starts_at", getattr(self.instance, "starts_at", None))
        end = data.get("ends_at", getattr(self.instance, "ends_at", None))
        rate = data.get("discount_rate", getattr(self.instance, "discount_rate", 0))
        if start and end and end <= start:
            raise s.ValidationError("Invalid promotion period.")
        if not 0 <= rate <= 1:
            raise s.ValidationError("Rate must be between zero and one.")
        return data


class TierSerializer(s.ModelSerializer):
    class Meta:
        model = m.LoyaltyTiers
        fields = ["id", "code", "bonus_rate", "discount_rate"]

    def validate(self, data):
        if data.get("code", getattr(self.instance, "code", None)) not in [
            "STANDARD",
            "SOCIAL",
            "PREMIUM",
        ]:
            raise s.ValidationError("Invalid tier code.")
        if any(
            not 0 <= data[x] <= 1 for x in ("bonus_rate", "discount_rate") if x in data
        ):
            raise s.ValidationError("Rates must be between zero and one.")
        return data


class PromotionProductSerializer(s.ModelSerializer):
    class Meta:
        model = m.PromotionProducts
        fields = ["id", "promotion", "product"]


class CategorySerializer(s.ModelSerializer):
    class Meta:
        model = m.Categories
        fields = ["id", "name"]


class ManufacturerSerializer(s.ModelSerializer):
    class Meta:
        model = m.Manufacturers
        fields = ["id", "name"]


class ProfileSerializer(StrictSerializer):
    full_name = s.CharField(max_length=200, required=False)
    phone = s.CharField(max_length=32, required=False, allow_null=True)
    preferred_pharmacy_id = s.IntegerField(min_value=1, required=False, allow_null=True)


class SavedPrescriptionSerializer(StrictSerializer):
    display_label = s.CharField(max_length=100)


class UserAdminSerializer(s.ModelSerializer):
    password = s.CharField(
        write_only=True,
        min_length=12,
        max_length=128,
        required=False,
        trim_whitespace=False,
    )
    role = s.ChoiceField(choices=["CUSTOMER", "STAFF", "ADMIN"])

    class Meta:
        model = m.Users
        fields = ["id", "username", "email", "role", "is_active", "password"]

    def create(self, data):
        from django.contrib.auth.hashers import make_password

        if "password" not in data:
            raise s.ValidationError({"password": "Required for a new account."})
        data["password"] = make_password(data["password"])
        data["created_at"] = timezone.now()
        data["is_staff"] = data["role"] != "CUSTOMER"
        return super().create(data)

    def update(self, instance, data):
        from django.contrib.auth.hashers import make_password

        if "password" in data:
            data["password"] = make_password(data["password"])
        if "role" in data:
            data["is_staff"] = data["role"] != "CUSTOMER"
        return super().update(instance, data)


class DeliveryRuleSerializer(s.ModelSerializer):
    method = s.ChoiceField(choices=["PICKUP", "COURIER", "POSTAL"])

    class Meta:
        model = m.DeliveryRules
        fields = [
            "id",
            "method",
            "requires_cold_chain",
            "cold_chain_supported",
            "enabled",
            "max_storage_min_c",
            "min_storage_max_c",
        ]

    def validate(self, data):
        low = data.get(
            "max_storage_min_c", getattr(self.instance, "max_storage_min_c", None)
        )
        high = data.get(
            "min_storage_max_c", getattr(self.instance, "min_storage_max_c", None)
        )
        if low is not None and high is not None and low > high:
            raise s.ValidationError("Invalid temperature range.")
        return data
