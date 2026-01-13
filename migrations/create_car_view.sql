-- Migration: Create car_view for API backward compatibility
-- This view flattens the Brand -> Model -> Offer relationship

CREATE OR REPLACE VIEW car_view AS
SELECT
    o.id,
    b.name AS brand,
    m.name AS model,
    o.year_manufacture,
    o.mileage,
    o.power,
    o.price,
    o.url,
    o.years_in_usage,
    o.price_per_km,
    o.mileage_per_year
FROM offers o
INNER JOIN models m ON o.model_id = m.id
INNER JOIN brands b ON m.brand_id = b.id;

-- Create indexes on offers table for better query performance
CREATE INDEX IF NOT EXISTS idx_offers_model_id ON offers(model_id);
CREATE INDEX IF NOT EXISTS idx_offers_price ON offers(price);
CREATE INDEX IF NOT EXISTS idx_offers_year_manufacture ON offers(year_manufacture);
CREATE INDEX IF NOT EXISTS idx_offers_mileage ON offers(mileage);
CREATE INDEX IF NOT EXISTS idx_offers_unique_id ON offers(unique_id);

-- Note: Run this migration after creating the database schema
-- Usage: mysql -u root -p bazos_cars < migrations/create_car_view.sql
