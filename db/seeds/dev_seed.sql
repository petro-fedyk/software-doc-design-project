-- Development-only, synthetic and repeatable reference data. No users or credentials.
INSERT INTO pharmacies (code, name, address, city, phone, is_active)
VALUES ('DEMO-KYIV-01', 'Demo Central Pharmacy', '1 Example Street', 'Kyiv', '+380000000001', TRUE)
ON DUPLICATE KEY UPDATE name=VALUES(name), address=VALUES(address), city=VALUES(city), phone=VALUES(phone), is_active=VALUES(is_active);

INSERT INTO categories (name) VALUES ('Demo OTC'), ('Demo Prescription')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO manufacturers (name) VALUES ('Demo Manufacturer')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO products (sku, name, description, category_id, manufacturer_id, prescription_required, storage_min_c, storage_max_c, is_active)
SELECT s.sku, s.name, s.description, c.id, m.id, s.prescription_required, s.storage_min_c, s.storage_max_c, TRUE
FROM (
  SELECT 'DEMO-OTC-001' sku, 'Demo Vitamin Tablets' name, 'Synthetic development seed item.' description, 'Demo OTC' category_name, FALSE prescription_required, NULL storage_min_c, NULL storage_max_c
  UNION ALL SELECT 'DEMO-OTC-COLD-001', 'Demo Cold-Chain Product', 'Synthetic temperature-restricted seed item.', 'Demo OTC', FALSE, 2.00, 8.00
  UNION ALL SELECT 'DEMO-RX-001', 'Demo Prescription Product', 'Synthetic prescription-only seed item.', 'Demo Prescription', TRUE, NULL, NULL
) s JOIN categories c ON c.name=s.category_name JOIN manufacturers m ON m.name='Demo Manufacturer'
ON DUPLICATE KEY UPDATE name=VALUES(name), description=VALUES(description), category_id=VALUES(category_id), manufacturer_id=VALUES(manufacturer_id), prescription_required=VALUES(prescription_required), storage_min_c=VALUES(storage_min_c), storage_max_c=VALUES(storage_max_c), is_active=TRUE;

INSERT INTO pharmacy_inventory (pharmacy_id, product_id, unit_price, on_hand, reserved, is_listed, updated_at, version)
SELECT p.id, pr.id, s.unit_price, s.on_hand, 0, TRUE, UTC_TIMESTAMP(6), 0
FROM (SELECT 'DEMO-OTC-001' sku, 125.00 unit_price, 25 on_hand UNION ALL SELECT 'DEMO-OTC-COLD-001', 240.00, 8 UNION ALL SELECT 'DEMO-RX-001', 399.00, 5) s
JOIN products pr ON pr.sku=s.sku JOIN pharmacies p ON p.code='DEMO-KYIV-01'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price), is_listed=VALUES(is_listed), updated_at=UTC_TIMESTAMP(6);

INSERT INTO loyalty_tiers (code, bonus_rate, discount_rate) VALUES
('STANDARD', 0.0100, 0.0000), ('SOCIAL', 0.0250, 0.0300), ('PREMIUM', 0.0500, 0.0700)
ON DUPLICATE KEY UPDATE bonus_rate=VALUES(bonus_rate), discount_rate=VALUES(discount_rate);

INSERT INTO delivery_rules (method, requires_cold_chain, cold_chain_supported, enabled, max_storage_min_c, min_storage_max_c)
SELECT s.method, s.requires_cold_chain, s.cold_chain_supported, TRUE, s.max_storage_min_c, s.min_storage_max_c
FROM (SELECT 'PICKUP' method, FALSE requires_cold_chain, TRUE cold_chain_supported, NULL max_storage_min_c, NULL min_storage_max_c
      UNION ALL SELECT 'COURIER', FALSE, FALSE, NULL, NULL
      UNION ALL SELECT 'POSTAL', FALSE, FALSE, NULL, NULL) s
WHERE NOT EXISTS (SELECT 1 FROM delivery_rules r WHERE r.method=s.method AND r.requires_cold_chain=s.requires_cold_chain AND r.cold_chain_supported=s.cold_chain_supported AND r.max_storage_min_c <=> s.max_storage_min_c AND r.min_storage_max_c <=> s.min_storage_max_c);

INSERT INTO promotions (code, description, discount_rate, starts_at, ends_at, is_active)
VALUES ('DEMO-10', 'Synthetic development promotion', 0.1000, '2026-01-01 00:00:00.000000', '2030-01-01 00:00:00.000000', TRUE)
ON DUPLICATE KEY UPDATE description=VALUES(description), discount_rate=VALUES(discount_rate), starts_at=VALUES(starts_at), ends_at=VALUES(ends_at), is_active=VALUES(is_active);
