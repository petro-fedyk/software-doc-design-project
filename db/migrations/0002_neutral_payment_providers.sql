-- Allow payment method categories without claiming a concrete provider integration.
ALTER TABLE payments DROP CHECK chk_payments_provider;
ALTER TABLE payments
  ADD CONSTRAINT chk_payments_provider
  CHECK (provider IN ('CARD_PROCESSOR','BANK_TRANSFER','CASH_ON_DELIVERY','PAYMENT_GATEWAY'));
