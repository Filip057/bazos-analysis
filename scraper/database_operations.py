from datetime import datetime
import re
import logging
from typing import Optional, Dict

from sqlalchemy.orm import sessionmaker, scoped_session
from database.model import Model, Brand, Offer, engine

# Configure logging
logger = logging.getLogger(__name__)

# Scoped session configuration
Session = scoped_session(sessionmaker(bind=engine))

# Pre-compiled regex for unique_id extraction
UNIQUE_ID_PATTERN = re.compile(r'inzerat/(\d+)/')


"""
Here are functions that i use to operate with database, or somehow related to database
"""

# ── Pre-compiled patterns for check_if_car (compiled once, not per call) ──

# Multi-word phrases checked first (order matters — longer phrases before single words
# to avoid false positives like "na díly" vs standalone "díly")
_NOT_SELLING_PATTERNS = re.compile(
    r'\b(?:koup[ií]m|hled[aá]m|sh[aá]n[ií]m|popt[aá]v[aá]m'
    r'|pronaj[ií]m[aá]m|pron[aá]jem|p[uů]j[čc]ovna)\b',
    re.IGNORECASE,
)

# Phrases that clearly indicate non-car listings (multi-word, checked on heading)
_PARTS_PHRASES = re.compile(
    r'(?:'
    r'na\s+d[ií]ly|n[aá]hradn[ií]\s+d[ií]ly|auto\s*d[ií]ly'
    r'|[čc]eln[ií]\s+sklo|hlava\s+motoru'
    r'|stře[sš]n[ií]\s+nosi[čc]|stře[sš]n[ií]\s+box'
    r'|ta[zž]n[eé]\s+za[rř][ií]zen[ií]'
    r'|zimn[ií]\s+pneu|letn[ií]\s+pneu'
    r'|sada\s+kol|sada\s+disk[uů]|sada\s+pneu'
    r'|na\s+rozborku|rozborka'
    r')',
    re.IGNORECASE,
)

# Wheel/rim spec patterns in heading (e.g., "7,5jx18", "5x112", "R16 sada")
_WHEEL_SPEC_PATTERNS = re.compile(
    r'(?:'
    r'\d+[,.]?\d*\s*[jJ]\s*[xX]\s*\d+'       # "7,5jx18", "6Jx15"
    r'|(?:^|\s)\d+[xX]\d{2,3}(?:\s|$)'        # "5x112", "5x100" (bolt pattern)
    r'|\bR\d{2}\b'                              # "R16", "R18" (rim size)
    r'|\b[rR]?\d{2}"'                           # 18", r17" (inch notation)
    r')',
    re.IGNORECASE,
)

# Description-level patterns (checked on description text, not heading)
_DESC_PARTS_PHRASES = re.compile(
    r'(?:'
    r'na\s+d[ií]ly'                             # "na díly"
    r'|na\s+opravu'                             # "na opravu"
    r'|nem[aá]\s+papíry|bez\s+papír[uů]'       # "nemá papíry", "bez papírů"
    r'|bez\s+TP|nem[aá]\s+TP'                  # "bez TP", "nemá TP"
    r'|bez\s+(?:technick[eé]ho\s+)?pr[uů]kazu' # "bez průkazu", "bez technického průkazu"
    r'|nosn[yý]\s+r[aá]m|[šs]asi'             # "nosný rám", "šasi" (chassis for sale)
    r')',
    re.IGNORECASE,
)

# Heading starts with a component name (selling a part, not a car)
_HEADING_STARTS_WITH_PART = re.compile(
    r'^\s*(?:motor|převodovka|p[rř]evodovka|turbo|kompresor)\s',
    re.IGNORECASE,
)

# Installment/financing listings — price is just a down payment, not real car price
_INSTALLMENT_PATTERNS = re.compile(
    r'(?:'
    r'na\s+spl[aá]tky'                         # "na splátky"
    r'|akontace'                                # "akontace"
    r'|bez\s+nahl[ií][zž]en[ií]'               # "bez nahlížení do registrů"
    r'|spl[aá]tk[yi]\s+(?:dle|od|bez)'         # "splátky dle domluvy", "splátky od 3000"
    r')',
    re.IGNORECASE,
)

# Single keywords that in a heading strongly indicate parts/accessories, not a car.
# Intentionally conservative — only words that almost never appear in real car sale headings.
_PARTS_KEYWORDS = re.compile(
    r'\b(?:'
    # Parts and components
    r'n[aá]razn[ií]k[y]?|blatn[ií]k[y]?|sv[eě]tl[ao]|sv[eě]tla'
    r'|n[aá]prava|lo[zž]isk[oa]|brzd[oy]|desti[čc]k[yi]|kotou[čc][e]?'
    r'|tlumi[čc][e]?|pru[zž]in[ya]'
    r'|p[ií]st[y]?|v[aá]lce|turbodmychadlo'
    r'|v[yý]fuk|katalyz[aá]tor|dpf|egr'
    # Chassis, body parts, interior
    r'|[šs]asi|korb[auye]|nosn[yý]\s+r[aá]m'
    r'|seda[čc]k[yi]|tapec[eiy]|interi[eé]r|potah[y]?'
    # Body kits, bumper sets
    r'|body\s*kit'
    # Camper conversions
    r'|autovestavb[ay]|obytn[aá]\s+vestavb[ay]'
    # Tyres, wheels, discs
    r'|pneumatik[yi]|pneu|disk[yi]|alu\s*kol[ao]?'
    # Non-car vehicles — motorcycles
    r'|motocykl|motorka|motorky|sk[uú]tr|moped'
    # Non-car vehicles — buses
    r'|autobus'
    # Non-car vehicles — tractors, construction, industrial
    r'|traktor[y]?|bagr[y]?|naklada[čc][e]?|rolba'
    r'|vysokozdvi[zž]n[yý]'
    # Non-car vehicles — caravans, trailers
    r'|karavan[y]?|obytn[yý]|obyt[nň][aá]k'
    r'|p[rř][ií]v[eě]s[y]?|p[rř][ií]v[eě]sn[yý]'
    # Non-car vehicles — quads, trikes, golf carts
    r'|[čc]ty[rř]kolk[ay]|t[rř][ií]kolk[ay]'
    r'|golfov[yý]\s+voz[ií]k'
    # Accessories only (not parts of car description)
    r'|autosed[aá][čc]k[au]|kobe[rř]e[čc]k[yi]|potahy'
    # Tyres as standalone listing
    r'|kol[ay]\s*\+\s*gum[yi]'
    # Explicit parts listings
    r'|autodíly|autodily|d[ií]ly'
    r')\b',
    re.IGNORECASE,
)

