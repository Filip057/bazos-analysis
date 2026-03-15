#!/usr/bin/env python3
"""
Data Quality Audit - Measure completeness and accuracy
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
from collections import Counter

config = get_config()

def audit():
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("DATA QUALITY AUDIT REPORT")
    print("=" * 70)

    # Total records
    cursor.execute("SELECT COUNT(*) FROM offers")
    total = cursor.fetchone()[0]
    print(f"\n📊 Total Offers: {total:,}")

    # Completeness check
    print("\n" + "=" * 70)
    print("COMPLETENESS (% of non-NULL values)")
    print("=" * 70)

    fields = ['year_manufacture', 'mileage', 'power', 'fuel', 'price']
    for field in fields:
        cursor.execute(f"SELECT COUNT(*) FROM offers WHERE {field} IS NOT NULL")
        count = cursor.fetchone()[0]
        pct = (count / total * 100) if total > 0 else 0
        status = "✅" if pct >= 90 else "⚠️" if pct >= 70 else "❌"
        print(f"  {status} {field:20s}: {count:5d}/{total:5d} ({pct:5.1f}%)")

    # Fuel normalization issues
    print("\n" + "=" * 70)
    print("FUEL TYPE NORMALIZATION ISSUES")
    print("=" * 70)

    cursor.execute("SELECT fuel, COUNT(*) as count FROM offers WHERE fuel IS NOT NULL GROUP BY fuel ORDER BY count DESC")
    fuel_types = cursor.fetchall()

    if fuel_types:
        print(f"\n  Found {len(fuel_types)} different fuel type values:")
        for fuel, count in fuel_types:
            print(f"    {fuel:30s}: {count:4d} ({count/total*100:4.1f}%)")
    else:
        print("  No fuel data found")

    # Suspicious values - fuel field containing numbers (likely mileage)
    print("\n" + "=" * 70)
    print("SUSPICIOUS VALUES (fuel contains numbers)")
    print("=" * 70)

    cursor.execute("""
        SELECT id, fuel, mileage, url
        FROM offers
        WHERE fuel REGEXP '[0-9]'
        LIMIT 10
    """)
    suspicious = cursor.fetchall()

    if suspicious:
        print(f"\n  ⚠️  Found {len(suspicious)} offers with numbers in fuel field:")
        for offer_id, fuel, mileage, url in suspicious[:5]:
            print(f"    ID {offer_id}: fuel='{fuel}', mileage={mileage}")
            print(f"      URL: {url}")
    else:
        print("  ✅ No suspicious values found")

    # Missing critical data
    print("\n" + "=" * 70)
    print("MISSING CRITICAL DATA")
    print("=" * 70)

    cursor.execute("""
        SELECT COUNT(*)
        FROM offers
        WHERE year_manufacture IS NULL
           OR mileage IS NULL
           OR price IS NULL
    """)
    missing_critical = cursor.fetchone()[0]
    pct = (missing_critical / total * 100) if total > 0 else 0
    print(f"  Offers missing year/mileage/price: {missing_critical:,} ({pct:.1f}%)")

    # Summary
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    recommendations = []

    # Fuel normalization
    if len(fuel_types) > 5:
        recommendations.append("1. NORMALIZE fuel types (found {0} variants, should be ~4)".format(len(fuel_types)))

    # Suspicious values
    if suspicious:
        recommendations.append("2. FIX suspicious fuel values (numbers in text field)")

    # Completeness
    cursor.execute("SELECT COUNT(*) FROM offers WHERE fuel IS NULL")
    null_fuel = cursor.fetchone()[0]
    if null_fuel / total > 0.3:
        recommendations.append("3. IMPROVE fuel extraction ({}% missing)".format(int(null_fuel/total*100)))

    if recommendations:
        for rec in recommendations:
            print(f"  ⚠️  {rec}")
    else:
        print("  ✅ Data quality looks good!")

    print("\n" + "=" * 70)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    audit()
