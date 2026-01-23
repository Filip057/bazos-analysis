"""
Standalone Scraper for ML Training Data
========================================

This version DOES NOT need database connection.
Perfect for running on your laptop without MySQL!

Usage:
    python3 scrape_for_training_standalone.py --limit 100 --brand toyota
"""

import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
import argparse
import logging
from typing import List, Dict, Tuple, Optional
import json
import re
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm as async_tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MAX_CONCURRENT_REQUESTS = 20
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1
REQUEST_TIMEOUT = 30
CHUNK_SIZE = 50

# Import centralized regex patterns
from patterns import (
    MILEAGE_PATTERN_1,
    MILEAGE_PATTERN_2,
    MILEAGE_PATTERN_3,
    POWER_PATTERN,
    YEAR_PATTERN
)


# Extraction functions (copied from data_scrap.py)
def get_mileage(long_string: str) -> Optional[int]:
    """Extract mileage from text"""
    text = re.sub(r'[^\w\s]', '', long_string.lower())

    matches1 = MILEAGE_PATTERN_1.findall(text)
    if matches1:
        try:
            return int(matches1[0].replace(' ', ''))
        except ValueError:
            pass

    matches2 = MILEAGE_PATTERN_2.findall(text)
    if matches2:
        try:
            return int(matches2[0].replace(' ', '')) * 1000
        except ValueError:
            pass

    matches3 = MILEAGE_PATTERN_3.findall(text)
    if matches3:
        try:
            return int(matches3[0].replace(' ', '')) * 1000
        except ValueError:
            pass

    return None


def get_power(long_string: str) -> Optional[int]:
    """Extract power from text"""
    text = re.sub(r'[^\w\s]', '', long_string.lower())
    match = POWER_PATTERN.search(text)
    if match:
        return int(re.sub(r'\D', '', match.group(1)))
    return None


def get_year_manufacture(long_string: str) -> Optional[int]:
    """Extract year from text"""
    match = YEAR_PATTERN.search(long_string)
    if match:
        return int(match.group(1))
    return None


def check_if_car(model, heading, price):
    """Check if listing is actually a car"""
    if model == None:
        return False
    if price is None or price < 5000:
        return False

    non_car_keywords = ['ALU','kola' ,'kol' , 'motor','sada','díly', 'sklo',
                       'převodovka', 'pneu', 'pneumatiky', 'disky', 'sedadla',
                       'baterie', 'náhradní', 'zrcátka', 'motocykl', 'motorky',
                       'moto', 'kolo', 'kola', 'skútr','motorové', 'karavany',
                       'choppery', 'endura', 'autobus', 'autodíly', 'zimní', 'letní']

    non_car_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, non_car_keywords)) + r')\b', re.IGNORECASE)

    return not bool(non_car_pattern.search(heading))


