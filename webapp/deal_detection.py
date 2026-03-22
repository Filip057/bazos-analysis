"""
Deal detection service — identifies underpriced car offers.

Uses IQR-based statistics to compare each offer against its market segment
(brand + model + fuel). Cars priced significantly below median are flagged
as deals with a deal_score percentage.
"""

import logging
from statistics import median as calc_median, quantiles
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.model import Car

logger = logging.getLogger(__name__)

# Minimum offers in a segment to compute meaningful stats
MIN_SEGMENT_SIZE = 5

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


def _get_segment_prices(session: Session, brand: str, model: str,
                        fuel: Optional[str] = None) -> list[int]:
    """Fetch all valid prices for a brand+model(+fuel) segment."""
    query = (
        session.query(Car.price)
        .filter(
            Car.brand == brand,
            Car.model == model,
            Car.price > MIN_PRICE,
            Car.price < MAX_PRICE,
        )
    )
    if fuel:
        query = query.filter(Car.fuel == fuel)

    return [row[0] for row in query.all()]


def find_deals(session: Session, brand: Optional[str] = None,
               model: Optional[str] = None, fuel: Optional[str] = None,
               min_score: float = 15, limit: int = 50, offset: int = 0) -> dict:
    """
    Find underpriced offers across market segments.

    Segments are defined as brand + model + fuel. For each segment with
    enough data, offers below median by at least min_score% are returned.

    Args:
        session: SQLAlchemy session
        brand: optional brand filter
        model: optional model filter
        fuel: optional fuel filter
        min_score: minimum deal score (%, default 15)
        limit: max results per page
        offset: pagination offset

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
        prices = _get_segment_prices(session, seg_brand, seg_model, seg_fuel)
        stats = calculate_segment_stats(prices)
        if not stats or stats["median"] == 0:
            continue

        # Find offers below the threshold in this segment
        # Skip extreme outliers: must be above Q1-1.5*IQR AND at least 10% of median
        threshold_price = stats["median"] * (1 - min_score / 100)
        iqr_floor = stats["q1"] - 1.5 * stats["iqr"] if stats["iqr"] > 0 else MIN_PRICE
        median_floor = stats["median"] * 0.10
        outlier_floor = max(MIN_PRICE, iqr_floor, median_floor)

        offer_query = (
            session.query(Car)
            .filter(
                Car.brand == seg_brand,
                Car.model == seg_model,
                Car.price > outlier_floor,
                Car.price < threshold_price,
            )
        )
        if seg_fuel:
            offer_query = offer_query.filter(Car.fuel == seg_fuel)

        for car in offer_query.all():
            deal_score = score_offer(car.price, stats)
            if deal_score is None or deal_score < min_score:
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
                "deal_score": deal_score,
                "median_price": round(stats["median"]),
                "segment_count": stats["count"],
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


def score_single_offer(session: Session, car_id: int) -> Optional[dict]:
    """
    Score a single offer against its market segment.

    Returns deal info dict or None if car not found / not enough data.
    """
    car = session.query(Car).filter(Car.id == car_id).first()
    if not car or not car.price or not car.brand or not car.model:
        return None

    # Try with fuel first, then without
    prices = _get_segment_prices(session, car.brand, car.model, car.fuel)
    confidence = "high"

    if len(prices) < MIN_SEGMENT_SIZE:
        prices = _get_segment_prices(session, car.brand, car.model, None)
        confidence = "low"

    if len(prices) < MIN_SEGMENT_SIZE:
        return None

    stats = calculate_segment_stats(prices)
    if not stats:
        return None

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
