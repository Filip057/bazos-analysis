"""
Mixed Brand Scraper
===================

Scrapes multiple brands with different counts per brand.

Usage:
    python3 scrape_mixed_brands.py --brands toyota:17 skoda:17 volkswagen:16 --output training_mixed.json
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path

# Import the standalone scraper
from labeling.scrape_for_training_standalone import TrainingDataScraper, logger


async def scrape_mixed_brands(brand_counts: list, output_file: str):
    """
    Scrape multiple brands with specific counts

    Args:
        brand_counts: List of "brand:count" strings, e.g., ["toyota:17", "skoda:17", "volkswagen:16"]
        output_file: Output JSON file
    """
    # Parse brand:count format
    brands_config = []
    total_count = 0

    for bc in brand_counts:
        if ':' not in bc:
            logger.error(f"❌ Invalid format: {bc}. Use 'brand:count' format (e.g., 'toyota:17')")
            sys.exit(1)

        brand, count_str = bc.split(':', 1)
        try:
            count = int(count_str)
        except ValueError:
            logger.error(f"❌ Invalid count for {brand}: {count_str}")
            sys.exit(1)

        brands_config.append((brand, count))
        total_count += count

    logger.info(f"\n{'='*60}")
    logger.info(f"Mixed Brand Scraper")
    logger.info(f"{'='*60}")
    for brand, count in brands_config:
        logger.info(f"  {brand}: {count} cars")
    logger.info(f"Total: {total_count} cars")
    logger.info(f"{'='*60}\n")

    # Scrape each brand
    all_data = []
    scraper = TrainingDataScraper()

    for brand, count in brands_config:
        logger.info(f"\n📥 Scraping {brand}...")
        brand_url = [(brand, f'https://auto.bazos.cz/{brand}/')]

        brand_data = await scraper.scrape_for_training(brand_url, limit=count)

        if brand_data:
            logger.info(f"✓ Got {len(brand_data)} cars from {brand}")
            all_data.extend(brand_data)
        else:
            logger.warning(f"⚠️  No data from {brand}")

    if not all_data:
        logger.error("❌ No data scraped at all!")
        return

    # Save combined data
    scraper.save_for_labeling(all_data, output_file)

    # Show analysis
    scraper.analyze_regex_performance(all_data)

    logger.info("\n" + "="*60)
    logger.info("✅ Mixed brand scraping complete!")
    logger.info("="*60)
    logger.info(f"Total cars scraped: {len(all_data)}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"\n🎯 Next steps:")
    logger.info(f"   1. Filter: python3 filter_training_data.py --input {output_file} --output filtered_{output_file}")
    logger.info(f"   2. Label:  python3 label_data.py --input filtered_{output_file} --output training_data_labeled.json --limit 50")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape multiple brands with specific counts per brand"
    )
    parser.add_argument(
        "--brands",
        nargs="+",
        required=True,
        help="Brand and count pairs in format 'brand:count' (e.g., toyota:17 skoda:17 volkswagen:16)"
    )
    parser.add_argument(
        "--output",
        default="training_mixed.json",
        help="Output JSON file (default: training_mixed.json)"
    )

    args = parser.parse_args()

    asyncio.run(scrape_mixed_brands(args.brands, args.output))


if __name__ == "__main__":
    main()
