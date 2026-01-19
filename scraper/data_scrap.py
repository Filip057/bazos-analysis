from collections import Counter
from bs4 import BeautifulSoup
import re
import logging

import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector

import time
from typing import List, Tuple, Optional, Dict

# dictionary for car brands and its models
from scraper.car_models import CAR_MODELS
import scraper.car_models as car_models

from scraper.database_operations import check_if_car, fetch_data_into_database

# Progress tracking
from tqdm.asyncio import tqdm as async_tqdm

# ML + Regex extraction system
from ml.production_extractor import ProductionExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SECTION FOR STOPWORDS
import nltk
nltk.download('punkt')
stopwords_set = set()

with open('stopwords-cs.txt', 'r', encoding='utf-8') as file:
    for line in file:
        word = line.strip()  # Remove leading/trailing whitespace and newline characters
        stopwords_set.add(word)

CAR_URL = 'https://auto.bazos.cz/'

CAR_MODELS = car_models.CAR_MODELS

CAR_BRANDS = ['alfa', 'audi', 'bmw', 'citroen', 'dacia', 'fiat',
              'ford', 'honda', 'hyundai', 'chevrolet', 'kia', 'mazda', 'mercedes', 'mitsubishi',
              'nissan', 'opel', 'peugeot', 'renault', 'seat', 'suzuki', 'skoda', 'toyota', 'volkswagen',
              'volvo']

# Extraction is now handled by ProductionExtractor (ML + context-aware regex)

# Connection pooling and rate limiting
MAX_CONCURRENT_REQUESTS = 20  # Limit concurrent requests to avoid overwhelming server
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds
CHUNK_SIZE = 50  # Process URLs in chunks
# Filter for string, clear it out of stop words
def preprocess_text(text):
    # Tokenize text, remove stopwords, and convert to lowercase
    tokens = nltk.word_tokenize(text)
    filtered_tokens = [token.lower() for token in tokens if token.lower() not in stopwords_set and token.isalnum()]
    return filtered_tokens

# analyse string to get frequecy of words in offers 
def get_frequency_analysis(string_list: list):

    combined_text = ' '.join(string_list)
    preprocessed_text = preprocess_text(combined_text)
    word_counts = Counter(preprocessed_text)
    return word_counts


# OLD EXTRACTION FUNCTIONS REMOVED - Now using ProductionExtractor (ML + context-aware regex)
# The new system combines:
#   - ML model (spaCy NER trained on 201+ examples)
#   - Context-aware regex (avoids false positives like STK dates)
#   - Continuous learning (auto-collects training data from production)

def get_model(brand, header: str) -> str:
    """Extract car model from header text (still uses regex as models vary by brand)"""
    models = CAR_MODELS.get(brand)
    if models is not None:
        pattern = re.compile(r'\b(?:' + '|'.join(models) + r')\b', re.IGNORECASE)
        match = pattern.search(header)
        if match:
            return match.group(0)
    return None

# ASYNCHRONOUS WEB SCRAPPING with error handling and retries
# Cascade of web scrapping to get detail info about car offer

