"""
Admin data operations — all database write operations for the admin browser.

Keeps write logic out of Flask routes (per project convention).
Reads use the Car view model, writes target the Offer table directly.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import func, case, literal
from sqlalchemy.orm import Session

from database.model import Car, Offer

logger = logging.getLogger(__name__)

# Editable fields with validation rules: (min, max) or allowed values
EDITABLE_FIELDS = {
    "year_manufacture": {"type": "int", "min": 1900, "max": datetime.now().year + 1},
    "mileage": {"type": "int", "min": 0, "max": 1_000_000},
    "power": {"type": "int", "min": 0, "max": 2000},
    "fuel": {"type": "enum", "values": {"diesel", "benzin", "benzín", "lpg", "elektro", "cng", "hybrid", None}},
    "review_status": {"type": "enum", "values": {"checked", "dismissed", "sold", None}},
}

# Fuel normalization rules (regex pattern -> normalized value)
FUEL_NORMALIZATION = {
    r"benzin.*": "benzin",
    r"lpg.*": "lpg",
    r"diesel.*": "diesel",
    r"nafta.*": "diesel",
    r"elektr.*": "elektro",
    r"electric.*": "elektro",
    r"hybrid.*": "hybrid",
    r"cng.*": "cng",
    r"zemní plyn.*": "cng",
}


def validate_field_value(field: str, value) -> tuple[bool, str]:
    """
    Validate a field value against the rules in EDITABLE_FIELDS.

    Returns (is_valid, error_message).
    """
    if field not in EDITABLE_FIELDS:
        return False, f"Field '{field}' is not editable"

    rules = EDITABLE_FIELDS[field]

    if value is None:
        return True, ""

    if rules["type"] == "int":
        if not isinstance(value, int):
            return False, f"Field '{field}' must be an integer"
        if value < rules["min"] or value > rules["max"]:
            return False, f"Field '{field}' must be between {rules['min']} and {rules['max']}"

    elif rules["type"] == "enum":
        if value not in rules["values"]:
            return False, f"Field '{field}' must be one of {rules['values']}"

    return True, ""


def _recompute_derived_fields(offer: Offer) -> None:
    """Recompute years_in_usage, price_per_km, mileage_per_year after field update."""
    current_year = datetime.now().year

    if offer.year_manufacture:
        offer.years_in_usage = current_year - offer.year_manufacture
    else:
        offer.years_in_usage = None

    if offer.price and offer.mileage and offer.mileage > 0:
        offer.price_per_km = round(offer.price / offer.mileage, 4)
    else:
        offer.price_per_km = None

    if offer.mileage and offer.years_in_usage and offer.years_in_usage > 0:
        offer.mileage_per_year = round(offer.mileage / offer.years_in_usage, 2)
    else:
        offer.mileage_per_year = None


def update_offer_fields(session: Session, offer_id: int,
                        updates: dict) -> Optional[dict]:
    """
    Update one or more fields on an Offer.

    Args:
        session: SQLAlchemy session
        offer_id: ID of the offer to update
        updates: dict of {field_name: new_value}

    Returns:
        Updated offer data dict, or None if not found.

    Raises:
        ValueError: if any field/value is invalid.
    """
    # Validate all fields first
    for field, value in updates.items():
        valid, error = validate_field_value(field, value)
        if not valid:
            raise ValueError(error)

    offer = session.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        return None

    for field, value in updates.items():
        setattr(offer, field, value)

    _recompute_derived_fields(offer)
    session.flush()

    # Return updated data via Car view (has brand/model joined)
    car = session.query(Car).filter(Car.id == offer_id).first()
    return car.serialize() if car else None


def delete_offer(session: Session, offer_id: int) -> bool:
    """
    Delete a single offer.

    Returns True if deleted, False if not found.
    """
    offer = session.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        return False

    session.delete(offer)
    session.flush()
    logger.info("Deleted offer id=%d", offer_id)
    return True


def get_data_quality_summary(session: Session) -> dict:
    """
    Return data completeness stats and anomaly counts.

    Returns dict with per-field completeness percentages and anomaly counts.
    """
    total = session.query(func.count(Car.id)).scalar() or 0
    if total == 0:
        return {"total": 0, "fields": {}, "anomalies": {}}

    fields_to_check = ["year_manufacture", "mileage", "power", "fuel", "price"]
    field_stats = {}

    for field_name in fields_to_check:
        col = getattr(Car, field_name)
        filled = session.query(func.count(Car.id)).filter(col.isnot(None)).scalar()
        field_stats[field_name] = {
            "filled": filled,
            "missing": total - filled,
            "pct": round(filled / total * 100, 1),
        }

    # Anomaly counts
    misplaced_fuel = session.query(func.count(Car.id)).filter(
        Car.fuel.regexp_match("[0-9]")
    ).scalar()

    mileage_outliers = session.query(func.count(Car.id)).filter(
        Car.mileage > 1_000_000
    ).scalar()

    price_outliers = session.query(func.count(Car.id)).filter(
        Car.price > 50_000_000
    ).scalar()

    return {
        "total": total,
        "fields": field_stats,
        "anomalies": {
            "misplaced_fuel": misplaced_fuel,
            "mileage_outliers": mileage_outliers,
            "price_outliers": price_outliers,
        },
    }


def bulk_normalize_fuel(session: Session) -> dict:
    """
    Apply fuel normalization rules. Returns count of affected rows and details.
    """
    details = []
    total_updated = 0

    for pattern, normalized in FUEL_NORMALIZATION.items():
        count = (
            session.query(Offer)
            .filter(Offer.fuel.regexp_match(pattern), Offer.fuel != normalized)
            .update({Offer.fuel: normalized}, synchronize_session="fetch")
        )
        if count > 0:
            details.append({"pattern": pattern, "normalized_to": normalized, "count": count})
            total_updated += count

    session.flush()
    return {"affected": total_updated, "details": details}


def _extract_mileage_from_text(text: str) -> Optional[int]:
    """Extract mileage from text like '111tkm', '150 000 km', etc."""
    if not text:
        return None

    match = re.search(r"(\d+(?:\s?\d+)*)\s*t?km", text.lower())
    if not match:
        return None

    mileage_str = match.group(1).replace(" ", "")
    mileage = int(mileage_str)

    if "tkm" in text.lower():
        mileage *= 1000

    return mileage


def bulk_fix_misplaced(session: Session) -> dict:
    """
    Fix offers where mileage-like values ended up in the fuel field.

    Returns count of affected rows.
    """
    offers = (
        session.query(Offer)
        .filter(Offer.fuel.regexp_match("[0-9]"))
        .all()
    )

    fixed = 0
    for offer in offers:
        extracted = _extract_mileage_from_text(offer.fuel)

        if extracted:
            if offer.mileage is None:
                offer.mileage = extracted
            offer.fuel = None
            _recompute_derived_fields(offer)
            fixed += 1

    session.flush()
    return {"affected": fixed}
