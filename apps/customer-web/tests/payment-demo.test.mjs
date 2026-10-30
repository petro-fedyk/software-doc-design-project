import test from "node:test";
import assert from "node:assert/strict";
import { demoPaymentRequestPayload, isFictionalDemoCard } from "../src/payment-demo.js";

const designated = {
  cardholder: "DEMO USER",
  card_number: "0000 0000 0000 0000",
  expiry: "12/30",
  cvv: "000",
};

test("accepts only the documented fictional card tuple", () => {
  assert.equal(isFictionalDemoCard(designated), true);
  assert.equal(isFictionalDemoCard({ ...designated, card_number: "1234 5678 9012 3456" }), false);
  assert.equal(isFictionalDemoCard({ ...designated, cvv: "123" }), false);
  assert.equal(isFictionalDemoCard({ ...designated, cardholder: "Jane Doe" }), false);
});

test("payment API payload contains only an idempotency key and scenario", () => {
  assert.deepEqual(demoPaymentRequestPayload("demo-key-123456", "APPROVED"), {
    idempotency_key: "demo-key-123456",
    demo_scenario: "APPROVED",
  });
  assert.throws(() => demoPaymentRequestPayload("demo-key-123456", "SUCCESS"), TypeError);
});
