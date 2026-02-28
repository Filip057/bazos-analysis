"""
Resilient Pipeline Runner
==========================

Replaces data_scrap.main() with a checkpoint-based, per-URL pipeline.

Key improvements over the old approach:
    OLD: load all URLs → scrape all → extract all → save all  (crash = restart from 0)
    NEW: per-URL scrape+extract+save with checkpoint after each  (crash = resume)

Error isolation:
    - One failed URL  → log + continue (other URLs not affected)
    - One failed page → log + continue (other pages not affected)
    - One failed brand→ log + continue (other brands not affected)

Checkpoint/resume:
    - After each successfully saved URL, checkpoint is updated
    - On resume, already-done URLs are skipped automatically
    - Failed URLs are retried on resume (not skipped!)

Usage:
    # Run from scratch
    runner = PipelineRunner()
    asyncio.run(runner.run(brands=['skoda', 'volkswagen']))

    # Auto-resume last incomplete session
    runner = PipelineRunner.resume_last()
    asyncio.run(runner.run())

    # Resume specific session
    runner = PipelineRunner.resume('20250225_143000')
    asyncio.run(runner.run())

    # Test mode (no DB writes)
    runner = PipelineRunner(skip_db=True)
    asyncio.run(runner.run(brands=['skoda']))

CLI:
    python3 -m pipeline.runner --brands skoda volkswagen
    python3 -m pipeline.runner --resume
    python3 -m pipeline.runner --resume 20250225_143000
    python3 -m pipeline.runner --list-sessions
"""

import asyncio
import logging
import re
import time
from typing import List, Optional, Tuple

import aiomysql
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from bs4 import BeautifulSoup
from tqdm import tqdm

