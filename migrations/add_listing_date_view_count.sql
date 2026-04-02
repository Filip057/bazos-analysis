-- Migration: Add listing_date and view_count columns to offers table
-- listing_date: when the listing was created on bazos.cz
-- view_count: number of views at the time of scraping
--
-- Usage:
--   mysql -u root -p bazos_cars < migrations/add_listing_date_view_count.sql

USE bazos_cars;

-- 1. Add listing_date column (safe: check if exists)
SET @col1 = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'bazos_cars' AND TABLE_NAME = 'offers' AND COLUMN_NAME = 'listing_date'
);
SET @sql1 = IF(@col1 = 0,
    'ALTER TABLE offers ADD COLUMN listing_date DATE NULL AFTER scraped_at',
    'SELECT "Column listing_date already exists" AS info'
);
PREPARE stmt1 FROM @sql1;
EXECUTE stmt1;
DEALLOCATE PREPARE stmt1;

-- 2. Add view_count column
SET @col2 = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'bazos_cars' AND TABLE_NAME = 'offers' AND COLUMN_NAME = 'view_count'
);
SET @sql2 = IF(@col2 = 0,
    'ALTER TABLE offers ADD COLUMN view_count INT NULL AFTER listing_date',
    'SELECT "Column view_count already exists" AS info'
);
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 3. Add indexes
CREATE INDEX idx_listing_date ON offers (listing_date);
CREATE INDEX idx_view_count ON offers (view_count);

-- 4. Recreate car_view
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
    o.listing_date,
    o.view_count,
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
