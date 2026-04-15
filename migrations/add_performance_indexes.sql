-- Migration: Add composite indexes for common query patterns.
-- The car_view JOIN (offers → models → brands) benefits from existing FK indexes,
-- but aggregation queries need composite indexes on offers.

-- Composite index for deal detection: segment grouping + price filtering
CREATE INDEX IF NOT EXISTS idx_offers_model_price
    ON offers(model_id, price);

-- Composite index for fuel-based queries (fuel distribution, deal segments)
CREATE INDEX IF NOT EXISTS idx_offers_fuel
    ON offers(fuel);

-- Composite index for year + price range queries
CREATE INDEX IF NOT EXISTS idx_offers_year_price
    ON offers(year_manufacture, price);
