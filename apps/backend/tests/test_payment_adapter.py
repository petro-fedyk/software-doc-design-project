import pytest

from pharmacy.infrastructure.providers import SimulatedPaymentGateway


@pytest.mark.parametrize(
    ("scenario", "status", "failure_code"),
    [
        ("APPROVED", "SUCCEEDED", None),
        ("DECLINED", "FAILED", "DEMO_DECLINED"),
        ("TIMEOUT", "UNKNOWN", "DEMO_TIMEOUT"),
    ],
)
def test_gateway_returns_explicit_educational_scenario(scenario, status, failure_code):
    result = SimulatedPaymentGateway().authorize(
        "order-1", "10.00", "idempotency-123", scenario=scenario
    )
    assert result["status"] == status
    assert result["failure_code"] == failure_code
    assert result["reference"].startswith("DEMO-")


def test_gateway_rejects_unknown_scenarios():
    with pytest.raises(ValueError):
        SimulatedPaymentGateway().authorize(
            "order-1", "10.00", "idempotency-123", scenario="PAID"
        )