async def fetch_data(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Optional[str]:
    """Fetch data from URL with retry logic and rate limiting"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with semaphore:  # Rate limiting
                async with session.get(url, timeout=ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                    response.raise_for_status()
                    return await response.text()
        except asyncio.TimeoutError:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            logger.warning(f"Timeout fetching {url} after {RETRY_ATTEMPTS} attempts")
        except aiohttp.ClientError as e:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            logger.error(f"Error fetching {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            break
    return None
# getting urls for brands
async def get_brand_urls(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Tuple[str, str]]:
    """Fetch car brands URLs asynchronously"""
    brand_url_list = []
    data = await fetch_data(CAR_URL, session, semaphore)
    if not data:
        logger.error("Failed to fetch brand URLs")
        return brand_url_list

    soup = BeautifulSoup(data, 'html.parser')
    menubar = soup.find(class_="barvaleva")
    if menubar:
        a_tags = menubar.find_all('a')
        for tag in a_tags[:24]:
            car_href = tag.get('href')
            brand = car_href[1:-1]
            brand_url_list.append((brand, f'https://auto.bazos.cz{car_href}'))
    return brand_url_list

# [(brand, brand_url)]

# for each brand getting urls for all their pages - PARALLELIZED
async def get_all_pages_for_brands(brand_url_list: List[Tuple[str, str]], session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Tuple[str, List[str]]]:
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

    # CRITICAL FIX: Process all brands in parallel instead of sequentially
    tasks = [fetch_brand_pages(brand, base_url) for brand, base_url in brand_url_list]
    results = await async_tqdm.gather(*tasks, desc="Fetching brand pages")
    return results

# [(brand, [all brand url pages])]

# going through brand pages and getting urls for car offers detail - CHUNKED PROCESSING
async def get_urls_for_details(brand_pages: List[Tuple[str, List[str]]], session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Tuple[str, str]]:
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

    # Build list of all tasks with brand info
    all_tasks = [(brand, url) for brand, pages in brand_pages for url in pages]

    # Process in chunks to avoid memory issues
    final_list = []
    for i in range(0, len(all_tasks), CHUNK_SIZE):
        chunk = all_tasks[i:i + CHUNK_SIZE]
        tasks = [fetch_and_process(brand, url) for brand, url in chunk]
        results = await async_tqdm.gather(*tasks, desc=f"Fetching detail URLs (chunk {i//CHUNK_SIZE + 1}/{(len(all_tasks)-1)//CHUNK_SIZE + 1})")
        for result in results:
            final_list.extend(result)

    return final_list

# [(brand, [all detail urls])]

# scrapping description, heading - CHUNKED PROCESSING
async def get_descriptions_headings_price(brand_urls: List[Tuple[str, str]], session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Tuple[str, str, str, str, int]]:
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
        except (AttributeError, IndexError, ValueError) as e:
            # Silently skip malformed pages
            return None

    # Process in chunks
    final_list = []
    for i in range(0, len(brand_urls), CHUNK_SIZE):
        chunk = brand_urls[i:i + CHUNK_SIZE]
        tasks = [fetch_and_process(brand, url) for brand, url in chunk]
        results = await async_tqdm.gather(*tasks, desc=f"Scraping car details (chunk {i//CHUNK_SIZE + 1}/{(len(brand_urls)-1)//CHUNK_SIZE + 1})")
        final_list.extend([result for result in results if result is not None])

    return final_list

# processing the string and retrieving the data
async def process_data(brand: str, url: str, description: str, heading: str, price: int, extractor: ProductionExtractor) -> Dict:
    """Extract structured data from car listing using ML + context-aware regex"""

    # Use production extractor (ML + regex) on combined text
    combined_text = f"{heading}\n{description}"
    extraction_result = extractor.extract(combined_text, car_id=url)

    # Extract model separately (brand-specific patterns)
    model = get_model(brand=brand, header=heading)

    car_data = {
        "brand": brand,
        "model": model,
        "year_manufacture": extraction_result.get('year'),
        "mileage": extraction_result.get('mileage'),
        "power": extraction_result.get('power'),
        "fuel": extraction_result.get('fuel'),  # NEW: fuel type from ML
        "price": price,
        "heading": heading,
        "url": url,
        # Additional metadata from extraction
        "extraction_confidence": extraction_result.get('confidence'),  # high/medium/low
        "needs_review": extraction_result.get('flagged_for_review', False)
    }
    return car_data


# all together
async def main():
    """Main scraping orchestrator with ML extraction and connection pooling"""
    # Initialize production extractor (ML + context-aware regex)
    logger.info("Initializing ML + Regex extraction system...")
    extractor = ProductionExtractor()
    logger.info("✓ Production extractor ready")

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Configure connection pooling
    connector = TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=10)
    timeout = ClientTimeout(total=REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        logger.info("="*60)
        logger.info("Starting scraping process...")
        logger.info("="*60)

        # Step 1: Get car brands URLs (uncomment to scrape all brands)
        # brand_urls = await get_brand_urls(session, semaphore)
        # For testing, use a single brand:
        brand_urls = [('chevrolet', 'https://auto.bazos.cz/chevrolet/')]
        logger.info(f"Target brands: {', '.join([b[0] for b in brand_urls])}")

        # Step 2: Get all pages for each brand IN PARALLEL
        logger.info(f"Fetching pages for {len(brand_urls)} brand(s)...")
        brand_pages = await get_all_pages_for_brands(brand_urls, session, semaphore)
        total_pages = sum(len(pages) for _, pages in brand_pages)
        logger.info(f"Found {total_pages} pages to scrape")

        # Step 3: Get URLs for details on each page with chunked processing
        logger.info("Fetching detail URLs...")
        urls_detail_list = await get_urls_for_details(brand_pages, session, semaphore)
        logger.info(f"Found {len(urls_detail_list)} car listings")

        # Step 4: Get descriptions, headings, and prices with chunked processing
        logger.info("Scraping car details...")
        descriptions_headings_price_list = await get_descriptions_headings_price(urls_detail_list, session, semaphore)
        logger.info(f"Successfully scraped {len(descriptions_headings_price_list)} cars")

        # Step 5: Process data to extract structured information with ML
        logger.info("Extracting car data (ML + context-aware regex)...")
        tasks = [process_data(brand, url, description, heading, price, extractor)
                 for brand, url, description, heading, price in descriptions_headings_price_list]
        processed_data = await asyncio.gather(*tasks)

        # Step 6: Save extraction queues (training data and disagreements)
        logger.info("Saving ML extraction queues...")
        extractor.save_queues()
        extractor.print_stats()

        # Step 7: Save data into database
        logger.info("Saving to database...")
        await fetch_data_into_database(data=processed_data)
        logger.info(f"✓ Successfully saved {len(processed_data)} cars to database")

async def run():
    await main()


if __name__ == "__main__":
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("BAZOS CAR SCRAPER - OPTIMIZED VERSION")
    logger.info("=" * 60)
    asyncio.run(run())
    end_time = time.time()
    elapsed = end_time - start_time
    logger.info("\n" + "=" * 60)
    logger.info(f"✓ Execution time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    logger.info("=" * 60)
    

