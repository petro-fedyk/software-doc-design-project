-- Store branch facade image and its source on the pharmacy record.
ALTER TABLE pharmacies
  ADD COLUMN image_url VARCHAR(2048) NULL AFTER phone,
  ADD COLUMN image_source_url VARCHAR(2048) NULL AFTER image_url;
