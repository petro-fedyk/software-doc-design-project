ALTER TABLE orders
  ADD COLUMN cancellation_reason_code VARCHAR(32) NULL;

ALTER TABLE orders
  ADD CONSTRAINT chk_orders_cancellation_reason
    CHECK (cancellation_reason_code IS NULL OR cancellation_reason_code IN (
      'OUT_OF_STOCK',
      'PRICE_CHANGED',
      'PRESCRIPTION_ISSUE',
      'DELIVERY_UNAVAILABLE',
      'OTHER',
      'CUSTOMER_REQUEST'
    ));
