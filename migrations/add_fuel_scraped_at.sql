-- Migration: Add fuel and scraped_at columns to offers table
-- Run this ONCE on an existing database.
-- New installs get these columns automatically via init_database().
--
-- Usage:
--   mysql -u root -p bazos_cars < migrations/add_fuel_scraped_at.sql
--
-- Safe to run: uses IF NOT EXISTS via ALTER TABLE ... MODIFY COLUMN pattern
-- and only adds columns that are missing.

USE bazos_cars;

-- 1. Add fuel column (type of fuel: diesel | benzín | lpg | elektro)
ALTER TABLE offers
    ADD COLUMN IF NOT EXISTS fuel VARCHAR(50) NULL AFTER power;

-- 2. Add scraped_at column (timestamp of last scrape for this offer)
ALTER TABLE offers
    ADD COLUMN IF NOT EXISTS scraped_at DATETIME NULL AFTER url;

-- 3. Add indexes for the new columns (skip if already exist)
CREATE INDEX IF NOT EXISTS idx_fuel      ON offers (fuel);
CREATE INDEX IF NOT EXISTS idx_scraped_at ON offers (scraped_at);

-- 4. Update car_view to include the new columns
--    Drop and recreate the view so it reflects the new offers columns.
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
    o.mileage_per_year
FROM offers o
JOIN models m  ON o.model_id  = m.id
JOIN brands b  ON m.brand_id  = b.id;

-- Verify
SELECT 'Migration complete.' AS status;
SELECT COUNT(*) AS total_offers FROM offers;
SELECT COUNT(*) AS offers_with_fuel      FROM offers WHERE fuel      IS NOT NULL;
SELECT COUNT(*) AS offers_with_scraped_at FROM offers WHERE scraped_at IS NOT NULL;