from ml.production_extractor import ProductionExtractor
from pipeline.checkpoint import CheckpointManager
from scraper.data_scrap import (
    fetch_data,
    get_brand_urls,
    get_all_pages_for_brands,
    get_model,
    CAR_BRANDS,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT,
    CHUNK_SIZE,
)
from scraper.database_operations import (
    check_if_car,
    compute_derived_metrics,
    get_model_id_sync,
    Session,
    UNIQUE_ID_PATTERN,
    init_database,
)
from webapp.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class PipelineRunner:
    """
    Resilient scraping pipeline with checkpoint-based resume.

    Processes each URL independently:
      1. Check checkpoint → skip if already done
      2. Fetch HTML
      3. Parse content (description, heading, price)
      4. Filter non-car items
      5. Extract data with ML + regex
      6. Save to database
      7. Mark URL as done in checkpoint
    """

    def __init__(
        self,
        checkpoint: Optional[CheckpointManager] = None,
        skip_db: bool = False,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
        url_limit: Optional[int] = None,
    ):
        self.checkpoint = checkpoint or CheckpointManager()
        self.skip_db = skip_db
        self.max_concurrent = max_concurrent
        self.url_limit = url_limit
        self.extractor: Optional[ProductionExtractor] = None
        self._runtime_stats = {
            "saved": 0, "failed": 0, "filtered": 0, "skipped": 0
        }

    # ------------------------------------------------------------------
    # Class-level constructors for resume
    # ------------------------------------------------------------------

    @classmethod
    def resume_last(cls, **kwargs) -> 'PipelineRunner':
        """Resume the most recent incomplete session."""
        checkpoint = CheckpointManager.resume_last()
        if checkpoint is None:
            logger.info("No incomplete session found. Starting fresh.")
            checkpoint = CheckpointManager()
        return cls(checkpoint=checkpoint, **kwargs)

    @classmethod
    def resume(cls, session_id: str, **kwargs) -> 'PipelineRunner':
        """Resume a specific session by ID."""
        checkpoint = CheckpointManager(session_id=session_id)
        return cls(checkpoint=checkpoint, **kwargs)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(self, brands: Optional[List[str]] = None, url_limit: Optional[int] = None):
        """
        Run the full pipeline.

        Args:
            brands: List of brand names to scrape, or None to scrape all.
            url_limit: Optional limit on total URLs to process (for testing).
        """
        logger.info("=" * 65)
        logger.info(f"PIPELINE SESSION: {self.checkpoint.session_id}")
        logger.info(f"DB writes:        {'DISABLED (test mode)' if self.skip_db else 'ENABLED'}")
        logger.info("=" * 65)

        # Initialize ML extractor once (expensive - loaded once, reused per URL)
        logger.info("Loading ML extractor (spaCy NER model)...")
        self.extractor = ProductionExtractor()
        logger.info("ML extractor ready.")

        semaphore = asyncio.Semaphore(self.max_concurrent)
        connector = TCPConnector(limit=self.max_concurrent, limit_per_host=10)
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)
        start_time = time.time()

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as http_session:
            if self.skip_db:
                await self._run_pipeline(http_session, semaphore, brands=brands, db_pool=None, url_limit=url_limit or self.url_limit)
            else:
                # Initialize DB tables (idempotent)
                try:
                    init_database()
                except Exception as e:
                    logger.error(f"DB init failed: {e}. Check MySQL connection and .env config.")
                    raise

                async with aiomysql.create_pool(
                    host=config.MYSQL_HOST,
                    port=int(config.MYSQL_PORT),
                    user=config.MYSQL_USER,
                    password=config.MYSQL_PASSWORD,
                    db=config.MYSQL_DATABASE,
                    minsize=2,
                    maxsize=10,
                    autocommit=False,
                ) as db_pool:
                    await self._run_pipeline(http_session, semaphore, brands=brands, db_pool=db_pool, url_limit=url_limit or self.url_limit)

        # Finalize
        elapsed = time.time() - start_time
        self.checkpoint.save(force=True)
        self.checkpoint.complete()

        # Save ML learning queues
        if self.extractor:
            try:
                self.extractor.save_queues()
                self.extractor.print_stats()
            except Exception as e:
                logger.warning(f"Could not save ML queues: {e}")

        self._print_final_stats(elapsed)

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    async def _run_pipeline(self, http_session, semaphore, brands, db_pool, url_limit=None):
        """Iterate over brands, then pages, then individual URLs."""
        brand_list = await self._resolve_brands(brands, http_session, semaphore)
        logger.info(f"Brands to process: {[b for b, _ in brand_list]}")

        if url_limit:
            logger.info(f"URL limit: {url_limit} (test mode)")

        total_processed = 0
        for brand, brand_url in brand_list:
            if self.checkpoint.is_brand_done(brand):
                logger.info(f"  Skipping brand '{brand}' (already completed in this session)")
                self._runtime_stats["skipped"] += 1
                continue

            try:
                logger.info(f"  Processing brand: {brand}")
                processed = await self._process_brand(brand, brand_url, http_session, semaphore, db_pool, url_limit=url_limit, total_processed=total_processed)
                total_processed += processed

                if url_limit and total_processed >= url_limit:
                    logger.info(f"URL limit ({url_limit}) reached. Stopping.")
                    break

                self.checkpoint.mark_brand_done(brand)
                logger.info(f"  Brand '{brand}' done.")
            except Exception as e:
                # Brand-level error: log and continue with next brand
                logger.error(f"  Brand '{brand}' failed unexpectedly: {e}. Continuing...")

    async def _process_brand(self, brand, brand_url, http_session, semaphore, db_pool, url_limit=None, total_processed=0):
        """
        Process all pages for a single brand.

        Returns: Number of URLs processed in this brand.
        """
        # Get all pages for this brand
        pages_result = await get_all_pages_for_brands(
            [(brand, brand_url)], http_session, semaphore
        )
        pages = pages_result[0][1] if pages_result else []
        logger.info(f"    {brand}: {len(pages)} pages")

        processed_count = 0

        # Process page by page (not all at once to avoid memory blowup)
        for page_url in pages:
            try:
                detail_urls = await self._get_detail_urls(page_url, http_session, semaphore)

                # Apply URL limit if specified
                if url_limit:
                    remaining = url_limit - (total_processed + processed_count)
                    if remaining <= 0:
                        logger.info(f"    URL limit reached for brand '{brand}'. Stopping.")
                        break
                    detail_urls = detail_urls[:remaining]

                # Process detail URLs in small concurrent chunks
                for chunk_start in range(0, len(detail_urls), CHUNK_SIZE):
                    chunk = detail_urls[chunk_start:chunk_start + CHUNK_SIZE]
                    tasks = [
                        self._process_single_url(brand, url, http_session, semaphore, db_pool)
                        for url in chunk
                    ]
                    # return_exceptions=True ensures one failure doesn't cancel the others
                    await asyncio.gather(*tasks, return_exceptions=True)
                    processed_count += len(chunk)
            except Exception as e:
                # Page-level error: log and continue with next page
                logger.error(f"    Page {page_url} failed: {e}. Skipping page.")

        return processed_count

    async def _get_detail_urls(self, page_url, http_session, semaphore) -> List[str]:
        """Extract all detail listing URLs from a single page."""
        html = await fetch_data(page_url, http_session, semaphore)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        headings = soup.find_all('div', class_='inzeraty inzeratyflex')
        urls = []
        for head in headings:
            try:
                relative_url = head.find('a').get('href')
                urls.append(f"https://auto.bazos.cz{relative_url}")
            except (AttributeError, TypeError):
                continue
        return urls

    async def _process_single_url(self, brand, url, http_session, semaphore, db_pool) -> str:
        """
        Process one car listing URL end-to-end with full error isolation.

        Returns: 'saved' | 'filtered' | 'failed' | 'skipped'
        """
        # 1. Checkpoint: already done?
        if self.checkpoint.is_url_done(url):
            self._runtime_stats["skipped"] += 1
            return "skipped"

        try:
            # 2. Fetch HTML
            html = await fetch_data(url, http_session, semaphore)
            if not html:
                self.checkpoint.mark_url_done(url, "failed")
                self._runtime_stats["failed"] += 1
                return "failed"

            # 3. Parse content
            parsed = self._parse_car_page(html)
            if parsed is None:
                self.checkpoint.mark_url_done(url, "failed")
                self._runtime_stats["failed"] += 1
                return "failed"

            description, heading, price = parsed

            # 4. Filter non-car items (tires, parts, motorcycles, ...)
            if not check_if_car(description, heading, price):
                self.checkpoint.mark_url_done(url, "filtered")
                self._runtime_stats["filtered"] += 1
                return "filtered"

            # 5. Extract data (ML + context-aware regex)
            combined_text = f"{heading}\n{description}"
            extraction = self.extractor.extract(combined_text, car_id=url)

            car_data = {
                "brand": brand,
                "model": get_model(brand=brand, header=heading),
                "year_manufacture": extraction.get("year"),
                "mileage": extraction.get("mileage"),
                "power": extraction.get("power"),
                "fuel": extraction.get("fuel"),
                "price": price,
                "url": url,
                "extraction_confidence": extraction.get("confidence"),
            }

            # 6. Save to DB
            if not self.skip_db and db_pool:
                await self._save_to_db(db_pool, car_data)

            # 7. Checkpoint: mark done
            self.checkpoint.mark_url_done(url, "saved")
            self._runtime_stats["saved"] += 1
            return "saved"

        except Exception as e:
            # URL-level error: log and continue
            logger.warning(f"URL {url} failed: {e}")
            self.checkpoint.mark_url_done(url, "failed")
            self._runtime_stats["failed"] += 1
            return "failed"

    # ------------------------------------------------------------------
    # DB operations
    # ------------------------------------------------------------------

    async def _save_to_db(self, db_pool, car_data: dict):
        """Save a single car offer to the database (upsert by unique_id)."""
        # Synchronous model_id lookup (cached)
        session = Session()
        try:
            model_id = get_model_id_sync(session, car_data["brand"], car_data["model"])
        finally:
            session.close()

        if not model_id:
            return  # Unknown brand/model combination

        unique_id_match = UNIQUE_ID_PATTERN.search(car_data["url"])
        unique_id = unique_id_match.group(1) if unique_id_match else None

        years_in_usage, price_per_km, mileage_per_year = compute_derived_metrics(
            car_data["price"], car_data["mileage"], car_data["year_manufacture"]
        )

        sql = """
        INSERT INTO offers (
            model_id, year_manufacture, mileage, power, fuel,
            price, url, years_in_usage, price_per_km, mileage_per_year,
            unique_id, scraped_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            year_manufacture = VALUES(year_manufacture),
            mileage          = VALUES(mileage),
            power            = VALUES(power),
            fuel             = VALUES(fuel),
            price            = VALUES(price),
            years_in_usage   = VALUES(years_in_usage),
            price_per_km     = VALUES(price_per_km),
            mileage_per_year = VALUES(mileage_per_year),
            scraped_at       = NOW()
        """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (
                    model_id,
                    car_data["year_manufacture"],
                    car_data["mileage"],
                    car_data["power"],
                    car_data["fuel"],
                    car_data["price"],
                    car_data["url"],
                    years_in_usage,
                    price_per_km,
                    mileage_per_year,
                    unique_id,
                ))
                await conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_brands(self, brands, http_session, semaphore) -> List[Tuple[str, str]]:
        """Resolve brand names to (brand, url) pairs."""
        if brands:
            result = []
            for brand in brands:
                b = brand.lower().strip()
                if b in CAR_BRANDS:
                    result.append((b, f"https://auto.bazos.cz/{b}/"))
                else:
                    logger.warning(f"Unknown brand '{brand}' — skipping.")
            return result
        else:
            logger.info("No brands specified — fetching all from Bazos.cz")
            return await get_brand_urls(http_session, semaphore)

    def _parse_car_page(self, html: str):
        """
        Parse car detail page HTML.
        Returns (description, heading, price) or None if parsing fails.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            description = soup.find("div", class_="popisdetail").text.strip()
            heading = soup.find(class_="nadpisdetail").text.strip()
            price_nc = (
                soup.find("table")
                .find("td", class_="listadvlevo")
                .find("table")
                .find_all("tr")[-1]
                .text
            )
            price_digits = "".join(re.findall(r"\d+", price_nc))
            price = int(price_digits) if price_digits else None
            return description, heading, price
        except (AttributeError, IndexError, ValueError):
            return None

    def _print_final_stats(self, elapsed: float):
        total = sum(self._runtime_stats.values())
        logger.info("=" * 65)
        logger.info(f"PIPELINE COMPLETE   ({elapsed:.1f}s / {elapsed/60:.1f}min)")
        logger.info(f"  Saved:    {self._runtime_stats['saved']:>6}")
        logger.info(f"  Failed:   {self._runtime_stats['failed']:>6}")
        logger.info(f"  Filtered: {self._runtime_stats['filtered']:>6}")
        logger.info(f"  Skipped:  {self._runtime_stats['skipped']:>6} (already done)")
        logger.info(f"  Total:    {total:>6}")
        logger.info(f"  Session:  {self.checkpoint.session_id}")
        logger.info("=" * 65)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("pipeline.log"),
            logging.StreamHandler(),
        ],
    )

    parser = argparse.ArgumentParser(
        description="Resilient Bazos scraping pipeline with checkpoint/resume",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape Škoda (new session)
  python3 -m pipeline.runner --brands skoda

  # Scrape multiple brands
  python3 -m pipeline.runner --brands skoda volkswagen audi

  # Test mode (no DB, limit 10 URLs)
  python3 -m pipeline.runner --brands skoda --skip-db --limit 10

  # Auto-resume last incomplete session
  python3 -m pipeline.runner --resume

  # Resume specific session
  python3 -m pipeline.runner --resume 20250225_143000

  # List all sessions
  python3 -m pipeline.runner --list-sessions
        """,
    )

    parser.add_argument("--brands", nargs="+", help="Brand names to scrape")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="last",
        metavar="SESSION_ID",
        help="Resume last incomplete session, or specify a session ID",
    )
    parser.add_argument("--skip-db", action="store_true", help="Skip DB writes (test mode)")
    parser.add_argument("--limit", type=int, metavar="N", help="Limit total URLs to process (for testing)")
    parser.add_argument("--list-sessions", action="store_true", help="List all pipeline sessions")

    args = parser.parse_args()

    if args.list_sessions:
        CheckpointManager.print_sessions()
        sys.exit(0)

    # Build runner
    if args.resume == "last":
        runner = PipelineRunner.resume_last(skip_db=args.skip_db, url_limit=args.limit)
    elif args.resume:
        runner = PipelineRunner.resume(args.resume, skip_db=args.skip_db, url_limit=args.limit)
    else:
        runner = PipelineRunner(skip_db=args.skip_db, url_limit=args.limit)

    asyncio.run(runner.run(brands=args.brands))
