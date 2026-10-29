-- Store source-attributed remote product photos for the database-backed catalogue.
ALTER TABLE products
  ADD COLUMN image_url VARCHAR(2048) NULL AFTER description,
  ADD COLUMN image_source_url VARCHAR(2048) NULL AFTER image_url;
