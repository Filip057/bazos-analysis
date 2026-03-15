#!/usr/bin/env python3
"""
ASYNC Re-extraction: Scrape + Extract all offers in parallel

This script uses async/await for FAST scraping:
- Scrapes 20 URLs concurrently
- Expected runtime: ~3-5 minutes (vs. 13 min sync)

Based on existing async scraper (scraper/data_scrap.py)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from bs4 import BeautifulSoup
import pymysql
from webapp.config import get_config
from ml.production_extractor import ProductionExtractor
import time
from tqdm.asyncio import tqdm as async_tqdm

config = get_config()

# Connection pooling (from existing scraper)
MAX_CONCURRENT_REQUESTS = 20
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1
REQUEST_TIMEOUT = 30

async def fetch_data(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
    """Fetch data from URL with retry logic and rate limiting (from scraper/data_scrap.py)"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with semaphore:
                async with session.get(url, timeout=ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                    response.raise_for_status()
                    return await response.text()
        except asyncio.TimeoutError:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except aiohttp.ClientError:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except Exception:
            break
    return None

async def scrape_offer_detail(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
    """Scrape title and description from Bazos offer (async)"""
    data = await fetch_data(url, session, semaphore)

    if not data:
        return None, None

    try:
        soup = BeautifulSoup(data, 'html.parser')

        # Extract title
        title_elem = soup.find('h1', class_='nadpisdetail')
        title = title_elem.text.strip() if title_elem else ''

        # Extract description
        desc_elem = soup.find('div', class_='popisdetail')
        description = desc_elem.text.strip() if desc_elem else ''

        return title, description
    except Exception:
        return None, None

async def scrape_and_extract_offer(offer_id: int, url: str, session: aiohttp.ClientSession,
                                   semaphore: asyncio.Semaphore, extractor: ProductionExtractor):
    """Scrape offer and extract data (single offer)"""
    # Scrape
    title, description = await scrape_offer_detail(url, session, semaphore)

    if title is None:
        return {
            'id': offer_id,
            'success': False,
            'error': 'scrape_failed'
        }

    # Extract
    full_text = f"{title}\n{description}" if description else title
    result = extractor.extract(full_text, car_id=str(offer_id))

    return {
        'id': offer_id,
        'success': True,
        'year': result['year'],
        'mileage': result['mileage'],
        'power': result['power'],
        'fuel': result['fuel']
    }

async def process_batch(offers_batch, session: aiohttp.ClientSession,
                       semaphore: asyncio.Semaphore, extractor: ProductionExtractor):
    """Process a batch of offers in parallel"""
    tasks = [
        scrape_and_extract_offer(offer_id, url, session, semaphore, extractor)
        for offer_id, url in offers_batch
    ]
    return await asyncio.gather(*tasks)

def update_database(results, conn):
    """Update database with extraction results"""
    cursor = conn.cursor()

    stats = {
        'total': 0,
        'year_improved': 0,
        'mileage_improved': 0,
        'power_improved': 0,
        'fuel_improved': 0,
        'year_kept': 0,
        'mileage_kept': 0,
        'power_kept': 0,
        'fuel_kept': 0,
        'scrape_failed': 0
    }

    for result in results:
        if not result['success']:
            stats['scrape_failed'] += 1
            stats['total'] += 1
            continue

        offer_id = result['id']

        # Get current values
        cursor.execute("""
            SELECT year_manufacture, mileage, power, fuel
            FROM offers
            WHERE id = %s
        """, (offer_id,))
        current = cursor.fetchone()

        if not current:
            continue

        old_year, old_mileage, old_power, old_fuel = current

        new_year = result['year']
        new_mileage = result['mileage']
        new_power = result['power']
        new_fuel = result['fuel']

        # Keep existing values if new extraction returns None
        final_year = new_year if new_year is not None else old_year
        final_mileage = new_mileage if new_mileage is not None else old_mileage
        final_power = new_power if new_power is not None else old_power
        final_fuel = new_fuel if new_fuel is not None else old_fuel

        # Update database
        cursor.execute("""
            UPDATE offers
            SET year_manufacture = %s,
                mileage = %s,
                power = %s,
                fuel = %s
            WHERE id = %s
        """, (final_year, final_mileage, final_power, final_fuel, offer_id))

        # Track improvements
        stats['total'] += 1
        if old_year is None and new_year is not None:
            stats['year_improved'] += 1
        if old_mileage is None and new_mileage is not None:
            stats['mileage_improved'] += 1
        if old_power is None and new_power is not None:
            stats['power_improved'] += 1
        if old_fuel is None and new_fuel is not None:
            stats['fuel_improved'] += 1

        # Track kept values
        if old_year is not None and new_year is None:
            stats['year_kept'] += 1
        if old_mileage is not None and new_mileage is None:
            stats['mileage_kept'] += 1
        if old_power is not None and new_power is None:
            stats['power_kept'] += 1
        if old_fuel is not None and new_fuel is None:
            stats['fuel_kept'] += 1

    conn.commit()
    return stats

async def main():
    """Main async function"""
    print("=" * 70)
    print("ASYNC RE-EXTRACTION (FAST - 20 concurrent requests)")
    print("=" * 70)

    # Connect to database
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM offers WHERE url IS NOT NULL")
    total_offers = cursor.fetchone()[0]
    print(f"\nTotal offers to re-extract: {total_offers}")

    # Fetch all offers
    print("\n📥 Fetching offer URLs from database...")
    cursor.execute("""
        SELECT id, url
        FROM offers
        WHERE url IS NOT NULL
    """)
    offers = cursor.fetchall()
    print(f"Found {len(offers)} offers with URLs")

    # Initialize extractor
    print("🔧 Initializing improved extractor...")
    extractor = ProductionExtractor()

    print(f"\n🚀 Starting ASYNC scraping + extraction...")
    print(f"   Concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"   ETA: ~{len(offers)*0.15/60:.0f} minutes (vs. ~13 min sync)\n")

    start_time = time.time()

    # Create async session with connection pooling
    connector = TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=MAX_CONCURRENT_REQUESTS)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    all_results = []

    async with aiohttp.ClientSession(connector=connector) as session:
        # Process in batches with progress bar
        batch_size = 100
        for i in range(0, len(offers), batch_size):
            batch = offers[i:i+batch_size]

            # Process batch
            batch_results = await process_batch(batch, session, semaphore, extractor)
            all_results.extend(batch_results)

            # Update progress
            print(f"  [{i+len(batch)}/{len(offers)}] processed...")

    elapsed = time.time() - start_time

    # Update database
    print("\n💾 Updating database...")
    stats = update_database(all_results, conn)

    # Print results
    print(f"\n{'='*70}")
    print("RE-EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"  Total processed:     {stats['total']}")
    print(f"  Scrape failed:       {stats['scrape_failed']} (URL not accessible)")
    print(f"\n  IMPROVEMENTS (NULL → value):")
    print(f"    Year improved:       {stats['year_improved']}")
    print(f"    Mileage improved:    {stats['mileage_improved']}")
    print(f"    Power improved:      {stats['power_improved']}")
    print(f"    Fuel improved:       {stats['fuel_improved']}")
    print(f"\n  REGRESSION PREVENTION (kept existing values):")
    print(f"    Year kept:           {stats['year_kept']} (extraction failed, kept old value)")
    print(f"    Mileage kept:        {stats['mileage_kept']}")
    print(f"    Power kept:          {stats['power_kept']}")
    print(f"    Fuel kept:           {stats['fuel_kept']}")
    print(f"\n  Time taken:          {elapsed:.1f}s ({elapsed/60:.1f} min, {len(offers)/elapsed:.1f} offers/sec)")
    print(f"{'='*70}\n")

    # Show new completeness
    print("📊 NEW COMPLETENESS METRICS:\n")

    for field in ['year_manufacture', 'mileage', 'power', 'fuel']:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM offers
            WHERE {field} IS NOT NULL
        """)
        non_null = cursor.fetchone()[0]
        completeness = (non_null / total_offers) * 100

        status = "✅" if completeness >= 80 else "⚠️" if completeness >= 70 else "❌"
        print(f"  {status} {field:20s}: {non_null:4d}/{total_offers} ({completeness:5.1f}%)")

    cursor.close()
    conn.close()

    print(f"\n{'='*70}")
    print("NEXT STEP: Run data quality audit to verify improvements")
    print("  python3 scripts/data_quality_audit.py")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(main())
