"""Independent Observer subscribers; the outbox worker supplies atomic dispatch."""


class NotificationSubscriber:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def handle(self, payload):
        with self.uow_factory() as uow:
            order = uow.orders.get(payload["order_id"])
            order.status = payload.get("status", order.status)
            uow.engagement.notify_order(order, payload.get("_outbox_event_id"))
            uow.commit()


class LoyaltySubscriber:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def handle(self, payload):
        with self.uow_factory() as uow:
            order = uow.orders.get(payload["order_id"], lock=True)
            if order.status == "COMPLETED":
                uow.loyalty.accrue(order, payload.get("loyalty_points"))
            uow.commit()
