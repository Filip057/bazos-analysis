-- Migration: Add review_status column to offers table
-- Allows marking suspicious offers as reviewed so they don't appear again.
--
-- Values: NULL (not reviewed), 'checked' (reviewed OK), 'dismissed' (junk)
--
-- Usage:
--   mysql -u root -p bazos_cars < migrations/add_review_status.sql

USE bazos_cars;

-- 1. Add review_status column (safe: check if it already exists)
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'bazos_cars' AND TABLE_NAME = 'offers' AND COLUMN_NAME = 'review_status'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE offers ADD COLUMN review_status VARCHAR(20) NULL AFTER mileage_per_year',
    'SELECT "Column review_status already exists" AS info'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add index for filtering by status (safe: ignore if exists)
CREATE INDEX idx_review_status ON offers (review_status);

-- 3. Recreate car_view to include review_status
DROP VIEW IF EXISTS car_view;

CREATE VIEW car_view AS
SELECT
    o.id,
    b.name   AS brand,
    m.name   AS model,
    o.year_manufacture,
    o.mileage,
    o.power,
    o.fuel,
    o.price,
    o.url,
    o.scraped_at,
    o.years_in_usage,
    o.price_per_km,
    o.mileage_per_year,
    o.review_status
FROM offers o
JOIN models m  ON o.model_id  = m.id
JOIN brands b  ON m.brand_id  = b.id;

-- Verify
SELECT 'Migration complete.' AS status;
SELECT COUNT(*) AS total_offers FROM offers;
SELECT COUNT(*) AS offers_with_status FROM offers WHERE review_status IS NOT NULL;
