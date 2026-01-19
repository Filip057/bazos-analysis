"""
Scrape Real Data for ML Training
=================================

This script scrapes real car descriptions from Bazos and prepares them
for labeling. Much better than synthetic examples!

Features:
- Scrapes real descriptions (not from database)
- Shows what current regex extracts
- Saves in format ready for labeling
- Limits to specified number of cars

Usage:
    python scrape_for_training.py --limit 100 --brand chevrolet
"""

import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
import argparse
import logging
from typing import List, Dict, Tuple
from pathlib import Path
import json

# Import your existing scraper functions
from scraper.data_scrap import (
    fetch_data,
    get_all_pages_for_brands,
    get_urls_for_details,
    get_descriptions_headings_price,
    get_mileage,
    get_year_manufacture,
    get_power,
    get_model,
    MAX_CONCURRENT_REQUESTS
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingDataScraper:
    """Scrapes real car data for ML training"""

    def __init__(self):
        self.scraped_data = []

    async def scrape_for_training(self, brand_urls: List[Tuple[str, str]],
                                  limit: int = 100) -> List[Dict]:
        """
        Scrape real car descriptions for training.

        Args:
            brand_urls: List of (brand, url) tuples
            limit: Maximum number of cars to scrape

        Returns:
            List of car data dictionaries
        """
        logger.info(f"Starting training data collection...")
        logger.info(f"Target: {limit} car descriptions")

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        # Configure connection pooling
        connector = TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=10)
        timeout = ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

            # Step 1: Get pages for brands
            logger.info(f"Fetching pages for {len(brand_urls)} brand(s)...")
            brand_pages = await get_all_pages_for_brands(brand_urls, session, semaphore)

            # Step 2: Get detail URLs (but limit them!)
            logger.info("Fetching detail URLs...")
            all_detail_urls = await get_urls_for_details(brand_pages, session, semaphore)

            # Limit to requested number
            detail_urls = all_detail_urls[:limit]
            logger.info(f"Will scrape {len(detail_urls)} car listings")

            # Step 3: Get descriptions, headings, prices
            logger.info("Scraping car details...")
            scraped_cars = await get_descriptions_headings_price(detail_urls, session, semaphore)

            # Step 4: Process and analyze each car
            training_data = []
            for i, (brand, url, description, heading, price) in enumerate(scraped_cars, 1):

                # Try current regex extraction
                regex_mileage = get_mileage(description) or get_mileage(heading)
                regex_year = get_year_manufacture(description) or get_year_manufacture(heading)
                regex_power = get_power(description) or get_power(heading)
                regex_model = get_model(brand, heading)

                # Create full text (what you'll label)
                full_text = f"{heading}. {description}"

                # Create training data entry
                entry = {
                    'id': i,
                    'text': full_text,
                    'heading': heading,
                    'description': description,
                    'brand': brand,
                    'url': url,
                    'price': price,
                    # What regex found (for comparison)
                    'regex_extracted': {
                        'mileage': regex_mileage,
                        'year': regex_year,
                        'power': regex_power,
                        'model': regex_model
                    }
                }

                training_data.append(entry)

                # Log progress
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(scraped_cars)} cars")

            logger.info(f"\n✓ Scraped {len(training_data)} cars successfully!")
            return training_data

    def save_for_labeling(self, data: List[Dict], output_file: str):
        """
        Save scraped data in format ready for labeling.

        Creates:
        1. descriptions.txt - One text per line for label_data.py
        2. scraped_data.json - Full data with regex results for analysis
        """
        # Save full data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ Saved full data to {output_file}")

        # Save just texts for labeling
        text_file = output_file.replace('.json', '_texts.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            for entry in data:
                f.write(entry['text'] + '\n')

        logger.info(f"✓ Saved texts for labeling to {text_file}")

        return text_file

    def analyze_regex_performance(self, data: List[Dict]):
        """
        Analyze how well current regex performs on real data.
        This shows you where ML will help most!
        """
        total = len(data)
        mileage_found = sum(1 for d in data if d['regex_extracted']['mileage'] is not None)
        year_found = sum(1 for d in data if d['regex_extracted']['year'] is not None)
        power_found = sum(1 for d in data if d['regex_extracted']['power'] is not None)
        all_found = sum(1 for d in data if all([
            d['regex_extracted']['mileage'],
            d['regex_extracted']['year'],
            d['regex_extracted']['power']
        ]))

        logger.info("\n" + "=" * 60)
        logger.info("Current Regex Performance Analysis")
        logger.info("=" * 60)
        logger.info(f"Total cars scraped:        {total}")
        logger.info(f"Mileage found:             {mileage_found} ({mileage_found/total*100:.1f}%)")
        logger.info(f"Year found:                {year_found} ({year_found/total*100:.1f}%)")
        logger.info(f"Power found:               {power_found} ({power_found/total*100:.1f}%)")
        logger.info(f"All fields found:          {all_found} ({all_found/total*100:.1f}%)")
        logger.info(f"\nMissed fields:             {total - all_found} ({(total-all_found)/total*100:.1f}%)")
        logger.info("=" * 60)

        # Show examples of failures
        failures = [d for d in data if not all([
            d['regex_extracted']['mileage'],
            d['regex_extracted']['year'],
            d['regex_extracted']['power']
        ])]

        if failures:
            logger.info(f"\n📋 Sample failures (these are good for training!):\n")
            for i, fail in enumerate(failures[:5], 1):
                logger.info(f"{i}. Missing fields:")
                if not fail['regex_extracted']['mileage']:
                    logger.info(f"   ❌ Mileage")
                if not fail['regex_extracted']['year']:
                    logger.info(f"   ❌ Year")
                if not fail['regex_extracted']['power']:
                    logger.info(f"   ❌ Power")
                logger.info(f"   Text: {fail['text'][:100]}...")
                logger.info("")

        logger.info(f"\n💡 ML can potentially improve by {(total-all_found)/total*100:.1f}%!\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape real car data for ML training"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of cars to scrape (default: 100)"
    )
    parser.add_argument(
        "--brand",
        default="chevrolet",
        help="Brand to scrape (default: chevrolet)"
    )
    parser.add_argument(
        "--output",
        default="training_data_scraped.json",
        help="Output JSON file (default: training_data_scraped.json)"
    )
    parser.add_argument(
        "--multiple-brands",
        nargs="+",
        help="Scrape multiple brands (e.g., --multiple-brands chevrolet ford bmw)"
    )

    args = parser.parse_args()

    # Determine which brands to scrape
    if args.multiple_brands:
        brand_urls = [(brand, f'https://auto.bazos.cz/{brand}/') for brand in args.multiple_brands]
    else:
        brand_urls = [(args.brand, f'https://auto.bazos.cz/{args.brand}/')]

    logger.info(f"\n{'='*60}")
    logger.info(f"Scraping Training Data from Bazos.cz")
    logger.info(f"{'='*60}")
    logger.info(f"Brands: {', '.join([b for b, _ in brand_urls])}")
    logger.info(f"Limit: {args.limit} cars")
    logger.info(f"{'='*60}\n")

    # Create scraper
    scraper = TrainingDataScraper()

    # Scrape the data
    data = await scraper.scrape_for_training(brand_urls, limit=args.limit)

    if not data:
        logger.error("❌ No data scraped! Check your internet connection.")
        return

    # Analyze regex performance
    scraper.analyze_regex_performance(data)

    # Save for labeling
    text_file = scraper.save_for_labeling(data, args.output)

    # Print next steps
    logger.info("\n" + "="*60)
    logger.info("✅ Data collection complete!")
    logger.info("="*60)
    logger.info(f"\n📁 Files created:")
    logger.info(f"   1. {args.output} - Full scraped data with regex results")
    logger.info(f"   2. {text_file} - Texts ready for labeling")
    logger.info(f"\n🎯 Next steps:")
    logger.info(f"\n   1. Label the data:")
    logger.info(f"      python label_data.py --input {text_file} --output training_data_labeled.json --limit 50")
    logger.info(f"\n   2. Train your model:")
    logger.info(f"      python train_ml_model.py --data training_data_labeled.json --iterations 30")
    logger.info(f"\n   3. See improvement!")
    logger.info(f"      Your ML model will handle the {len([d for d in data if not all(d['regex_extracted'].values())])} cases regex missed!")
    logger.info("")


if __name__ == "__main__":
    import sys

    if sys.platform == 'win32':
        # Windows fix for asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
