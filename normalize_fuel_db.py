#!/usr/bin/env python3
"""
Normalize Fuel Values in Database
----------------------------------
Cleans up old fuel data to use consistent normalized values.

Usage:
    python3 normalize_fuel_db.py --dry-run  # Preview changes
    python3 normalize_fuel_db.py            # Apply changes

This script:
  - Finds all unique fuel values in DB
  - Normalizes them using DataNormalizer
  - Updates database with normalized values
  - Shows before/after statistics
"""

import sys
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ml.production_extractor import DataNormalizer
from webapp.config import get_config

# Load configuration
config = get_config()

def get_db_connection():
    """Create database connection"""
    connection_string = (
        f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
        f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}"
    )
    engine = create_engine(connection_string)
    return engine

def analyze_fuel_values(engine):
    """Get current fuel value distribution"""
    print("=" * 70)
    print("🔍 ANALYZING CURRENT FUEL VALUES")
    print("=" * 70)

    query = text("""
        SELECT fuel, COUNT(*) as count
        FROM offers
        WHERE fuel IS NOT NULL
        GROUP BY fuel
        ORDER BY count DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

    print(f"\nFound {len(rows)} distinct fuel values:\n")

    total = sum(row[1] for row in rows)
    normalizer = DataNormalizer()

    # Group by normalized value
    normalized_groups = {}
    for fuel, count in rows:
        normalized = normalizer.normalize_fuel(fuel)
        if normalized not in normalized_groups:
            normalized_groups[normalized] = []
        normalized_groups[normalized].append((fuel, count))

    # Show current distribution
    for fuel, count in rows:
        percentage = (count / total) * 100
        normalized = normalizer.normalize_fuel(fuel)

        if fuel == normalized:
            marker = "✅"  # Already normalized
        else:
            marker = f"→ {normalized}"  # Will be changed

        print(f"  {fuel:20s}: {count:6d} ({percentage:5.1f}%)  {marker}")

    print(f"\n{'─' * 70}")
    print(f"Total offers with fuel: {total:,}")
    print(f"{'─' * 70}\n")

    return normalized_groups, total

def preview_changes(normalized_groups):
    """Show what will change"""
    print("=" * 70)
    print("📋 PREVIEW OF CHANGES")
    print("=" * 70)

    changes_needed = False

    for normalized_value, variants in sorted(normalized_groups.items()):
        # Count variants that need changing
        to_change = [(fuel, count) for fuel, count in variants if fuel != normalized_value]
        already_normalized = [(fuel, count) for fuel, count in variants if fuel == normalized_value]

        if to_change:
            changes_needed = True
            print(f"\n{normalized_value}:")

            if already_normalized:
                total_normalized = sum(count for _, count in already_normalized)
                print(f"  ✅ Already normalized: {total_normalized:,} offers")

            print(f"  ⚠️  Will be changed:")
            for fuel, count in to_change:
                print(f"     '{fuel}' → '{normalized_value}' ({count:,} offers)")

    if not changes_needed:
        print("\n✅ All fuel values are already normalized!")
        print("   No changes needed.")

    print(f"\n{'=' * 70}\n")
    return changes_needed

def normalize_database(engine, dry_run=True):
    """Normalize fuel values in database"""
    print("=" * 70)
    if dry_run:
        print("🔍 DRY RUN MODE (no changes will be made)")
    else:
        print("✅ APPLYING CHANGES")
    print("=" * 70)

    normalizer = DataNormalizer()

    # Get all distinct fuel values
    query = text("SELECT DISTINCT fuel FROM offers WHERE fuel IS NOT NULL")

    with engine.connect() as conn:
        result = conn.execute(query)
        fuel_values = [row[0] for row in result.fetchall()]

    # Build normalization mapping
    updates = {}
    for fuel in fuel_values:
        normalized = normalizer.normalize_fuel(fuel)
        if fuel != normalized:
            updates[fuel] = normalized

    if not updates:
        print("\n✅ No changes needed! All values already normalized.")
        return

    print(f"\nWill normalize {len(updates)} distinct values:\n")

    total_updated = 0

    for old_value, new_value in sorted(updates.items()):
        # Count how many rows will be affected
        count_query = text("SELECT COUNT(*) FROM offers WHERE fuel = :fuel")

        with engine.connect() as conn:
            result = conn.execute(count_query, {"fuel": old_value})
            count = result.scalar()

        print(f"  '{old_value}' → '{new_value}' ({count:,} offers)")

        if not dry_run:
            # Apply update
            update_query = text("UPDATE offers SET fuel = :new_value WHERE fuel = :old_value")

            with engine.begin() as conn:
                result = conn.execute(update_query, {"new_value": new_value, "old_value": old_value})
                total_updated += result.rowcount

    if dry_run:
        print(f"\n⚠️  DRY RUN: Would update {sum(updates.values())} offers")
        print("   Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Updated {total_updated:,} offers")
        print("   Database normalized!")

    print(f"\n{'=' * 70}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Normalize fuel values in database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (dry run):
  python3 normalize_fuel_db.py --dry-run

  # Apply changes:
  python3 normalize_fuel_db.py

  # Check result:
  python3 normalize_fuel_db.py --analyze-only

Normalized values:
  diesel  ← nafta, Diesel, TDi, td, motorová nafta
  benzín  ← benzin, Benzín, gas, gasoline
  lpg     ← LPG, plyn
  elektro ← elektro, electric, EV
        """
    )

    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--analyze-only', action='store_true', help='Only show current distribution')

    args = parser.parse_args()

    # Connect to database
    try:
        engine = get_db_connection()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Analyze current state
    normalized_groups, total = analyze_fuel_values(engine)

    if args.analyze_only:
        print("✅ Analysis complete!")
        return

    # Preview changes
    changes_needed = preview_changes(normalized_groups)

    if not changes_needed:
        print("✅ No normalization needed!")
        return

    # Normalize (dry run or real)
    normalize_database(engine, dry_run=args.dry_run or args.analyze_only)

    if args.dry_run:
        print("\n💡 To apply changes, run:")
        print("   python3 normalize_fuel_db.py")
    else:
        print("\n✅ Normalization complete!")
        print("\n📊 Re-analyzing to verify...")
        analyze_fuel_values(engine)

if __name__ == '__main__':
    main()