MIN_CAR_PRICE = 5000
MAX_CAR_PRICE = 50_000_000  # 50M CZK — anything above is clearly fake


def check_if_car(description, heading, price):
    """Check if a listing is probably a real car-for-sale offer.

    Returns True if the listing looks like a genuine car sale.
    Returns False for parts, accessories, "looking to buy", rentals, etc.
    """
    if price is None or price < MIN_CAR_PRICE or price > MAX_CAR_PRICE:
        return False

    if not heading:
        return False

    # Check heading for "buying" intent (not selling)
    if _NOT_SELLING_PATTERNS.search(heading):
        return False

    # Check heading for parts phrases (multi-word, high confidence)
    if _PARTS_PHRASES.search(heading):
        return False

    # Check heading for parts keywords (single words, conservative list)
    if _PARTS_KEYWORDS.search(heading):
        return False

    # Heading starts with a component name (e.g., "Motor Octavia III 1.6")
    if _HEADING_STARTS_WITH_PART.search(heading):
        return False

    # Wheel/rim specs in heading (e.g., "7,5jx18 5x112 Škoda Luna")
    if _WHEEL_SPEC_PATTERNS.search(heading):
        return False

    # Description-level checks (na díly, nemá papíry, etc.)
    if description and _DESC_PARTS_PHRASES.search(description):
        return False

    # Installment sales — listed price is just a down payment, skews statistics
    if description and _INSTALLMENT_PATTERNS.search(description):
        return False
    if _INSTALLMENT_PATTERNS.search(heading):
        return False

    return True

def validate_year(year_manufacture: int) -> Optional[int]:
    """Validate year of manufacture before DB insert.

    Returns the year if valid, None otherwise.
    Rejects future years and anything before 1900.
    """
    if year_manufacture is None:
        return None
    current_year = datetime.now().year
    if 1900 <= year_manufacture <= current_year:
        return year_manufacture
    logger.warning("Rejected invalid year_manufacture=%s", year_manufacture)
    return None


def validate_mileage(mileage) -> Optional[int]:
    """Validate mileage before DB insert.

    Returns mileage if plausible, None otherwise.
    """
    if mileage is None:
        return None
    try:
        mileage = int(mileage)
    except (TypeError, ValueError):
        return None
    if 0 < mileage <= 1_500_000:
        return mileage
    logger.warning("Rejected invalid mileage=%s", mileage)
    return None


def validate_power(power) -> Optional[int]:
    """Validate engine power (kW) before DB insert.

    Returns power if plausible, None otherwise.
    """
    if power is None:
        return None
    try:
        power = int(power)
    except (TypeError, ValueError):
        return None
    if 0 < power <= 1500:
        return power
    logger.warning("Rejected invalid power=%s", power)
    return None


def validate_price(price) -> Optional[int]:
    """Validate price (CZK) before DB insert.

    Returns price if plausible, None otherwise.
    Rejects negative, zero, and extreme outlier prices.
    """
    if price is None:
        return None
    try:
        price = int(price)
    except (TypeError, ValueError):
        return None
    if 0 < price <= 50_000_000:
        return price
    logger.warning("Rejected invalid price=%s", price)
    return None


def compute_derived_metrics(price, mileage, year_manufacture):
    """Compute derived metrics from validated inputs."""
    current_year = datetime.now().year
    year_manufacture = validate_year(year_manufacture)
    mileage = validate_mileage(mileage)
    price = validate_price(price)
    years_in_usage = current_year - year_manufacture if year_manufacture else None
    price_per_km = price / mileage if price and mileage and mileage > 0 else None
    mileage_per_year = mileage / years_in_usage if mileage and years_in_usage and years_in_usage > 0 else None
    return years_in_usage, price_per_km, mileage_per_year

# Cache for model lookups to avoid repeated database queries
_model_cache: Dict[tuple, Optional[int]] = {}


def get_model_id_sync(session, brand_name: str, model_name: Optional[str]) -> Optional[int]:
    """Synchronous model ID lookup with auto-create for missing brands/models."""
    if not model_name:
        return None

    brand_name = brand_name.lower().strip()
    model_name = model_name.lower().strip()

    # Check cache first
    cache_key = (brand_name, model_name)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    # Query or create brand
    brand = session.query(Brand).filter(Brand.name.ilike(brand_name)).first()
    if not brand:
        brand = Brand(name=brand_name)
        session.add(brand)
        session.flush()
        logger.info("Auto-created brand: %s", brand_name)

    # Query or create model
    model = session.query(Model).filter(Model.name.ilike(model_name), Model.brand_id == brand.id).first()
    if not model:
        model = Model(name=model_name, brand_id=brand.id)
        session.add(model)
        session.flush()
        logger.info("Auto-created model: %s / %s", brand_name, model_name)

    _model_cache[cache_key] = model.id
    return model.id



