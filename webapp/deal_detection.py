"""
Deal detection service — identifies underpriced car offers.

Uses IQR-based statistics to compare each offer against its market segment
(brand + model + fuel + similar year). Cars priced significantly below the
segment median are flagged as deals with a deal_score percentage.

Year-aware segmentation: a 2005 Octavia is compared against 2002-2008 Octavias,
not against 2022 models. This prevents old cheap cars from showing as "deals".
"""

import logging
from collections import defaultdict
from statistics import median as calc_median, quantiles
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.model import Car

logger = logging.getLogger(__name__)

# Minimum offers in a segment to compute meaningful stats
MIN_SEGMENT_SIZE = 5

# Year tolerance bands for progressive relaxation
YEAR_BANDS = [3, 5, None]  # ±3 → ±5 → all years

# Price sanity bounds (CZK)
MIN_PRICE = 10_000
MAX_PRICE = 5_000_000


def calculate_segment_stats(prices: list[int]) -> Optional[dict]:
    """
    Calculate IQR-based statistics from a list of prices.

    Returns dict with q1, median, q3, iqr, count, or None if empty.
    """
    if not prices:
        return None

    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    med = calc_median(sorted_prices)

    if n < 4:
        # Not enough data for proper quartiles
        q1 = sorted_prices[0]
        q3 = sorted_prices[-1]
    else:
        q1, _, q3 = quantiles(sorted_prices, n=4)

    return {
        "q1": q1,
        "median": med,
        "q3": q3,
        "iqr": q3 - q1,
        "count": n,
    }


def score_offer(price: int, stats: dict) -> Optional[float]:
    """
    Calculate deal score: how much below median (%).

    Positive = cheaper than median. Negative = more expensive.
    Returns None if median is 0.
    """
    if not stats or stats["median"] == 0:
        return None
    return round((stats["median"] - price) / stats["median"] * 100, 1)


def _get_segment_offers(session: Session, brand: str, model: str,
                        fuel: Optional[str] = None) -> list[tuple]:
    """Fetch (id, price, year) tuples for a brand+model(+fuel) segment."""
    query = (
        session.query(Car.id, Car.price, Car.year_manufacture)
        .filter(
            Car.brand == brand,
            Car.model == model,
            Car.price > MIN_PRICE,
            Car.price < MAX_PRICE,
        )
    )
    if fuel:
        query = query.filter(Car.fuel == fuel)

    return query.all()


def _compute_year_band_stats(offers: list[tuple], year: Optional[int]) -> tuple[Optional[dict], str]:
    """
    Compute segment stats for a specific year with progressive relaxation.

    Tries ±3 years first, then ±5, then all years.

    Args:
        offers: list of (id, price, year) tuples for the segment
        year: target year (None = use all offers)

    Returns:
        (stats_dict, confidence) where confidence is "high", "medium", or "low"
    """
    if year is None:
        # No year info — use all offers
        prices = [price for _, price, _ in offers]
        stats = calculate_segment_stats(prices)
        if stats and stats["count"] >= MIN_SEGMENT_SIZE:
            return stats, "low"
        return None, "low"

    for band in YEAR_BANDS:
        if band is None:
            prices = [price for _, price, _ in offers]
            confidence = "low"
        else:
            prices = [
                price for _, price, yr in offers
                if yr is not None and abs(yr - year) <= band
            ]
            confidence = "high" if band <= 3 else "medium"

        stats = calculate_segment_stats(prices)
        if stats and stats["count"] >= MIN_SEGMENT_SIZE:
            return stats, confidence

    return None, "low"


_CONFIDENCE_LEVELS = {"high": 3, "medium": 2, "low": 1}


