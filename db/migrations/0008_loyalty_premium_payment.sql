ALTER TABLE loyalty_accounts
  ADD COLUMN premium_payment_status VARCHAR(16) NOT NULL DEFAULT 'NOT_PAID',
  ADD COLUMN premium_payment_reference VARCHAR(100) NULL,
  ADD COLUMN premium_payment_key VARCHAR(100) NULL;

ALTER TABLE loyalty_accounts
  ADD CONSTRAINT chk_loyalty_accounts_premium_payment_status
    CHECK (premium_payment_status IN ('NOT_PAID','SUCCEEDED','FAILED','UNKNOWN'));
