from hashlib import sha256


class SimulatedPaymentGateway:
    """Local educational adapter; it never contacts a bank or handles card data."""

    SCENARIOS = {"APPROVED", "DECLINED", "TIMEOUT"}

    def __init__(self, succeed=True):
        self.succeed = succeed

    def authorize(self, reference, amount, idempotency_key, scenario=None):
        if scenario is not None and scenario not in self.SCENARIOS:
            raise ValueError("Unsupported educational payment scenario")
        status = {
            "APPROVED": "SUCCEEDED",
            "DECLINED": "FAILED",
            "TIMEOUT": "UNKNOWN",
        }.get(scenario, "SUCCEEDED" if self.succeed else "FAILED")
        suffix = scenario or ("APPROVED" if self.succeed else "DECLINED")
        return {
            "status": status,
            "reference": "DEMO-" + sha256(idempotency_key.encode()).hexdigest()[:32],
            "failure_code": None if status == "SUCCEEDED" else f"DEMO_{suffix}",
        }

    def refund(self, reference, amount, idempotency_key):
        return self.authorize(reference, amount, idempotency_key)


class SimulatedShipmentProvider:
    def prepare(self, order_id, method):
        return f"SIM-{method}-{order_id}"
