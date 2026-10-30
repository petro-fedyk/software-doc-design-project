# Educational card-payment simulator

This coursework flow is not a payment integration. No bank connection, real card, or money movement is involved.

## Customer use case

The signed-in customer selects a CARD payment method directly in the cart. The cart displays the card form and accepts only this fictional credential tuple:

| Field | Designated value |
|---|---|
| Cardholder | `DEMO USER` |
| Card number | `0000 0000 0000 0000` |
| Expiration | `12/30` |
| CVV | `000` |

All other values are rejected locally, including normal-looking card numbers. The fields are cleared before any request and are never included in network requests, browser storage, application logs, or MySQL. After the server returns its quote, the customer confirms the total and the portal creates the order, then requests payment. The customer chooses a demonstration result: `APPROVED`, `DECLINED`, or `TIMEOUT`.

## Backend flow

`POST /api/orders/{id}/pay/` accepts only `idempotency_key` and `demo_scenario`. `PaymentApplicationService` verifies the customer owns the order, creates/reuses one payment in the existing `payments` table, and adds one `payment.requested` outbox event. The event payload carries the scenario, order ID, and payment ID; it contains no card data. `EventApplicationService` invokes `SimulatedPaymentGateway`, which maps the explicit outcome to `SUCCEEDED`, `FAILED`, or `UNKNOWN`. `DjangoPaymentRepository` persists that state. Duplicate requests with the same idempotency key return the existing payment and do not enqueue a second event.

The payment outcome does not move the order through fulfilment states. The existing order workflow remains authoritative, and staff shipment/completion checks the persisted payment state. The customer can review the result at **Мій кабінет → Замовлення**.

## API contract

```http
POST /api/orders/{id}/pay/
Authorization: Bearer <customer token>
Content-Type: application/json

{"idempotency_key":"demo-request-123456","demo_scenario":"APPROVED"}
```

`demo_scenario` is one of `APPROVED`, `DECLINED`, `TIMEOUT`; it defaults to `APPROVED` for older coursework clients. Strict serialization rejects card-number, CVV, cardholder, and expiration fields. See `docs/backend/openapi.yaml` for the endpoint schema.

## Payment sequence

See [payment-demo.mmd](../diagrams/sequence/source/payment-demo.mmd). The state is written to the current MySQL database; no payment table/schema addition is used.

## Manual verification

1. Use a designated customer and place products in the cart.
2. Select CARD as the payment method. Verify the form appears below the selector and the server-calculated quote is shown before order confirmation.
3. Enter only the fictional tuple above and choose one outcome. Verify invalid values are rejected before a request.
4. Try a real-looking number or altered CVV once; the portal must reject it locally, clear all card fields, and make no API request. For the designated tuple, confirm the payment request body has exactly `idempotency_key` and `demo_scenario`; the test fields should be cleared before checkout requests.
5. Confirm the quoted order and wait for the existing outbox worker. Confirm customer history shows simulated success, rejection, or unresolved timeout.
6. Inspect MySQL `payments` and `outbox_events`: status/provider/scenario should persist; card fields/values should not. The order remains at its prior fulfilment state, and shipment remains gated by the payment state.
7. Replay the exact request with its idempotency key. Confirm there is still one payment and one payment event.

Do not use real credentials. Do not put card data in a curl command, ticket, screenshot, or log.
