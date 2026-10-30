-- Use the existing payments table while clearly identifying simulator records.
ALTER TABLE payments DROP CHECK chk_payments_provider;
ALTER TABLE payments
  ADD CONSTRAINT chk_payments_provider
  CHECK (provider IN (
    'CARD_PROCESSOR',
    'BANK_TRANSFER',
    'CASH_ON_DELIVERY',
    'PAYMENT_GATEWAY',
    'EDUCATIONAL_SIMULATOR'
  ));
