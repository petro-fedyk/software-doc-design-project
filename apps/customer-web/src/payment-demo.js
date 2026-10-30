const DEMO_CARD = Object.freeze({
  cardholder: "DEMO USER",
  cardNumber: "0000000000000000",
  expiry: "12/30",
  cvv: "000",
});

export function isFictionalDemoCard({ cardholder, card_number, expiry, cvv }) {
  return String(cardholder || "").trim().toUpperCase() === DEMO_CARD.cardholder
    && String(card_number || "").replace(/\s/g, "") === DEMO_CARD.cardNumber
    && String(expiry || "").trim() === DEMO_CARD.expiry
    && String(cvv || "").trim() === DEMO_CARD.cvv;
}

export function demoPaymentRequestPayload(idempotencyKey, scenario) {
  if (!["APPROVED", "DECLINED", "TIMEOUT"].includes(scenario)) {
    throw new TypeError("Unsupported educational payment scenario");
  }
  return { idempotency_key: idempotencyKey, demo_scenario: scenario };
}
