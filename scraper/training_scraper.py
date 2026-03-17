#!/usr/bin/env python3
"""
Simple Training Data Scraper
-----------------------------
Lightweight wrapper around data_scrap.py for generating unlabeled training data.

NO REFACTORING of existing code - just a simple facade!

Usage:
    python3 -m scraper.training_scraper --brand skoda --max-offers 500 --output unlabeled_500.json
"""

import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
import json
import argparse
import logging
from typing import List, Dict, Optional
from tqdm.asyncio import tqdm as async_tqdm
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base URL
CAR_URL = 'https://auto.bazos.cz/'

# Connection settings (same as data_scrap.py)
MAX_CONCURRENT_REQUESTS = 20
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1
REQUEST_TIMEOUT = 30


async def fetch_url(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Optional[str]:
    """Fetch URL with retry logic (borrowed from data_scrap.py)"""
    for attempt in range(RETRY_ATTEMPTS):
        async with semaphore:
            try:
                async with session.get(url, timeout=ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
            except Exception as e:
                logger.warning(f"Error fetching {url}: {e} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")

            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return None


async def get_listing_urls(brand: str, max_offers: int, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[str]:
    """Get list of car listing URLs from category pages

    Bazos.cz URL pattern:
      - https://auto.bazos.cz/skoda/      (offers 0-19)
      - https://auto.bazos.cz/skoda/20/   (offers 20-39)
      - https://auto.bazos.cz/skoda/40/   (offers 40-59)
      - etc. (increment by 20 each page)
    """
    logger.info(f"📄 Fetching listing URLs for brand: {brand} (target: {max_offers} offers)")

    urls = []
    base_url = f"{CAR_URL}{brand}/"

    # Calculate how many pages to fetch (20 offers per page)
    # Add 20% buffer for duplicates/errors
    max_offset = int(max_offers * 1.2)
    page_count = 0

    # Iterate through offsets: 0, 20, 40, 60, ...
    for offset in range(0, max_offset, 20):
        page_count += 1
        page_url = f"{base_url}{offset}/" if offset > 0 else base_url

        html = await fetch_url(page_url, session, semaphore)
        if not html:
            logger.warning(f"Failed to fetch page at offset {offset}")
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # Find car listing links (same pattern as data_scrap.py)
        links = soup.find_all('a', href=True)
        page_urls = []
        for link in links:
            href = link.get('href', '')
            # Match pattern: /inzerat/123456789/...
            if '/inzerat/' in href and href.startswith('http'):
                if href not in urls:  # Deduplicate
                    urls.append(href)
                    page_urls.append(href)

        logger.info(f"  Page {page_count} (offset {offset}): +{len(page_urls)} URLs (total: {len(urls)})")

        # Stop if we have enough URLs
        if len(urls) >= max_offers:
            logger.info(f"  Reached target ({len(urls)} >= {max_offers}), stopping")
            break

        # Small delay between pages
        await asyncio.sleep(0.5)

    logger.info(f"✅ Found {len(urls)} unique listing URLs")
    return urls


async def scrape_listing(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Optional[Dict]:
    """Scrape single car listing - extract RAW text only (no ML extraction!)"""
    html = await fetch_url(url, session, semaphore)
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Extract header (title)
        header_elem = soup.find('h1', class_='nadpisdetail')
        header = header_elem.get_text(strip=True) if header_elem else ""

        # Extract description
        desc_elem = soup.find('div', class_='popisdetail')
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Combine into single text (same as training format)
        if header or description:
            # Clean up text
            text = f"{header}. {description}" if header and description else (header or description)

            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            return {
                'text': text,
                'url': url,
                'header': header,
                'description': description
            }

    except Exception as e:
        logger.warning(f"Error parsing {url}: {e}")

    return None


async def scrape_training_data(brand: str, max_offers: int, output_file: str):
    """Main scraping function - get unlabeled training data"""

    logger.info("=" * 70)
    logger.info("🤖 TRAINING DATA SCRAPER")
    logger.info("=" * 70)
    logger.info(f"Brand: {brand}")
    logger.info(f"Target: {max_offers} offers")
    logger.info(f"Output: {output_file}")
    logger.info("=" * 70)

    # Setup async session
    connector = TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    timeout = ClientTimeout(total=REQUEST_TIMEOUT)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Phase 1: Get listing URLs (will fetch up to max_offers)
        urls = await get_listing_urls(brand, max_offers, session, semaphore)

        # Limit to max_offers
        urls = urls[:max_offers]
        logger.info(f"📊 Will scrape {len(urls)} listings")

        # Phase 2: Scrape each listing
        logger.info("🔍 Scraping listing details...")

        tasks = [scrape_listing(url, session, semaphore) for url in urls]
        results = []

        # Use tqdm for progress bar
        for coro in async_tqdm.as_completed(tasks, total=len(tasks), desc="Scraping"):
            result = await coro
            if result:
                results.append(result)

        logger.info(f"✅ Successfully scraped {len(results)}/{len(urls)} listings")

        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Saved to {output_file}")
        logger.info("=" * 70)
        logger.info("🎉 DONE!")
        logger.info("=" * 70)
        logger.info(f"Next steps:")
        logger.info(f"  1. Check data: head -50 {output_file}")
        logger.info(f"  2. Copy prompt from: gpt_entity_extraction_prompt_v2.md")
        logger.info(f"  3. Send to GPT-4 for labeling")
        logger.info(f"  4. Train model with labeled data")

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Scrape training data from Bazos.cz (unlabeled, for GPT labeling)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape 500 Škoda offers
  python3 -m scraper.training_scraper --brand skoda --max-offers 500 --output unlabeled_500.json

  # Scrape 200 VW offers
  python3 -m scraper.training_scraper --brand volkswagen --max-offers 200 --output unlabeled_vw.json

  # Scrape all brands (mixed)
  python3 -m scraper.training_scraper --brand auto --max-offers 500 --output unlabeled_mixed.json

Available brands:
  alfa, audi, bmw, citroen, dacia, fiat, ford, honda, hyundai,
  chevrolet, kia, mazda, mercedes, mitsubishi, nissan, opel,
  peugeot, renault, seat, suzuki, skoda, toyota, volkswagen, volvo

  Or use 'auto' for all brands (mixed)

Output format:
  [
    {
      "text": "Škoda Fabia 1.2 HTP 47kW 2003 180tis km...",
      "url": "https://auto.bazos.cz/inzerat/123456789/...",
      "header": "Škoda Fabia 1.2 HTP 47kW 2003",
      "description": "180tis km serviska najeto 238500..."
    },
    ...
  ]

This is RAW unlabeled data ready for GPT/Claude labeling!
        """
    )

    parser.add_argument('--brand', required=True, help='Brand to scrape (e.g., skoda, vw, auto)')
    parser.add_argument('--max-offers', type=int, default=500, help='Maximum offers to scrape (default: 500)')
    parser.add_argument('--output', default='unlabeled_training.json', help='Output JSON file (default: unlabeled_training.json)')

    args = parser.parse_args()

    # Run async scraper
    asyncio.run(scrape_training_data(args.brand, args.max_offers, args.output))


if __name__ == '__main__':
    main()
