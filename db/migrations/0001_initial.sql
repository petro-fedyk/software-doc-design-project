-- Internet Pharmacy Stage 06 schema. MySQL 8.0.16+ / InnoDB / utf8mb4.
-- Versioned SQL is the schema source of truth. No stored procedures or triggers.

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(150) NOT NULL,
  email VARCHAR(254) NOT NULL,
  password VARCHAR(128) NOT NULL,
  role VARCHAR(16) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_staff BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email),
  CONSTRAINT chk_users_role CHECK (role IN ('ADMIN','STAFF','CUSTOMER'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS pharmacies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL,
  name VARCHAR(160) NOT NULL,
  address VARCHAR(300) NOT NULL,
  city VARCHAR(100) NOT NULL,
  phone VARCHAR(32) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pharmacies_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS employee_assignments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  pharmacy_id BIGINT UNSIGNED NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_employee_assignments_user_pharmacy (user_id, pharmacy_id),
  KEY ix_employee_assignments_pharmacy_active (pharmacy_id, is_active),
  CONSTRAINT fk_employee_assignments_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_employee_assignments_pharmacy FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS customer_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  phone VARCHAR(32) NULL,
  full_name VARCHAR(200) NOT NULL,
  preferred_pharmacy_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_customer_profiles_user (user_id),
  CONSTRAINT fk_customer_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_customer_profiles_pharmacy FOREIGN KEY (preferred_pharmacy_id) REFERENCES pharmacies(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS categories (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_categories_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS manufacturers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(160) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_manufacturers_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS products (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sku VARCHAR(64) NOT NULL,
  name VARCHAR(200) NOT NULL,
  description TEXT NULL,
  category_id BIGINT UNSIGNED NOT NULL,
  manufacturer_id BIGINT UNSIGNED NOT NULL,
  prescription_required BOOLEAN NOT NULL,
  storage_min_c DECIMAL(5,2) NULL,
  storage_max_c DECIMAL(5,2) NULL,
  is_active BOOLEAN NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_products_sku (sku),
  KEY ix_products_category (category_id),
  KEY ix_products_manufacturer (manufacturer_id),
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
  CONSTRAINT fk_products_manufacturer FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE RESTRICT,
  CONSTRAINT chk_products_storage_range CHECK (storage_min_c IS NULL OR storage_max_c IS NULL OR storage_min_c <= storage_max_c)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS pharmacy_inventory (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  pharmacy_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  on_hand INT UNSIGNED NOT NULL,
  reserved INT UNSIGNED NOT NULL,
  is_listed BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at DATETIME(6) NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pharmacy_inventory_pharmacy_product (pharmacy_id, product_id),
  KEY ix_pharmacy_inventory_product_listed (product_id, is_listed),
  CONSTRAINT fk_pharmacy_inventory_pharmacy FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pharmacy_inventory_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT chk_pharmacy_inventory_price CHECK (unit_price >= 0),
  CONSTRAINT chk_pharmacy_inventory_reserved CHECK (reserved <= on_hand)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS inventory_movements (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  inventory_id BIGINT UNSIGNED NOT NULL,
  delta_on_hand INT NOT NULL,
  reason VARCHAR(32) NOT NULL,
  reference_type VARCHAR(32) NULL,
  reference_id BIGINT UNSIGNED NULL,
  performed_by_id BIGINT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  KEY ix_inventory_movements_inventory_created (inventory_id, created_at),
  KEY ix_inventory_movements_performed_by (performed_by_id),
  CONSTRAINT fk_inventory_movements_inventory FOREIGN KEY (inventory_id) REFERENCES pharmacy_inventory(id) ON DELETE RESTRICT,
  CONSTRAINT fk_inventory_movements_user FOREIGN KEY (performed_by_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT chk_inventory_movements_reason CHECK (reason IN ('RECEIPT','ADJUSTMENT','FULFILLMENT','RETURN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS carts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id BIGINT UNSIGNED NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_carts_customer (customer_id),
  CONSTRAINT fk_carts_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS cart_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cart_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cart_items_cart_product (cart_id, product_id),
  KEY ix_cart_items_product (product_id),
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT chk_cart_items_quantity CHECK (quantity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS orders (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_number VARCHAR(36) NOT NULL,
  customer_id BIGINT UNSIGNED NOT NULL,
  pharmacy_id BIGINT UNSIGNED NOT NULL,
  status VARCHAR(32) NOT NULL,
  fulfillment_method VARCHAR(16) NOT NULL,
  payment_method VARCHAR(32) NOT NULL,
  subtotal DECIMAL(12,2) NOT NULL,
  discount_total DECIMAL(12,2) NOT NULL,
  shipping_total DECIMAL(12,2) NOT NULL,
  grand_total DECIMAL(12,2) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'UAH',
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_orders_order_number (order_number),
  KEY ix_orders_customer_created (customer_id, created_at),
  KEY ix_orders_pharmacy_status_created (pharmacy_id, status, created_at),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_orders_pharmacy FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id) ON DELETE RESTRICT,
  CONSTRAINT chk_orders_fulfillment CHECK (fulfillment_method IN ('PICKUP','COURIER','POSTAL')),
  CONSTRAINT chk_orders_status CHECK (status IN ('PENDING_CONFIRMATION','CONFIRMED','PROCESSING','READY_FOR_PICKUP','AWAITING_SHIPMENT','SHIPPED','COMPLETED','CANCELLED')),
  CONSTRAINT chk_orders_subtotal CHECK (subtotal >= 0),
  CONSTRAINT chk_orders_discount CHECK (discount_total >= 0),
  CONSTRAINT chk_orders_shipping CHECK (shipping_total >= 0),
  CONSTRAINT chk_orders_grand_total CHECK (grand_total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS order_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  product_name_snapshot VARCHAR(200) NOT NULL,
  unit_price_snapshot DECIMAL(12,2) NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  line_total DECIMAL(12,2) NOT NULL,
  PRIMARY KEY (id),
  KEY ix_order_items_order (order_id),
  KEY ix_order_items_product (product_id),
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT chk_order_items_price CHECK (unit_price_snapshot >= 0),
  CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
  CONSTRAINT chk_order_items_total CHECK (line_total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS reservations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_item_id BIGINT UNSIGNED NOT NULL,
  inventory_id BIGINT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  status VARCHAR(16) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_reservations_order_item (order_item_id),
  KEY ix_reservations_status_expires (status, expires_at),
  KEY ix_reservations_inventory_status (inventory_id, status),
  CONSTRAINT fk_reservations_order_item FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE RESTRICT,
  CONSTRAINT fk_reservations_inventory FOREIGN KEY (inventory_id) REFERENCES pharmacy_inventory(id) ON DELETE RESTRICT,
  CONSTRAINT chk_reservations_quantity CHECK (quantity > 0),
  CONSTRAINT chk_reservations_status CHECK (status IN ('ACTIVE','FULFILLED','CANCELLED','EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS payments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  provider VARCHAR(32) NOT NULL,
  status VARCHAR(24) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  idempotency_key VARCHAR(80) NOT NULL,
  provider_reference VARCHAR(100) NULL,
  failure_code VARCHAR(64) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_payments_idempotency_key (idempotency_key),
  UNIQUE KEY uq_payments_provider_reference (provider_reference),
  KEY ix_payments_order_status (order_id, status),
  CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT chk_payments_provider CHECK (provider IN ('DEMO_CARD','DEMO_CRYPTO','DEMO_PAYPAL','DEMO_MONO')),
  CONSTRAINT chk_payments_status CHECK (status IN ('PENDING','SUCCEEDED','FAILED','UNKNOWN','REFUNDED')),
  CONSTRAINT chk_payments_amount CHECK (amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS refunds (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  payment_id BIGINT UNSIGNED NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status VARCHAR(16) NOT NULL,
  reason VARCHAR(200) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  KEY ix_refunds_payment (payment_id),
  CONSTRAINT fk_refunds_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
  CONSTRAINT chk_refunds_amount CHECK (amount > 0),
  CONSTRAINT chk_refunds_status CHECK (status IN ('PENDING','SUCCEEDED','FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS deliveries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  method VARCHAR(16) NOT NULL,
  recipient_name VARCHAR(200) NULL,
  recipient_phone VARCHAR(32) NULL,
  destination VARCHAR(300) NULL,
  provider VARCHAR(32) NULL,
  status VARCHAR(24) NOT NULL,
  tracking_reference VARCHAR(100) NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_deliveries_order (order_id),
  CONSTRAINT fk_deliveries_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT chk_deliveries_method CHECK (method IN ('PICKUP','COURIER','POSTAL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS delivery_rules (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  method VARCHAR(16) NOT NULL,
  requires_cold_chain BOOLEAN NOT NULL,
  cold_chain_supported BOOLEAN NOT NULL,
  enabled BOOLEAN NOT NULL,
  max_storage_min_c DECIMAL(5,2) NULL,
  min_storage_max_c DECIMAL(5,2) NULL,
  PRIMARY KEY (id),
  KEY ix_delivery_rules_method_enabled (method, enabled),
  CONSTRAINT chk_delivery_rules_method CHECK (method IN ('PICKUP','COURIER','POSTAL')),
  CONSTRAINT chk_delivery_rules_temp_range CHECK (max_storage_min_c IS NULL OR min_storage_max_c IS NULL OR max_storage_min_c <= min_storage_max_c)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS prescription_records (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id BIGINT UNSIGNED NOT NULL,
  display_label VARCHAR(100) NOT NULL,
  masked_reference VARCHAR(40) NULL,
  is_demo BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  KEY ix_prescription_records_customer_created (customer_id, created_at),
  CONSTRAINT fk_prescription_records_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS prescription_verifications (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  checked_by_id BIGINT UNSIGNED NOT NULL,
  status VARCHAR(16) NOT NULL,
  is_demo BOOLEAN NOT NULL DEFAULT TRUE,
  checked_at DATETIME(6) NOT NULL,
  note VARCHAR(300) NULL,
  PRIMARY KEY (id),
  KEY ix_prescription_verifications_order_checked (order_id, checked_at),
  KEY ix_prescription_verifications_user (checked_by_id),
  CONSTRAINT fk_prescription_verifications_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT fk_prescription_verifications_user FOREIGN KEY (checked_by_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT chk_prescription_verifications_status CHECK (status IN ('APPROVED','REJECTED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS loyalty_tiers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(24) NOT NULL,
  bonus_rate DECIMAL(5,4) NOT NULL,
  discount_rate DECIMAL(5,4) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_loyalty_tiers_code (code),
  CONSTRAINT chk_loyalty_tiers_code CHECK (code IN ('STANDARD','SOCIAL','PREMIUM')),
  CONSTRAINT chk_loyalty_tiers_bonus_rate CHECK (bonus_rate BETWEEN 0 AND 1),
  CONSTRAINT chk_loyalty_tiers_discount_rate CHECK (discount_rate BETWEEN 0 AND 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS loyalty_accounts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id BIGINT UNSIGNED NOT NULL,
  tier_id BIGINT UNSIGNED NOT NULL,
  balance INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_loyalty_accounts_customer (customer_id),
  KEY ix_loyalty_accounts_tier (tier_id),
  CONSTRAINT fk_loyalty_accounts_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_loyalty_accounts_tier FOREIGN KEY (tier_id) REFERENCES loyalty_tiers(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS loyalty_transactions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  account_id BIGINT UNSIGNED NOT NULL,
  order_id BIGINT UNSIGNED NULL,
  points_delta INT NOT NULL,
  type VARCHAR(20) NOT NULL,
  event_key VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_loyalty_transactions_event_key (event_key),
  KEY ix_loyalty_transactions_account_created (account_id, created_at),
  KEY ix_loyalty_transactions_order (order_id),
  CONSTRAINT fk_loyalty_transactions_account FOREIGN KEY (account_id) REFERENCES loyalty_accounts(id) ON DELETE RESTRICT,
  CONSTRAINT fk_loyalty_transactions_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT chk_loyalty_transactions_delta CHECK (points_delta <> 0),
  CONSTRAINT chk_loyalty_transactions_type CHECK (type IN ('EARN','REDEEM','ADJUST'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS promotions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(50) NOT NULL,
  description VARCHAR(200) NULL,
  discount_rate DECIMAL(5,4) NOT NULL,
  starts_at DATETIME(6) NOT NULL,
  ends_at DATETIME(6) NOT NULL,
  is_active BOOLEAN NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_promotions_code (code),
  KEY ix_promotions_active_period (is_active, starts_at, ends_at),
  CONSTRAINT chk_promotions_discount_rate CHECK (discount_rate BETWEEN 0 AND 1),
  CONSTRAINT chk_promotions_period CHECK (ends_at > starts_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS promotion_products (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  promotion_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_promotion_products_promotion_product (promotion_id, product_id),
  KEY ix_promotion_products_product (product_id),
  CONSTRAINT fk_promotion_products_promotion FOREIGN KEY (promotion_id) REFERENCES promotions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_promotion_products_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS notifications (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  type VARCHAR(32) NOT NULL,
  title VARCHAR(160) NOT NULL,
  body TEXT NOT NULL,
  read_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  KEY ix_notifications_user_created (user_id, created_at),
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT chk_notifications_type CHECK (type IN ('ORDER','AVAILABILITY','LOYALTY','PROMOTION','REMINDER'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS availability_subscriptions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  pharmacy_id BIGINT UNSIGNED NOT NULL,
  is_active BOOLEAN NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_availability_customer_product_pharmacy (customer_id, product_id, pharmacy_id),
  CONSTRAINT fk_availability_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_availability_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT fk_availability_pharmacy FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS reminders (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  next_run_at DATETIME(6) NOT NULL,
  interval_days INT UNSIGNED NOT NULL,
  is_active BOOLEAN NOT NULL,
  PRIMARY KEY (id),
  KEY ix_reminders_customer_active_next (customer_id, is_active, next_run_at),
  CONSTRAINT fk_reminders_customer FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_reminders_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT chk_reminders_interval CHECK (interval_days > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS notification_preferences (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  promotions_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  reminders_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (id),
  UNIQUE KEY uq_notification_preferences_user (user_id),
  CONSTRAINT fk_notification_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS outbox_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_id CHAR(36) NOT NULL,
  event_type VARCHAR(80) NOT NULL,
  payload JSON NOT NULL,
  status VARCHAR(16) NOT NULL,
  attempts INT UNSIGNED NOT NULL DEFAULT 0,
  available_at DATETIME(6) NOT NULL,
  locked_until DATETIME(6) NULL,
  last_error VARCHAR(300) NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_outbox_events_event_id (event_id),
  KEY ix_outbox_events_status_available_id (status, available_at, id),
  CONSTRAINT chk_outbox_events_status CHECK (status IN ('PENDING','PROCESSING','DONE','FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS audit_entries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  actor_id BIGINT UNSIGNED NULL,
  action VARCHAR(80) NOT NULL,
  target_type VARCHAR(50) NOT NULL,
  target_id BIGINT UNSIGNED NULL,
  occurred_at DATETIME(6) NOT NULL,
  details JSON NULL,
  PRIMARY KEY (id),
  KEY ix_audit_entries_actor_occurred (actor_id, occurred_at),
  KEY ix_audit_entries_target (target_type, target_id),
  CONSTRAINT fk_audit_entries_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
