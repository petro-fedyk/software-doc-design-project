ALTER TABLE loyalty_accounts
  ADD COLUMN social_document_number CHAR(6) NULL,
  ADD COLUMN premium_active_until DATETIME(6) NULL,
  ADD COLUMN premium_status VARCHAR(16) NOT NULL DEFAULT 'INACTIVE',
  ADD COLUMN premium_monthly_price DECIMAL(8,2) NOT NULL DEFAULT 30.00;

ALTER TABLE loyalty_accounts
  ADD CONSTRAINT chk_loyalty_accounts_social_document
    CHECK (social_document_number IS NULL OR social_document_number REGEXP '^[0-9]{6}$'),
  ADD CONSTRAINT chk_loyalty_accounts_premium_status
    CHECK (premium_status IN ('INACTIVE','ACTIVE','EXPIRED'));
