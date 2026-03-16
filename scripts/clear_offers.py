#!/usr/bin/env python3
"""
Clear offers table (DELETE or TRUNCATE)

Usage:
  python3 scripts/clear_offers.py           # Shows stats, asks for confirmation
  python3 scripts/clear_offers.py --confirm # Skips confirmation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config

config = get_config()

def clear_offers(confirm=False):
    """Clear all offers from database"""

    # Connect
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("CLEAR OFFERS TABLE")
    print("=" * 70)

    # Show current stats
    cursor.execute("SELECT COUNT(*) FROM offers")
    count = cursor.fetchone()[0]

    print(f"\n📊 Current offers: {count}")

    if count == 0:
        print("✅ Table is already empty!")
        cursor.close()
        conn.close()
        return

    # Ask for confirmation
    if not confirm:
        print(f"\n⚠️  WARNING: This will DELETE all {count} offers!")
        print("   Brands and Models will NOT be deleted (CASCADE protection)")
        response = input("\n   Type 'yes' to confirm: ")

        if response.lower() != 'yes':
            print("❌ Cancelled")
            cursor.close()
            conn.close()
            return

    # Clear table
    print("\n🗑️  Deleting all offers...")

    try:
        # Use TRUNCATE (faster, resets AUTO_INCREMENT)
        cursor.execute("TRUNCATE TABLE offers")
        conn.commit()

        print(f"✅ Deleted {count} offers!")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM offers")
        new_count = cursor.fetchone()[0]
        print(f"📊 New count: {new_count}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTrying DELETE instead of TRUNCATE...")

        try:
            cursor.execute("DELETE FROM offers")
            conn.commit()
            print(f"✅ Deleted {count} offers using DELETE!")

            # Reset AUTO_INCREMENT
            cursor.execute("ALTER TABLE offers AUTO_INCREMENT = 1")
            conn.commit()
            print("✅ AUTO_INCREMENT reset to 1")

        except Exception as e2:
            print(f"❌ DELETE also failed: {e2}")
            conn.rollback()

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("NEXT STEP:")
    print("  python3 pipeline/runner.py")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clear offers table')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    clear_offers(confirm=args.confirm)
