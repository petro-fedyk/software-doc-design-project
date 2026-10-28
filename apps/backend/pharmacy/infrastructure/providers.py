from hashlib import sha256


class SimulatedPaymentGateway:
    def __init__(self, succeed=True):
        self.succeed = succeed

    def authorize(self, reference, amount, idempotency_key):
        return {
            "status": "SUCCEEDED" if self.succeed else "FAILED",
            "reference": "SIM-" + sha256(idempotency_key.encode()).hexdigest()[:32],
            "failure_code": None if self.succeed else "SIMULATED_DECLINE",
        }

    def refund(self, reference, amount, idempotency_key):
        return self.authorize(reference, amount, idempotency_key)


class SimulatedShipmentProvider:
    def prepare(self, order_id, method):
        return f"SIM-{method}-{order_id}"
