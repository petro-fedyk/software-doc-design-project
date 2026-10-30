import pytest
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from pharmacy import models as m


@pytest.fixture
def db(django_db_blocker):
    assert settings.DATABASES["default"]["NAME"].endswith("_test"), (
        "Tests require a separate *_test database provisioned with SQL migrations."
    )
    with django_db_blocker.unblock():
        with transaction.atomic():
            cache.clear()
            yield
            transaction.set_rollback(True)


@pytest.fixture
def records(db):
    now = timezone.now()
    password = make_password("pass")

    def user(name, role):
        return m.Users.objects.create(
            username=name,
            email=name + "@example.test",
            password=password,
            role=role,
            is_staff=role != "CUSTOMER",
            is_active=True,
            created_at=now,
        )

    customer = user("AA_customer", "CUSTOMER")
    other = user("other", "CUSTOMER")
    staff = user("SS_staff", "STAFF")
    admin = user("administrator", "ADMIN")
    outsider = user("outside", "STAFF")
    branch = m.Pharmacies.objects.create(
        code="B1",
        name="Test branch",
        address="Test address",
        city="Test city",
        is_active=True,
    )
    second = m.Pharmacies.objects.create(
        code="B2",
        name="Other branch",
        address="Test address",
        city="Test city",
        is_active=True,
    )
    m.EmployeeAssignments.objects.create(
        user=staff, pharmacy=branch, is_active=True, created_at=now
    )
    cat = m.Categories.objects.create(name="Test category")
    maker = m.Manufacturers.objects.create(name="Test maker")
    product = m.Products.objects.create(
        sku="TEST-OTC",
        name="Catalogue fixture",
        category=cat,
        manufacturer=maker,
        prescription_required=False,
        is_active=True,
    )
    rx = m.Products.objects.create(
        sku="TEST-RX",
        name="Prescription fixture",
        category=cat,
        manufacturer=maker,
        prescription_required=True,
        is_active=True,
    )
    for p in (product, rx):
        m.PharmacyInventory.objects.create(
            pharmacy=branch,
            product=p,
            unit_price="100.00",
            on_hand=10,
            reserved=0,
            is_listed=True,
            updated_at=now,
            version=0,
        )
    tier = m.LoyaltyTiers.objects.create(
        code="STANDARD", discount_rate=0, bonus_rate=".05"
    )
    m.LoyaltyAccounts.objects.create(customer=customer, tier=tier, balance=0)
    for method in ("COURIER", "POSTAL"):
        m.DeliveryRules.objects.create(
            method=method,
            requires_cold_chain=False,
            cold_chain_supported=False,
            enabled=True,
        )
    return locals()


@pytest.fixture
def client_for():
    from rest_framework.test import APIClient
    from pharmacy.api.auth import issue_token

    def factory(user=None):
        client = APIClient()
        if user:
            client.credentials(HTTP_AUTHORIZATION="Bearer " + issue_token(user))
        return client

    return factory