# Async scraping functions
async def fetch_data(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Optional[str]:
    """Fetch data from URL with retry logic"""
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
            logger.warning(f"Timeout fetching {url}")
        except aiohttp.ClientError as e:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            logger.error(f"Error fetching {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            break
    return None


async def get_all_pages_for_brands(brand_url_list: List[Tuple[str, str]],
                                   session: aiohttp.ClientSession,
                                   semaphore: asyncio.Semaphore) -> List[Tuple[str, List[str]]]:
    """Fetch all pages for each brand in parallel"""

    async def fetch_brand_pages(brand: str, base_url: str) -> Tuple[str, List[str]]:
        data = await fetch_data(base_url, session, semaphore)
        if not data:
            return (brand, [])

        soup = BeautifulSoup(data, 'html.parser')
        try:
            num_of_objs_text = soup.find('div', class_='inzeratynadpis').text.split('z ')[1].strip()
            num_of_objs = int(num_of_objs_text.replace(' ', ''))
            pages = [f"{base_url}{x}/" for x in range(20, num_of_objs, 20)]
            return (brand, pages)
        except (AttributeError, IndexError, ValueError) as e:
            logger.warning(f"Error parsing pages for {brand}: {e}")
            return (brand, [])

    tasks = [fetch_brand_pages(brand, base_url) for brand, base_url in brand_url_list]
    results = await async_tqdm.gather(*tasks, desc="Fetching brand pages")
    return results


async def get_urls_for_details(brand_pages: List[Tuple[str, List[str]]],
                               session: aiohttp.ClientSession,
                               semaphore: asyncio.Semaphore) -> List[Tuple[str, str]]:
    """Fetch detail URLs from brand pages with chunked processing"""

    async def fetch_and_process(brand: str, url: str) -> List[Tuple[str, str]]:
        data = await fetch_data(url, session, semaphore)
        if not data:
            return []

        soup = BeautifulSoup(data, 'html.parser')
        headings = soup.find_all('div', class_='inzeraty inzeratyflex')
        urls_detail_list = []
        if headings:
            for head in headings:
                try:
                    relative_url = head.find('a').get('href')
                    absolute_url = f"https://auto.bazos.cz{relative_url}"
                    urls_detail_list.append((brand, absolute_url))
                except (AttributeError, TypeError):
                    continue
        return urls_detail_list

    all_tasks = [(brand, url) for brand, pages in brand_pages for url in pages]

    final_list = []
    for i in range(0, len(all_tasks), CHUNK_SIZE):
        chunk = all_tasks[i:i + CHUNK_SIZE]
        tasks = [fetch_and_process(brand, url) for brand, url in chunk]
        results = await async_tqdm.gather(*tasks, desc=f"Fetching URLs (chunk {i//CHUNK_SIZE + 1})")
        for result in results:
            final_list.extend(result)

    return final_list


async def get_descriptions_headings_price(brand_urls: List[Tuple[str, str]],
                                         session: aiohttp.ClientSession,
                                         semaphore: asyncio.Semaphore) -> List[Tuple[str, str, str, str, int]]:
    """Scrape car details with chunked processing"""

    async def fetch_and_process(brand: str, url: str) -> Optional[Tuple[str, str, str, str, int]]:
        data = await fetch_data(url, session, semaphore)
        if not data:
            return None

        try:
            soup = BeautifulSoup(data, 'html.parser')

            description = soup.find('div', class_='popisdetail').text.strip()
            heading = soup.find(class_="nadpisdetail").text.strip()
            price_nc = soup.find('table').find('td', class_='listadvlevo').find('table').find_all('tr')[-1].text
            price_digits = ''.join(re.findall(r'\d+', price_nc))
            price = int(price_digits) if price_digits else None

            is_car = check_if_car(description, heading, price=price)
            if not is_car:
                return None

            return brand, url, description, heading, price
        except (AttributeError, IndexError, ValueError):
            return None

    final_list = []
    for i in range(0, len(brand_urls), CHUNK_SIZE):
        chunk = brand_urls[i:i + CHUNK_SIZE]
        tasks = [fetch_and_process(brand, url) for brand, url in chunk]
        results = await async_tqdm.gather(*tasks, desc=f"Scraping details (chunk {i//CHUNK_SIZE + 1})")
        final_list.extend([result for result in results if result is not None])

    return final_list


# Main scraper class
class TrainingDataScraper:
    """Standalone scraper that doesn't need database"""

    async def scrape_for_training(self, brand_urls: List[Tuple[str, str]], limit: int = 100) -> List[Dict]:
        """Scrape real car descriptions for training"""
        logger.info(f"Starting training data collection...")
        logger.info(f"Target: {limit} car descriptions")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        connector = TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=10)
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            logger.info(f"Fetching pages for {len(brand_urls)} brand(s)...")
            brand_pages = await get_all_pages_for_brands(brand_urls, session, semaphore)

            logger.info("Fetching detail URLs...")
            all_detail_urls = await get_urls_for_details(brand_pages, session, semaphore)

            detail_urls = all_detail_urls[:limit]
            logger.info(f"Will scrape {len(detail_urls)} car listings")

            logger.info("Scraping car details...")
            scraped_cars = await get_descriptions_headings_price(detail_urls, session, semaphore)

            training_data = []
            for i, (brand, url, description, heading, price) in enumerate(scraped_cars, 1):
                regex_mileage = get_mileage(description) or get_mileage(heading)
                regex_year = get_year_manufacture(description) or get_year_manufacture(heading)
                regex_power = get_power(description) or get_power(heading)

                full_text = f"{heading}. {description}"

                entry = {
                    'id': i,
                    'text': full_text,
                    'heading': heading,
                    'description': description,
                    'brand': brand,
                    'url': url,
                    'price': price,
                    'regex_extracted': {
                        'mileage': regex_mileage,
                        'year': regex_year,
                        'power': regex_power
                    }
                }

                training_data.append(entry)

                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(scraped_cars)} cars")

            logger.info(f"\n✓ Scraped {len(training_data)} cars successfully!")
            return training_data

    def save_for_labeling(self, data: List[Dict], output_file: str):
        """Save scraped data for labeling"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Saved full data to {output_file}")

        text_file = output_file.replace('.json', '_texts.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            for entry in data:
                f.write(entry['text'] + '\n')
        logger.info(f"✓ Saved texts for labeling to {text_file}")

        return text_file

    def analyze_regex_performance(self, data: List[Dict]):
        """Analyze how well current regex performs"""
        total = len(data)
        mileage_found = sum(1 for d in data if d['regex_extracted']['mileage'] is not None)
        year_found = sum(1 for d in data if d['regex_extracted']['year'] is not None)
        power_found = sum(1 for d in data if d['regex_extracted']['power'] is not None)
        all_found = sum(1 for d in data if all(d['regex_extracted'].values()))

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

        failures = [d for d in data if not all(d['regex_extracted'].values())]

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
    parser = argparse.ArgumentParser(description="Scrape real car data for ML training (standalone, no database needed)")
    parser.add_argument("--limit", type=int, default=100, help="Number of cars to scrape")
    parser.add_argument("--brand", default="toyota", help="Brand to scrape")
    parser.add_argument("--output", default="training_data_scraped.json", help="Output JSON file")
    parser.add_argument("--multiple-brands", nargs="+", help="Scrape multiple brands")

    args = parser.parse_args()

    if args.multiple_brands:
        brand_urls = [(brand, f'https://auto.bazos.cz/{brand}/') for brand in args.multiple_brands]
    else:
        brand_urls = [(args.brand, f'https://auto.bazos.cz/{args.brand}/')]

    logger.info(f"\n{'='*60}")
    logger.info(f"Standalone Scraper for ML Training Data")
    logger.info(f"{'='*60}")
    logger.info(f"Brands: {', '.join([b for b, _ in brand_urls])}")
    logger.info(f"Limit: {args.limit} cars")
    logger.info(f"{'='*60}\n")

    scraper = TrainingDataScraper()
    data = await scraper.scrape_for_training(brand_urls, limit=args.limit)

    if not data:
        logger.error("❌ No data scraped!")
        return

    scraper.analyze_regex_performance(data)
    text_file = scraper.save_for_labeling(data, args.output)

    logger.info("\n" + "="*60)
    logger.info("✅ Data collection complete!")
    logger.info("="*60)
    logger.info(f"\n📁 Files created:")
    logger.info(f"   1. {args.output}")
    logger.info(f"   2. {text_file}")
    logger.info(f"\n🎯 Next steps:")
    logger.info(f"\n   python3 label_data.py --input {text_file} --output training_data_labeled.json --limit 50")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
