"""Per-request constructor wiring; no mutable global service locator."""

from django.conf import settings
from pharmacy.application.services import (
    OrderApplicationService,
    PaymentApplicationService,
    InventoryApplicationService,
    CustomerApplicationService,
    EventApplicationService,
)
from pharmacy.infrastructure.repositories import DjangoUnitOfWork
from pharmacy.infrastructure.providers import (
    SimulatedPaymentGateway,
    SimulatedShipmentProvider,
)


class Services:
    def __init__(
        self, uow_factory=DjangoUnitOfWork, payment_gateway=None, shipment_provider=None
    ):
        self.orders = OrderApplicationService(
            uow_factory, enabled_methods=settings.ENABLED_PAYMENT_METHODS
        )
        self.payments = PaymentApplicationService(uow_factory)
        self.inventory = InventoryApplicationService(uow_factory)
        self.customers = CustomerApplicationService(uow_factory)
        self.events = EventApplicationService(
            uow_factory,
            payment_gateway or SimulatedPaymentGateway(),
            shipment_provider or SimulatedShipmentProvider(),
        )
