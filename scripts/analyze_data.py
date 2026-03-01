#!/usr/bin/env python3
"""
Analyze scraped data quality and prepare for cleaning
"""
from sqlalchemy import create_engine, text
from webapp.config import get_config
import pandas as pd

config = get_config()
engine = create_engine(config.DATABASE_URI)

print("=" * 80)
print("DATA QUALITY ANALYSIS - Skoda Offers")
print("=" * 80)

with engine.connect() as conn:
    # 1. Overall completeness
    print("\n1. DATA COMPLETENESS:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT
            COUNT(*) as total_offers,
            COUNT(DISTINCT model_id) as unique_models,
            ROUND(100.0 * COUNT(CASE WHEN year_manufacture IS NOT NULL THEN 1 END) / COUNT(*), 1) as year_pct,
            ROUND(100.0 * COUNT(CASE WHEN mileage IS NOT NULL THEN 1 END) / COUNT(*), 1) as mileage_pct,
            ROUND(100.0 * COUNT(CASE WHEN power IS NOT NULL THEN 1 END) / COUNT(*), 1) as power_pct,
            ROUND(100.0 * COUNT(CASE WHEN fuel IS NOT NULL THEN 1 END) / COUNT(*), 1) as fuel_pct,
            ROUND(100.0 * COUNT(CASE WHEN price IS NOT NULL THEN 1 END) / COUNT(*), 1) as price_pct
        FROM offers
    """))
    row = result.fetchone()
    print(f"Total offers:     {row[0]:,}")
    print(f"Unique models:    {row[1]:,}")
    print(f"Year filled:      {row[2]}%")
    print(f"Mileage filled:   {row[3]}%")
    print(f"Power filled:     {row[4]}%")
    print(f"Fuel filled:      {row[5]}%")
    print(f"Price filled:     {row[6]}%")

    # 2. Fuel field analysis (lowest accuracy)
    print("\n2. FUEL FIELD VALUES (needs cleaning):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT fuel, COUNT(*) as count,
               ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM offers WHERE fuel IS NOT NULL), 1) as pct
        FROM offers
        WHERE fuel IS NOT NULL
        GROUP BY fuel
        ORDER BY count DESC
        LIMIT 20
    """))
    print(f"{'Fuel Type':<30} {'Count':>10} {'%':>8}")
    print("-" * 80)
    for row in result:
        print(f"{row[0]:<30} {row[1]:>10,} {row[2]:>7}%")

    # 3. Year range check (outliers)
    print("\n3. YEAR RANGE (outliers check):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT
            MIN(year_manufacture) as min_year,
            MAX(year_manufacture) as max_year,
            AVG(year_manufacture) as avg_year,
            COUNT(CASE WHEN year_manufacture < 1950 THEN 1 END) as before_1950,
            COUNT(CASE WHEN year_manufacture > 2026 THEN 1 END) as future_year
        FROM offers
        WHERE year_manufacture IS NOT NULL
    """))
    row = result.fetchone()
    print(f"Min year:         {row[0]}")
    print(f"Max year:         {row[1]}")
    print(f"Avg year:         {row[2]:.1f}")
    print(f"Before 1950:      {row[3]} (likely errors)")
    print(f"Future (>2026):   {row[4]} (likely errors)")

    # 4. Price outliers
    print("\n4. PRICE RANGE (outliers check):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            COUNT(CASE WHEN price < 1000 THEN 1 END) as very_cheap,
            COUNT(CASE WHEN price > 10000000 THEN 1 END) as very_expensive
        FROM offers
        WHERE price IS NOT NULL
    """))
    row = result.fetchone()
    print(f"Min price:        {row[0]:,} Kč")
    print(f"Max price:        {row[1]:,} Kč")
    print(f"Avg price:        {row[2]:,.0f} Kč")
    print(f"< 1,000 Kč:       {row[3]} (likely errors)")
    print(f"> 10M Kč:         {row[4]} (likely errors)")

    # 5. Mileage outliers
    print("\n5. MILEAGE RANGE (outliers check):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT
            MIN(mileage) as min_mileage,
            MAX(mileage) as max_mileage,
            AVG(mileage) as avg_mileage,
            COUNT(CASE WHEN mileage = 0 THEN 1 END) as zero_mileage,
            COUNT(CASE WHEN mileage > 1000000 THEN 1 END) as over_1M
        FROM offers
        WHERE mileage IS NOT NULL
    """))
    row = result.fetchone()
    print(f"Min mileage:      {row[0]:,} km")
    print(f"Max mileage:      {row[1]:,} km")
    print(f"Avg mileage:      {row[2]:,.0f} km")
    print(f"Zero mileage:     {row[3]} (new cars)")
    print(f"> 1M km:          {row[4]} (likely errors)")

    # 6. Top 10 models
    print("\n6. TOP 10 MODELS:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT m.name, COUNT(*) as count
        FROM offers o
        JOIN models m ON o.model_id = m.id
        GROUP BY m.name
        ORDER BY count DESC
        LIMIT 10
    """))
    print(f"{'Model':<30} {'Count':>10}")
    print("-" * 80)
    for row in result:
        print(f"{row[0]:<30} {row[1]:>10,}")

    # 7. Sample of problematic records
    print("\n7. SAMPLE RECORDS WITH ISSUES:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT o.id, m.name, o.year_manufacture, o.mileage, o.power, o.fuel, o.price, o.url
        FROM offers o
        JOIN models m ON o.model_id = m.id
        WHERE o.year_manufacture < 1950
           OR o.year_manufacture > 2026
           OR o.price < 1000
           OR o.mileage > 1000000
        LIMIT 10
    """))
    print(f"{'ID':<8} {'Model':<20} {'Year':<6} {'Mileage':<12} {'Power':<6} {'Fuel':<10} {'Price':<12}")
    print("-" * 80)
    for row in result:
        print(f"{row[0]:<8} {row[1]:<20} {str(row[2]):<6} {str(row[3]):<12} {str(row[4]):<6} {str(row[5]):<10} {str(row[6]):<12}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print("1. Normalize fuel values (many variants detected)")
print("2. Remove/fix outlier years (< 1950 or > 2026)")
print("3. Remove/fix outlier prices (< 1,000 Kč or > 10M Kč)")
print("4. Remove/fix outlier mileage (> 1M km)")
print("5. Review records with missing critical fields")
print("=" * 80)