def find_deals(session: Session, brand: Optional[str] = None,
               model: Optional[str] = None, fuel: Optional[str] = None,
               min_score: float = 15, limit: int = 50, offset: int = 0,
               min_confidence: Optional[str] = None) -> dict:
    """
    Find underpriced offers using year-aware segmentation.

    Each offer is compared against similar cars of the same brand+model+fuel
    within a similar year range (±3 years, relaxing to ±5 or all if needed).

    Args:
        session: SQLAlchemy session
        brand: optional brand filter
        model: optional model filter
        fuel: optional fuel filter
        min_score: minimum deal score (%, default 15)
        limit: max results per page
        offset: pagination offset
        min_confidence: minimum confidence level ("high", "medium", or None for all)

    Returns:
        dict with 'deals' list and 'pagination' info
    """
    # Find segments with enough offers
    seg_query = (
        session.query(
            Car.brand, Car.model, Car.fuel,
            func.count(Car.id).label("cnt"),
        )
        .filter(
            Car.price > MIN_PRICE,
            Car.price < MAX_PRICE,
            Car.brand.isnot(None),
            Car.model.isnot(None),
        )
    )

    if brand:
        seg_query = seg_query.filter(Car.brand == brand)
    if model:
        seg_query = seg_query.filter(Car.model == model)
    if fuel:
        seg_query = seg_query.filter(Car.fuel == fuel)

    segments = (
        seg_query
        .group_by(Car.brand, Car.model, Car.fuel)
        .having(func.count(Car.id) >= MIN_SEGMENT_SIZE)
        .all()
    )

    all_deals = []

    for seg_brand, seg_model, seg_fuel, seg_count in segments:
        # Load all offers in this segment
        segment_offers = _get_segment_offers(session, seg_brand, seg_model, seg_fuel)
        if len(segment_offers) < MIN_SEGMENT_SIZE:
            continue

        # Cache stats per year to avoid recomputing
        year_stats_cache: dict[Optional[int], tuple] = {}

        # Load full car objects for potential deals (price below global segment median)
        # Pre-filter: only consider offers that could possibly be deals
        all_prices = [price for _, price, _ in segment_offers]
        global_stats = calculate_segment_stats(all_prices)
        if not global_stats or global_stats["median"] == 0:
            continue

        # Quick pre-filter: only look at cars below global median
        global_threshold = global_stats["median"] * (1 - min_score / 100)

        car_query = (
            session.query(Car)
            .filter(
                Car.brand == seg_brand,
                Car.model == seg_model,
                Car.price > MIN_PRICE,
                Car.price < global_threshold,
            )
        )
        if seg_fuel:
            car_query = car_query.filter(Car.fuel == seg_fuel)

        for car in car_query.all():
            # Get year-specific stats (with caching)
            year_key = car.year_manufacture
            if year_key not in year_stats_cache:
                year_stats_cache[year_key] = _compute_year_band_stats(
                    segment_offers, year_key
                )

            stats, confidence = year_stats_cache[year_key]
            if not stats or stats["median"] == 0:
                continue

            # Outlier floor: must be above 10% of year-band median
            outlier_floor = max(MIN_PRICE, stats["median"] * 0.10)
            if car.price <= outlier_floor:
                continue

            deal_score = score_offer(car.price, stats)
            if deal_score is None or deal_score < min_score:
                continue

            # Filter by confidence level
            if min_confidence:
                min_level = _CONFIDENCE_LEVELS.get(min_confidence, 0)
                cur_level = _CONFIDENCE_LEVELS.get(confidence, 0)
                if cur_level < min_level:
                    continue

            all_deals.append({
                "id": car.id,
                "brand": car.brand,
                "model": car.model,
                "fuel": car.fuel,
                "year_manufacture": car.year_manufacture,
                "mileage": car.mileage,
                "power": car.power,
                "price": car.price,
                "url": car.url,
                "review_status": car.review_status,
                "deal_score": deal_score,
                "median_price": round(stats["median"]),
                "segment_count": stats["count"],
                "confidence": confidence,
            })

    # Sort by deal score descending
    all_deals.sort(key=lambda d: d["deal_score"], reverse=True)

    total = len(all_deals)
    page_deals = all_deals[offset:offset + limit]

    return {
        "deals": page_deals,
        "pagination": {
            "page": (offset // limit) + 1 if limit else 1,
            "per_page": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit else 1,
        },
    }


def find_suspicious(session: Session, brand: Optional[str] = None,
                    model: Optional[str] = None, min_score: float = 25,
                    limit: int = 50, offset: int = 0,
                    hide_reviewed: bool = True) -> dict:
    """
    Find offers that look like great deals but are likely data errors.

    An offer is suspicious when:
    - deal_score is high (well below median) AND
    - it has missing fields, or outlier-range values

    Reuses the same segmentation logic as find_deals, but flags
    data quality issues instead of celebrating cheap prices.

    Args:
        hide_reviewed: if True, exclude offers with review_status set.

    Returns dict with 'offers' list and 'pagination' info.
    """
    # Get all "deals" with a high score threshold
    raw = find_deals(
        session, brand=brand, model=model,
        min_score=min_score, limit=10_000, offset=0,
    )

    # Build set of reviewed offer IDs to filter out
    reviewed_ids: set[int] = set()
    if hide_reviewed:
        rows = (
            session.query(Car.id, Car.review_status)
            .filter(Car.review_status.isnot(None))
            .all()
        )
        reviewed_ids = {row.id for row in rows}

    suspicious = []
    for deal in raw["deals"]:
        if hide_reviewed and deal["id"] in reviewed_ids:
            continue
        reasons = []

        # Missing core fields
        if deal["year_manufacture"] is None:
            reasons.append("chybí rok")
        if deal["mileage"] is None:
            reasons.append("chybí nájezd")
        if deal["fuel"] is None:
            reasons.append("chybí palivo")
        if deal["power"] is None:
            reasons.append("chybí výkon")

        # Outlier values
        if deal["mileage"] is not None and deal["mileage"] > 500_000:
            reasons.append(f"nájezd {deal['mileage']:,} km")
        if deal["mileage"] is not None and deal["mileage"] < 100:
            reasons.append(f"nájezd podezřele nízký ({deal['mileage']} km)")
        if deal["year_manufacture"] is not None and deal["year_manufacture"] < 1995:
            reasons.append(f"rok {deal['year_manufacture']}")

        # Extreme deal score suggests price or segment mismatch
        if deal["deal_score"] > 70:
            reasons.append(f"extrémní deal score {deal['deal_score']}%")

        # Very small segment — stats may be unreliable
        if deal["segment_count"] < 8:
            reasons.append(f"malý segment ({deal['segment_count']} aut)")

        if reasons:
            deal["suspicion_reasons"] = reasons
            deal["suspicion_count"] = len(reasons)
            suspicious.append(deal)

    # Sort by number of reasons (most suspicious first)
    suspicious.sort(key=lambda d: (d["suspicion_count"], d["deal_score"]), reverse=True)

    total = len(suspicious)
    page = suspicious[offset:offset + limit]

    return {
        "offers": page,
        "pagination": {
            "page": (offset // limit) + 1 if limit else 1,
            "per_page": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit else 1,
        },
    }


def score_single_offer(session: Session, car_id: int) -> Optional[dict]:
    """
    Score a single offer against its market segment (year-aware).

    Returns deal info dict or None if car not found / not enough data.
    """
    car = session.query(Car).filter(Car.id == car_id).first()
    if not car or not car.price or not car.brand or not car.model:
        return None

    # Try with fuel first, then without
    for try_fuel in [car.fuel, None]:
        segment_offers = _get_segment_offers(session, car.brand, car.model, try_fuel)
        if len(segment_offers) < MIN_SEGMENT_SIZE:
            continue

        stats, confidence = _compute_year_band_stats(segment_offers, car.year_manufacture)
        if stats and stats["count"] >= MIN_SEGMENT_SIZE:
            deal_score = score_offer(car.price, stats)
            return {
                "id": car.id,
                "brand": car.brand,
                "model": car.model,
                "fuel": car.fuel,
                "year_manufacture": car.year_manufacture,
                "mileage": car.mileage,
                "power": car.power,
                "price": car.price,
                "url": car.url,
                "deal_score": deal_score,
                "median_price": round(stats["median"]),
                "q1_price": round(stats["q1"]),
                "q3_price": round(stats["q3"]),
                "segment_count": stats["count"],
                "confidence": confidence,
            }

    return None
