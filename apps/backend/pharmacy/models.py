"""Reviewed mappings of the SQL-owned schema. Never migrate these models."""

from django.db import models


class AuditEntries(models.Model):
    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey("Users", models.DO_NOTHING, blank=True, null=True)
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=50)
    target_id = models.PositiveBigIntegerField(blank=True, null=True)
    occurred_at = models.DateTimeField()
    details = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "audit_entries"


class AvailabilitySubscriptions(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey("Users", models.DO_NOTHING)
    product = models.ForeignKey("Products", models.DO_NOTHING)
    pharmacy = models.ForeignKey("Pharmacies", models.DO_NOTHING)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "availability_subscriptions"
        unique_together = (("customer", "product", "pharmacy"),)


class CartItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    cart = models.ForeignKey("Carts", models.DO_NOTHING)
    product = models.ForeignKey("Products", models.DO_NOTHING)
    quantity = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "cart_items"
        unique_together = (("cart", "product"),)


class Carts(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.OneToOneField("Users", models.DO_NOTHING)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "carts"


class Categories(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = "categories"


class CustomerProfiles(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField("Users", models.DO_NOTHING)
    phone = models.CharField(max_length=32, blank=True, null=True)
    full_name = models.CharField(max_length=200)
    preferred_pharmacy = models.ForeignKey(
        "Pharmacies", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "customer_profiles"


class Deliveries(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField("Orders", models.DO_NOTHING)
    method = models.CharField(max_length=16)
    recipient_name = models.CharField(max_length=200, blank=True, null=True)
    recipient_phone = models.CharField(max_length=32, blank=True, null=True)
    destination = models.CharField(max_length=300, blank=True, null=True)
    provider = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=24)
    tracking_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "deliveries"


class DeliveryRules(models.Model):
    id = models.BigAutoField(primary_key=True)
    method = models.CharField(max_length=16)
    requires_cold_chain = models.BooleanField()
    cold_chain_supported = models.BooleanField()
    enabled = models.BooleanField()
    max_storage_min_c = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    min_storage_max_c = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "delivery_rules"


class EmployeeAssignments(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey("Users", models.DO_NOTHING)
    pharmacy = models.ForeignKey("Pharmacies", models.DO_NOTHING)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "employee_assignments"
        unique_together = (("user", "pharmacy"),)


class InventoryMovements(models.Model):
    id = models.BigAutoField(primary_key=True)
    inventory = models.ForeignKey("PharmacyInventory", models.DO_NOTHING)
    delta_on_hand = models.IntegerField()
    reason = models.CharField(max_length=32)
    reference_type = models.CharField(max_length=32, blank=True, null=True)
    reference_id = models.PositiveBigIntegerField(blank=True, null=True)
    performed_by = models.ForeignKey("Users", models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "inventory_movements"


class LoyaltyAccounts(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.OneToOneField("Users", models.DO_NOTHING)
    tier = models.ForeignKey("LoyaltyTiers", models.DO_NOTHING)
    balance = models.PositiveIntegerField()
    social_document_number = models.CharField(max_length=6, blank=True, null=True)
    premium_active_until = models.DateTimeField(blank=True, null=True)
    premium_status = models.CharField(max_length=16, default="INACTIVE")
    premium_monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default="30.00")
    premium_payment_status = models.CharField(max_length=16, default="NOT_PAID")
    premium_payment_reference = models.CharField(max_length=100, blank=True, null=True)
    premium_payment_key = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "loyalty_accounts"


class LoyaltyTiers(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=24)
    bonus_rate = models.DecimalField(max_digits=5, decimal_places=4)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        managed = False
        db_table = "loyalty_tiers"


class LoyaltyTransactions(models.Model):
    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey(LoyaltyAccounts, models.DO_NOTHING)
    order = models.ForeignKey("Orders", models.DO_NOTHING, blank=True, null=True)
    points_delta = models.IntegerField()
    type = models.CharField(max_length=20)
    event_key = models.CharField(unique=True, max_length=100)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "loyalty_transactions"


class Manufacturers(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=160)

    class Meta:
        managed = False
        db_table = "manufacturers"


class NotificationPreferences(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField("Users", models.DO_NOTHING)
    promotions_enabled = models.BooleanField()
    reminders_enabled = models.BooleanField()

    class Meta:
        managed = False
        db_table = "notification_preferences"


class Notifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey("Users", models.DO_NOTHING)
    type = models.CharField(max_length=32)
    title = models.CharField(max_length=160)
    body = models.TextField()
    source_event_id = models.CharField(max_length=36, blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "notifications"
        unique_together = (("source_event_id", "user", "type"),)


class OrderItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey("Orders", models.DO_NOTHING)
    product = models.ForeignKey("Products", models.DO_NOTHING)
    product_name_snapshot = models.CharField(max_length=200)
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = "order_items"


class Orders(models.Model):
    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(unique=True, max_length=36)
    customer = models.ForeignKey("Users", models.DO_NOTHING)
    pharmacy = models.ForeignKey("Pharmacies", models.DO_NOTHING)
    status = models.CharField(max_length=32)
    fulfillment_method = models.CharField(max_length=16)
    payment_method = models.CharField(max_length=32)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    cancellation_reason_code = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "orders"


class OutboxEvents(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_id = models.CharField(unique=True, max_length=36)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField()
    status = models.CharField(max_length=16)
    attempts = models.PositiveIntegerField()
    available_at = models.DateTimeField()
    locked_until = models.DateTimeField(blank=True, null=True)
    last_error = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "outbox_events"


class Payments(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Orders, models.DO_NOTHING)
    provider = models.CharField(max_length=32)
    status = models.CharField(max_length=24)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    idempotency_key = models.CharField(unique=True, max_length=80)
    provider_reference = models.CharField(
        unique=True, max_length=100, blank=True, null=True
    )
    failure_code = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "payments"


class Pharmacies(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=32)
    name = models.CharField(max_length=160)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=32, blank=True, null=True)
    image_url = models.URLField(max_length=2048, blank=True, null=True)
    image_source_url = models.URLField(max_length=2048, blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "pharmacies"


class PharmacyInventory(models.Model):
    id = models.BigAutoField(primary_key=True)
    pharmacy = models.ForeignKey(Pharmacies, models.DO_NOTHING)
    product = models.ForeignKey("Products", models.DO_NOTHING)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    on_hand = models.PositiveIntegerField()
    reserved = models.PositiveIntegerField()
    is_listed = models.BooleanField()
    updated_at = models.DateTimeField()
    version = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "pharmacy_inventory"
        unique_together = (("pharmacy", "product"),)


class PrescriptionRecords(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey("Users", models.DO_NOTHING)
    display_label = models.CharField(max_length=100)
    masked_reference = models.CharField(max_length=40, blank=True, null=True)
    is_demo = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "prescription_records"


class PrescriptionVerifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Orders, models.DO_NOTHING)
    checked_by = models.ForeignKey("Users", models.DO_NOTHING)
    status = models.CharField(max_length=16)
    is_demo = models.BooleanField()
    checked_at = models.DateTimeField()
    note = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "prescription_verifications"


class Products(models.Model):
    id = models.BigAutoField(primary_key=True)
    sku = models.CharField(unique=True, max_length=64)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=2048, blank=True, null=True)
    image_source_url = models.URLField(max_length=2048, blank=True, null=True)
    category = models.ForeignKey(Categories, models.DO_NOTHING)
    manufacturer = models.ForeignKey(Manufacturers, models.DO_NOTHING)
    prescription_required = models.BooleanField()
    storage_min_c = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    storage_max_c = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "products"


class PromotionProducts(models.Model):
    id = models.BigAutoField(primary_key=True)
    promotion = models.ForeignKey("Promotions", models.DO_NOTHING)
    product = models.ForeignKey(Products, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "promotion_products"
        unique_together = (("promotion", "product"),)


class Promotions(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50)
    description = models.CharField(max_length=200, blank=True, null=True)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=4)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "promotions"


class Refunds(models.Model):
    id = models.BigAutoField(primary_key=True)
    payment = models.ForeignKey(Payments, models.DO_NOTHING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16)
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "refunds"


class Reminders(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey("Users", models.DO_NOTHING)
    product = models.ForeignKey(Products, models.DO_NOTHING)
    next_run_at = models.DateTimeField()
    interval_days = models.PositiveIntegerField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "reminders"


class Reservations(models.Model):
    id = models.BigAutoField(primary_key=True)
    order_item = models.OneToOneField(OrderItems, models.DO_NOTHING)
    inventory = models.ForeignKey(PharmacyInventory, models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=16)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "reservations"


class Users(models.Model):
    @property
    def is_authenticated(self):
        return bool(self.is_active)

    @property
    def is_anonymous(self):
        return False

    id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=150)
    email = models.CharField(unique=True, max_length=254)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=16)
    is_active = models.BooleanField()
    is_staff = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"
