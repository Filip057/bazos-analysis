-- Initial database setup for bazos_cars
-- Creates all tables with fuel and scraped_at columns

USE bazos_cars;

-- Brands table
CREATE TABLE IF NOT EXISTS brands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    INDEX idx_brand_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Models table
CREATE TABLE IF NOT EXISTS models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    brand_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    INDEX idx_brand_id (brand_id),
    INDEX idx_model_name (name),
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Offers table (with fuel and scraped_at from start)
CREATE TABLE IF NOT EXISTS offers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unique_id VARCHAR(255) UNIQUE,
    model_id INT NOT NULL,
    year_manufacture INT,
    mileage BIGINT,
    power INT,
    fuel VARCHAR(50),
    price INT,
    url VARCHAR(255),
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model_id (model_id),
    INDEX idx_price (price),
    INDEX idx_year_manufacture (year_manufacture),
    INDEX idx_mileage (mileage),
    INDEX idx_unique_id (unique_id),
    INDEX idx_scraped_at (scraped_at),
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Database initialized successfully!' AS status;
