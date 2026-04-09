from contextlib import contextmanager
import logging

from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_restful import Api, Resource
from flask_cors import CORS
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from datetime import datetime

from database.model import Base, Car, Offer, Admin, init_database
from webapp.config import get_config
from webapp.deal_detection import find_deals, score_single_offer, find_suspicious
from webapp.auth import (
    admin_required, hash_password, verify_password, issue_token,
)
from database.admin_operations import (
    update_offer_fields, delete_offer, get_data_quality_summary,
    bulk_normalize_fuel, bulk_fix_misplaced, EDITABLE_FIELDS,
)
from scraper.scrape_service import ScrapeJobManager

# Sanity bounds for filtering outliers in statistics
MAX_REASONABLE_MILEAGE = 1_000_000  # km
MAX_REASONABLE_PRICE = 50_000_000   # CZK
MAX_PRICE_PER_KM = 500.0           # CZK/km — above this is likely bad data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

app = Flask(__name__)
app.config.from_object(config)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# CORS with restricted origins
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT],
    storage_uri=config.RATELIMIT_STORAGE_URL,
    enabled=config.RATELIMIT_ENABLED
)

# Connect to the database
engine = create_engine(
    config.DATABASE_URI,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=config.DEBUG
)
Base.metadata.bind = engine

# Create scoped session factory
DBSession = scoped_session(sessionmaker(bind=engine))


@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup."""
    session = DBSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        DBSession.remove()


# =============================================================================
# AUTH — admin login (JWT, 24h tokens)
# =============================================================================

@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
@csrf.exempt
def api_auth_login():
    """
    Authenticate an admin and return a JWT.

    JSON body: {"username": "...", "password": "..."}
    On success: {"token": "...", "username": "...", "expires_in": 86400}
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    try:
        with get_db_session() as session:
            admin = session.query(Admin).filter(Admin.username == username).first()
            if not admin or not verify_password(password, admin.password_hash):
                # Same error for both cases — don't leak which one is wrong
                return jsonify({"error": "Invalid credentials"}), 401

            admin.last_login = datetime.utcnow()
            token = issue_token(admin.id, admin.username)
            return jsonify({
                "token": token,
                "username": admin.username,
                "expires_in": 24 * 3600,
            })
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_auth_login: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/auth/me")
@limiter.limit("60 per minute")
@admin_required
def api_auth_me():
    """Return the currently authenticated admin (verifies token)."""
    payload = request.admin  # type: ignore[attr-defined]
    return jsonify({"username": payload.get("username"), "id": payload.get("sub")})


@app.route("/health")
def health():
    """Lightweight liveness probe — does not touch the database."""
    return jsonify({"status": "ok"}), 200


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """Analytics dashboard - Module 1: Overview"""
    return render_template("dashboard.html")


# =============================================================================
# DROPDOWN API — brands & models for forms
# =============================================================================

@app.route("/api/brands")
@limiter.limit("60 per minute")
def api_brands():
    """List all brands that have at least one offer."""
    try:
        with get_db_session() as session:
            rows = (
                session.query(Car.brand)
                .filter(Car.brand.isnot(None))
                .distinct()
                .order_by(Car.brand)
                .all()
            )
            return jsonify([r.brand for r in rows])
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_brands: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/models/<string:brand>")
@limiter.limit("60 per minute")
def api_models(brand):
    """List all models for a given brand that have at least one offer."""
    try:
        with get_db_session() as session:
            rows = (
                session.query(Car.model)
                .filter(Car.brand == brand, Car.model.isnot(None))
                .distinct()
                .order_by(Car.model)
                .all()
            )
            return jsonify([r.model for r in rows])
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_models: {e}")
        return jsonify({"error": "Database error"}), 500


# =============================================================================
# ANALYTICS API  — Module 1: Overview
# =============================================================================

@app.route("/api/stats/overview")
@limiter.limit("60 per minute")
def stats_overview():
    """
    High-level DB summary.

    Returns total cars, brands, averages, and data completeness.
    """
    try:
        with get_db_session() as session:
            total_cars = session.query(Car).count()

            if total_cars == 0:
                return jsonify({
                    "total_cars": 0,
                    "total_brands": 0,
                    "total_models": 0,
                    "avg_price": None,
                    "avg_mileage": None,
                    "avg_year": None,
                    "complete_data_pct": 0,
                    "last_scraped": None,
                })

            total_brands = session.query(Car.brand).distinct().count()
            total_models = session.query(Car.brand, Car.model).distinct().count()

            avg_price = session.query(func.avg(Car.price)).filter(
                Car.price > 0, Car.price < MAX_REASONABLE_PRICE
            ).scalar()
            avg_mileage = session.query(func.avg(Car.mileage)).filter(
                Car.mileage > 0, Car.mileage < MAX_REASONABLE_MILEAGE
            ).scalar()
            avg_year = session.query(func.avg(Car.year_manufacture)).scalar()

            # Cars with complete core data
            complete = session.query(Car).filter(
                Car.mileage.isnot(None),
                Car.year_manufacture.isnot(None),
                Car.price.isnot(None),
            ).count()

            # Last scrape time
            last_scraped = session.query(func.max(Car.scraped_at)).scalar()

            return jsonify({
                "total_cars": total_cars,
                "total_brands": total_brands,
                "total_models": total_models,
                "avg_price": round(float(avg_price)) if avg_price else None,
                "avg_mileage": round(float(avg_mileage)) if avg_mileage else None,
                "avg_year": round(float(avg_year), 1) if avg_year else None,
                "complete_data_pct": round(complete / total_cars * 100, 1),
                "last_scraped": last_scraped.isoformat() if last_scraped else None,
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_overview: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/brands")
@limiter.limit("60 per minute")
def stats_brands():
    """
    Per-brand statistics: count, avg price, avg mileage, avg year.

    Query params:
        limit (int): max brands to return (default 24, max 50)
    """
    try:
        limit = min(request.args.get("limit", 24, type=int), 50)

        with get_db_session() as session:
            # Use conditional averages to exclude outliers
            avg_price_expr = func.avg(
                func.IF(
                    (Car.price > 0) & (Car.price < MAX_REASONABLE_PRICE),
                    Car.price, None
                )
            )
            avg_mileage_expr = func.avg(
                func.IF(
                    (Car.mileage > 0) & (Car.mileage < MAX_REASONABLE_MILEAGE),
                    Car.mileage, None
                )
            )
            avg_price_per_km_expr = func.avg(
                func.IF(
                    (Car.price_per_km > 0) & (Car.price_per_km < MAX_PRICE_PER_KM),
                    Car.price_per_km, None
                )
            )

            rows = (
                session.query(
                    Car.brand,
                    func.count(Car.id).label("count"),
                    avg_price_expr.label("avg_price"),
                    avg_mileage_expr.label("avg_mileage"),
                    func.avg(Car.year_manufacture).label("avg_year"),
                    avg_price_per_km_expr.label("avg_price_per_km"),
                )
                .filter(Car.brand.isnot(None))
                .group_by(Car.brand)
                .order_by(func.count(Car.id).desc())
                .limit(limit)
                .all()
            )

            return jsonify([
                {
                    "brand": r.brand,
                    "count": r.count,
                    "avg_price": round(float(r.avg_price)) if r.avg_price else None,
                    "avg_mileage": round(float(r.avg_mileage)) if r.avg_mileage else None,
                    "avg_year": round(float(r.avg_year), 1) if r.avg_year else None,
                    "avg_price_per_km": round(float(r.avg_price_per_km), 2) if r.avg_price_per_km else None,
                }
                for r in rows
            ])

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_brands: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/models")
@limiter.limit("60 per minute")
def stats_models():
    """
    Per-model statistics for a given brand.

    Query params:
        brand (str): required
        limit (int): default 20
    """
    brand = request.args.get("brand")
    if not brand:
        return jsonify({"error": "brand parameter is required"}), 400

    try:
        limit = min(request.args.get("limit", 20, type=int), 100)

        with get_db_session() as session:
            avg_price_expr = func.avg(
                func.IF(
                    (Car.price > 0) & (Car.price < MAX_REASONABLE_PRICE),
                    Car.price, None
                )
            )
            avg_mileage_expr = func.avg(
                func.IF(
                    (Car.mileage > 0) & (Car.mileage < MAX_REASONABLE_MILEAGE),
                    Car.mileage, None
                )
            )
            avg_price_per_km_expr = func.avg(
                func.IF(
                    (Car.price_per_km > 0) & (Car.price_per_km < MAX_PRICE_PER_KM),
                    Car.price_per_km, None
                )
            )

            rows = (
                session.query(
                    Car.model,
                    func.count(Car.id).label("count"),
                    avg_price_expr.label("avg_price"),
                    avg_mileage_expr.label("avg_mileage"),
                    func.avg(Car.year_manufacture).label("avg_year"),
                    avg_price_per_km_expr.label("avg_price_per_km"),
                )
                .filter(Car.brand == brand, Car.model.isnot(None))
                .group_by(Car.model)
                .order_by(func.count(Car.id).desc())
                .limit(limit)
                .all()
            )

            return jsonify({
                "brand": brand,
                "models": [
                    {
                        "model": r.model,
                        "count": r.count,
                        "avg_price": round(float(r.avg_price)) if r.avg_price else None,
                        "avg_mileage": round(float(r.avg_mileage)) if r.avg_mileage else None,
                        "avg_year": round(float(r.avg_year), 1) if r.avg_year else None,
                        "avg_price_per_km": round(float(r.avg_price_per_km), 2) if r.avg_price_per_km else None,
                    }
                    for r in rows
                ]
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_models: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/year-distribution")
@limiter.limit("30 per minute")
def stats_year_distribution():
    """
    Count of cars by year of manufacture.

    Query params:
        brand (str): optional filter
        model (str): optional filter
    """
    try:
        brand = request.args.get("brand")
        model = request.args.get("model")

        with get_db_session() as session:
            query = (
                session.query(
                    Car.year_manufacture,
                    func.count(Car.id).label("count"),
                )
                .filter(Car.year_manufacture.isnot(None))
                .filter(Car.year_manufacture >= 1985)
            )

            if brand:
                query = query.filter(Car.brand == brand)
            if model:
                query = query.filter(Car.model == model)

            rows = query.group_by(Car.year_manufacture).order_by(Car.year_manufacture).all()

            return jsonify({
                "brand": brand,
                "model": model,
                "data": [{"year": r.year_manufacture, "count": r.count} for r in rows],
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_year_distribution: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/fuel-distribution")
@limiter.limit("30 per minute")
def stats_fuel_distribution():
    """
    Count of cars by fuel type.

    Query params:
        brand (str): optional filter
    """
    try:
        brand = request.args.get("brand")

        with get_db_session() as session:
            query = (
                session.query(
                    Car.fuel,
                    func.count(Car.id).label("count"),
                )
                .filter(Car.fuel.isnot(None))
            )

            if brand:
                query = query.filter(Car.brand == brand)

            rows = query.group_by(Car.fuel).order_by(func.count(Car.id).desc()).all()

            return jsonify({
                "brand": brand,
                "data": [{"fuel": r.fuel, "count": r.count} for r in rows],
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_fuel_distribution: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/price-distribution")
@limiter.limit("30 per minute")
def stats_price_distribution():
    """
    Price histogram with configurable bucket size.

    Query params:
        brand (str): optional
        model (str): optional
        bucket (int): bucket size in CZK (default 50000)
    """
    try:
        brand = request.args.get("brand")
        model = request.args.get("model")
        bucket = request.args.get("bucket", 50000, type=int)
        bucket = max(min(bucket, 500000), 10000)  # clamp 10k–500k

        with get_db_session() as session:
            query = session.query(Car.price).filter(
                Car.price.isnot(None),
                Car.price > 0,
                Car.price < 5_000_000,   # exclude outliers
            )
            if brand:
                query = query.filter(Car.brand == brand)
            if model:
                query = query.filter(Car.model == model)

            prices = [row[0] for row in query.all()]

        if not prices:
            return jsonify({"brand": brand, "model": model, "bucket": bucket, "data": []})

        # Build histogram manually (no numpy dependency)
        min_price = (min(prices) // bucket) * bucket
        max_price = ((max(prices) // bucket) + 1) * bucket
        buckets: dict = {}
        for b in range(min_price, max_price, bucket):
            buckets[b] = 0
        for p in prices:
            b = (p // bucket) * bucket
            buckets[b] = buckets.get(b, 0) + 1

        return jsonify({
            "brand": brand,
            "model": model,
            "bucket_size": bucket,
            "data": [
                {"price_from": k, "price_to": k + bucket, "count": v}
                for k, v in sorted(buckets.items())
                if v > 0
            ],
        })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_price_distribution: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/stats/scatter")
@limiter.limit("30 per minute")
def stats_scatter():
    """
    Scatter plot data: individual (mileage, price) points for a brand/model.

    Query params:
        brand (str): required
        model (str): optional — if omitted, returns all models for brand
        limit (int): max points (default 500, max 2000)
    """
    brand = request.args.get("brand")
    if not brand:
        return jsonify({"error": "brand parameter is required"}), 400

    try:
        model = request.args.get("model")
        limit = min(request.args.get("limit", 500, type=int), 2000)

        with get_db_session() as session:
            query = session.query(
                Car.model, Car.price, Car.mileage, Car.year_manufacture
            ).filter(
                Car.brand == brand,
                Car.price.isnot(None),
                Car.price > 0,
                Car.price < MAX_REASONABLE_PRICE,
                Car.mileage.isnot(None),
                Car.mileage > 0,
                Car.mileage < MAX_REASONABLE_MILEAGE,
            )

            if model:
                query = query.filter(Car.model == model)

            rows = query.order_by(func.rand()).limit(limit).all()

            return jsonify({
                "brand": brand,
                "model": model,
                "count": len(rows),
                "data": [
                    {
                        "model": r.model,
                        "price": r.price,
                        "mileage": r.mileage,
                        "year": r.year_manufacture,
                    }
                    for r in rows
                ],
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in stats_scatter: {e}")
        return jsonify({"error": "Database error"}), 500


# =============================================================================
# ADMIN BROWSER — data browsing, editing, and quality tools
# =============================================================================

@app.route("/admin/browser")
def admin_browser():
    """Data browser and admin tool."""
    return render_template("admin-browser.html")


@app.route("/admin/suspicious")
def suspicious_page():
    """Suspicious offers browser — likely data errors."""
    return render_template("suspicious.html")


@app.route("/api/admin/suspicious")
@limiter.limit("30 per minute")
@admin_required
def api_admin_suspicious():
    """
    Find offers that look like deals but are likely data errors.

    Query params:
        brand (str): optional filter
        model (str): optional filter
        min_score (float): minimum deal score (default 25)
        page (int): page number (default 1)
        per_page (int): results per page (default 50, max 100)
        hide_reviewed (int): 1 (default) to hide checked/dismissed offers, 0 to show all
    """
    try:
        brand = request.args.get("brand")
        model = request.args.get("model")
        min_score = request.args.get("min_score", 25, type=float)
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 50, type=int), 1), 100)
        hide_reviewed = request.args.get("hide_reviewed", 1, type=int) == 1

        with get_db_session() as session:
            result = find_suspicious(
                session,
                brand=brand,
                model=model,
                min_score=min_score,
                limit=per_page,
                offset=(page - 1) * per_page,
                hide_reviewed=hide_reviewed,
            )
            return jsonify(result)

    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_suspicious: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/offers")
@limiter.limit("60 per minute")
@admin_required
def api_admin_offers():
    """
    Paginated offer browser with filters.

    Query params:
        brand, model, fuel (str): exact match filters ('null' = filter for NULL)
        year_from, year_to (int): year range
        mileage_from, mileage_to (int): mileage range
        price_from, price_to (int): price range
        missing (str): comma-separated field names to filter for NULL
        sort (str): field to sort by (default 'id')
        sort_dir (str): 'asc' or 'desc' (default 'desc')
        page, per_page (int): pagination
    """
    try:
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)

        with get_db_session() as session:
            query = session.query(Car)

            # String filters (support 'null' for NULL filtering)
            for param in ("brand", "model", "fuel"):
                val = request.args.get(param)
                if val == "null":
                    query = query.filter(getattr(Car, param).is_(None))
                elif val:
                    query = query.filter(getattr(Car, param) == val)

            # Range filters
            range_filters = {
                "year": "year_manufacture",
                "mileage": "mileage",
                "price": "price",
            }
            for prefix, col_name in range_filters.items():
                col = getattr(Car, col_name)
                val_from = request.args.get(f"{prefix}_from", type=int)
                val_to = request.args.get(f"{prefix}_to", type=int)
                if val_from is not None:
                    query = query.filter(col >= val_from)
                if val_to is not None:
                    query = query.filter(col <= val_to)

            # Missing fields filter
            missing = request.args.get("missing", "")
            if missing:
                for field_name in missing.split(","):
                    field_name = field_name.strip()
                    if hasattr(Car, field_name):
                        query = query.filter(getattr(Car, field_name).is_(None))

            # Sorting
            sort_field = request.args.get("sort", "id")
            sort_dir = request.args.get("sort_dir", "desc")
            if hasattr(Car, sort_field):
                col = getattr(Car, sort_field)
                query = query.order_by(col.asc() if sort_dir == "asc" else col.desc())
            else:
                query = query.order_by(Car.id.desc())

            total = query.count()
            rows = query.offset((page - 1) * per_page).limit(per_page).all()

            return jsonify({
                "offers": [r.serialize() for r in rows],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page if per_page else 1,
                },
            })

    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_offers: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/offers/<int:offer_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@csrf.exempt
@admin_required
def api_admin_update_offer(offer_id: int):
    """
    Update one or more fields on an offer.

    JSON body: {"year_manufacture": 2015, "fuel": "diesel", ...}
    Only whitelisted fields are accepted.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        # Filter to only editable fields
        updates = {k: v for k, v in data.items() if k in EDITABLE_FIELDS}
        if not updates:
            return jsonify({"error": f"No valid fields. Editable: {list(EDITABLE_FIELDS.keys())}"}), 400

        with get_db_session() as session:
            result = update_offer_fields(session, offer_id, updates)
            if result is None:
                return jsonify({"error": "Offer not found"}), 404
            return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_update_offer: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/offers/<int:offer_id>", methods=["DELETE"])
@limiter.limit("10 per minute")
@csrf.exempt
@admin_required
def api_admin_delete_offer(offer_id: int):
    """Delete a single junk offer."""
    try:
        with get_db_session() as session:
            if delete_offer(session, offer_id):
                return jsonify({"ok": True})
            return jsonify({"error": "Offer not found"}), 404

    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_delete_offer: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/quality/summary")
@limiter.limit("30 per minute")
@admin_required
def api_admin_quality_summary():
    """Data completeness stats and anomaly counts."""
    try:
        with get_db_session() as session:
            return jsonify(get_data_quality_summary(session))
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_quality_summary: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/quality/normalize-fuel", methods=["POST"])
@limiter.limit("5 per minute")
@csrf.exempt
@admin_required
def api_admin_normalize_fuel():
    """Run bulk fuel normalization."""
    try:
        with get_db_session() as session:
            result = bulk_normalize_fuel(session)
            return jsonify(result)
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_normalize_fuel: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/admin/quality/fix-misplaced", methods=["POST"])
@limiter.limit("5 per minute")
@csrf.exempt
@admin_required
def api_admin_fix_misplaced():
    """Run bulk misplaced value fix."""
    try:
        with get_db_session() as session:
            result = bulk_fix_misplaced(session)
            return jsonify(result)
    except SQLAlchemyError as e:
        logger.error(f"DB error in api_admin_fix_misplaced: {e}")
        return jsonify({"error": "Database error"}), 500


# =============================================================================
# SCRAPING CONTROL — admin-triggered scraping with background threading
# =============================================================================

scrape_manager = ScrapeJobManager()


@app.route("/admin/scraping")
def admin_scraping_page():
    """Scraping control panel (admin-only, enforced client-side)."""
    return render_template("admin-scraping.html")


@app.route("/api/admin/scrape/start", methods=["POST"])
@limiter.limit("5 per minute")
@csrf.exempt
@admin_required
def api_admin_scrape_start():
    """
    Start a new scraping job in a background thread.

    JSON body: {"brands": ["skoda", "volkswagen"]} or omit for all brands.
    Returns 202 on success, 409 if a job is already running.
    """
    data = request.get_json(silent=True) or {}
    brands = data.get("brands")

    # Normalize: list of strings or None for all
    if isinstance(brands, str):
        brands = [brands]
    if brands and not isinstance(brands, list):
        return jsonify({"error": "brands must be a list of strings or omitted for all"}), 400

    result = scrape_manager.start_job(brands=brands)
    if result is None:
        return jsonify({"error": "A scraping job is already running"}), 409

    return jsonify(result), 202


@app.route("/api/admin/scrape/status")
@limiter.limit("60 per minute")
@admin_required
def api_admin_scrape_status():
    """Return the current or most recent active scraping job status."""
    job_id = request.args.get("job_id")
    if job_id:
        job = scrape_manager.get_job_status(job_id)
    else:
        job = scrape_manager.get_active_job()
    return jsonify({"job": job})


@app.route("/api/admin/scrape/cancel", methods=["POST"])
@limiter.limit("10 per minute")
@csrf.exempt
@admin_required
def api_admin_scrape_cancel():
    """Cancel a running scraping job."""
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id", "")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    if scrape_manager.cancel_job(job_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Job not found or not running"}), 404


@app.route("/api/admin/scrape/history")
@limiter.limit("30 per minute")
@admin_required
def api_admin_scrape_history():
    """Return recent scrape job history."""
    limit = min(request.args.get("limit", 20, type=int), 50)
    return jsonify({"jobs": scrape_manager.get_job_history(limit=limit)})


@app.route("/api/admin/scrape/db-stats")
@limiter.limit("30 per minute")
@admin_required
def api_admin_scrape_db_stats():
    """Return offer counts per brand and totals."""
    return jsonify(scrape_manager.get_db_stats())


@app.route('/car-compare')
def car_comparison():
    return render_template('car-compare.html')


@app.route("/deals")
def deals_page():
    """Underpriced offers browser."""
    return render_template("deals.html")


# =============================================================================
# DEALS API — underpriced offer detection
# =============================================================================

@app.route("/api/deals")
@limiter.limit("30 per minute")
def api_deals():
    """
    Find underpriced offers compared to their market segment.

    Query params:
        brand (str): optional filter
        model (str): optional filter
        fuel (str): optional filter
        min_score (float): minimum deal score % (default 15)
        page (int): page number (default 1)
        per_page (int): results per page (default 20, max 100)
    """
    try:
        brand = request.args.get("brand")
        model = request.args.get("model")
        fuel = request.args.get("fuel")
        min_score = request.args.get("min_score", 15, type=float)
        confidence = request.args.get("confidence")  # high, medium, or empty for all
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)

        with get_db_session() as session:
            result = find_deals(
                session,
                brand=brand,
                model=model,
                fuel=fuel,
                min_score=min_score,
                limit=per_page,
                offset=(page - 1) * per_page,
                min_confidence=confidence,
            )
            return jsonify(result)

    except SQLAlchemyError as e:
        logger.error(f"DB error in api_deals: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route("/api/deals/<int:car_id>")
@limiter.limit("60 per minute")
def api_deal_detail(car_id: int):
    """
    Deal analysis for a single offer against its market segment.

    Returns deal score, median price, quartiles, and segment size.
    """
    try:
        with get_db_session() as session:
            result = score_single_offer(session, car_id)
            if result is None:
                return jsonify({"error": "Car not found or not enough comparable data"}), 404
            return jsonify(result)

    except SQLAlchemyError as e:
        logger.error(f"DB error in api_deal_detail: {e}")
        return jsonify({"error": "Database error"}), 500


# ------  FORM CLASS ----------

class CarComparisonForm(FlaskForm):
    brand = StringField('Brand', validators=[DataRequired()])
    model = StringField('Model', validators=[DataRequired()])
    price = IntegerField('Price (CZK)', validators=[DataRequired(), NumberRange(min=1, max=100000000)])
    year = IntegerField('Year', validators=[Optional(), NumberRange(min=1900, max=2030)])
    y_plusminus = IntegerField('Year Plus/Minus', validators=[Optional(), NumberRange(min=0, max=50)])
    mileage = IntegerField('Mileage', validators=[Optional(), NumberRange(min=0, max=10000000)])
    m_pct_plusminus = IntegerField('Mileage Percentage Plus/Minus', validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField('Compare')


# -------------------
    
class CarListApi(Resource):
    decorators = [limiter.limit("30 per minute")]

    def get(self):
        """Get list of cars with pagination"""
        try:
            # Get pagination parameters with validation
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', config.DEFAULT_PAGE_SIZE, type=int)

            # Validate pagination parameters
            if page < 1:
                return {'error': 'Page must be >= 1'}, 400
            if per_page < 1 or per_page > config.MAX_PAGE_SIZE:
                return {'error': f'per_page must be between 1 and {config.MAX_PAGE_SIZE}'}, 400

            with get_db_session() as session:
                # Get total count
                total = session.query(Car).count()

                # Get paginated results
                cars = session.query(Car)\
                    .offset((page - 1) * per_page)\
                    .limit(per_page)\
                    .all()

                return {
                    'cars': [car.serialize() for car in cars],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
        except SQLAlchemyError as e:
            logger.error(f"Database error in CarListApi: {e}")
            return {'error': 'Database error occurred'}, 500
        except Exception as e:
            logger.error(f"Unexpected error in CarListApi: {e}")
            return {'error': 'An unexpected error occurred'}, 500


class CarApi(Resource):
    decorators = [limiter.limit("60 per minute")]

    def get(self, car_id):
        """Get a specific car by ID"""
        try:
            # Validate car_id
            if car_id < 1:
                return {'error': 'Invalid car ID'}, 400

            with get_db_session() as session:
                car = session.query(Car).filter_by(id=car_id).one()
                return car.serialize()

        except NoResultFound:
            return {'error': 'Car not found'}, 404
        except SQLAlchemyError as e:
            logger.error(f"Database error in CarApi: {e}")
            return {'error': 'Database error occurred'}, 500
        except Exception as e:
            logger.error(f"Unexpected error in CarApi: {e}")
            return {'error': 'An unexpected error occurred'}, 500


class CarStatApi(Resource):
    decorators = [limiter.limit("60 per minute")]

    def get(self, brand, model):
        """Get statistics for cars by brand and model"""
        try:
            # Validate input parameters
            if not brand or not model:
                return {'error': 'Brand and model are required'}, 400

            # Validate optional filters
            year_from = request.args.get('year_from', type=int)
            year_to = request.args.get('year_to', type=int)
            mileage_from = request.args.get('mileage_from', type=int)
            mileage_to = request.args.get('mileage_to', type=int)

            # Validate year ranges
            if year_from and (year_from < 1900 or year_from > 2030):
                return {'error': 'year_from must be between 1900 and 2030'}, 400
            if year_to and (year_to < 1900 or year_to > 2030):
                return {'error': 'year_to must be between 1900 and 2030'}, 400
            if year_from and year_to and year_from > year_to:
                return {'error': 'year_from must be <= year_to'}, 400

            # Validate mileage ranges
            if mileage_from and mileage_from < 0:
                return {'error': 'mileage_from must be >= 0'}, 400
            if mileage_to and mileage_to < 0:
                return {'error': 'mileage_to must be >= 0'}, 400
            if mileage_from and mileage_to and mileage_from > mileage_to:
                return {'error': 'mileage_from must be <= mileage_to'}, 400

            with get_db_session() as session:
                # Base query
                query = session.query(
                    func.avg(Car.price).label('average_price'),
                    func.max(Car.price).label('highest_price'),
                    func.min(Car.price).label('lowest_price'),
                    func.count(Car.id).label('count')
                )

                # Filter by brand and model
                query = query.filter(Car.brand == brand, Car.model == model)

                # Apply optional filters
                if year_from:
                    query = query.filter(Car.year_manufacture >= year_from)
                if year_to:
                    query = query.filter(Car.year_manufacture <= year_to)
                if mileage_from:
                    query = query.filter(Car.mileage >= mileage_from)
                if mileage_to:
                    query = query.filter(Car.mileage <= mileage_to)

                # Execute the query
                result = query.one()

                # Check if any cars found
                if result.count == 0:
                    return {
                        'brand': brand,
                        'model': model,
                        'message': 'No cars found matching the criteria',
                        'stats': None
                    }, 404

                # Format the response
                response = {
                    'average_price': float(result.average_price) if result.average_price else None,
                    'highest_price': float(result.highest_price) if result.highest_price else None,
                    'lowest_price': float(result.lowest_price) if result.lowest_price else None,
                    'count': result.count
                }

                return {'brand': brand, 'model': model, 'stats': response}

        except SQLAlchemyError as e:
            logger.error(f"Database error in CarStatApi: {e}")
            return {'error': 'Database error occurred'}, 500
        except Exception as e:
            logger.error(f"Unexpected error in CarStatApi: {e}")
            return {'error': 'An unexpected error occurred'}, 500


class CarCompareApi(Resource):
    decorators = [limiter.limit("30 per minute")]

    def get(self, brand, model, price):
        """Compare car price against similar offers"""
        try:
            # Validate input
            if not brand or not model:
                return {'error': 'Brand and model are required'}, 400
            if price < 1:
                return {'error': 'Price must be greater than 0'}, 400

            # Get and validate optional parameters
            year = request.args.get('year', type=int)
            y_plusminus = request.args.get('y_plusminus', type=int)
            mileage = request.args.get('mileage', type=int)
            m_pct_plusminus = request.args.get('m_pct_plusminus', type=int)

            # Validate year parameters
            if year and (year < 1900 or year > 2030):
                return {'error': 'Year must be between 1900 and 2030'}, 400
            if y_plusminus and (y_plusminus < 0 or y_plusminus > 50):
                return {'error': 'y_plusminus must be between 0 and 50'}, 400

            # Validate mileage parameters
            if mileage and mileage < 0:
                return {'error': 'Mileage must be >= 0'}, 400
            if m_pct_plusminus and (m_pct_plusminus < 0 or m_pct_plusminus > 100):
                return {'error': 'm_pct_plusminus must be between 0 and 100'}, 400

            with get_db_session() as session:
                # Filter cars by brand and model
                cars_query = session.query(Car).filter_by(brand=brand, model=model)

                # Apply year filter if provided
                if year and y_plusminus is not None:
                    y_plus = year + y_plusminus
                    y_minus = year - y_plusminus
                    cars_query = cars_query.filter(Car.year_manufacture.between(y_minus, y_plus))

                # Apply mileage filter if provided
                # BUG FIX: Changed from 'y_plusminus' to 'm_pct_plusminus'
                if mileage and m_pct_plusminus is not None:
                    m_plus = int(mileage * ((100 + m_pct_plusminus) / 100))
                    m_minus = int(mileage * ((100 - m_pct_plusminus) / 100))
                    cars_query = cars_query.filter(Car.mileage.between(m_minus, m_plus))

                # Calculate the percentile
                count_cars = cars_query.count()

                # BUG FIX: Handle division by zero
                if count_cars == 0:
                    return {
                        'error': 'No similar cars found for comparison',
                        'message': 'Try adjusting your search criteria',
                        'brand': brand,
                        'model': model,
                        'filters_applied': {
                            'year_range': f"{y_minus}-{y_plus}" if year and y_plusminus is not None else None,
                            'mileage_range': f"{m_minus}-{m_plus}" if mileage and m_pct_plusminus is not None else None
                        }
                    }, 404

                count_lower_price = cars_query.filter(Car.price < price).count()
                percentile = (count_lower_price / count_cars) * 100

                return {
                    'message': f"Your offer is more expensive than {percentile:.2f}% of similar car offers.",
                    'percentile': percentile,
                    'total_similar_cars': count_cars,
                    'cars_cheaper': count_lower_price,
                    'cars_more_expensive': count_cars - count_lower_price,
                    'filters_applied': {
                        'year_range': f"{y_minus}-{y_plus}" if year and y_plusminus is not None else None,
                        'mileage_range': f"{m_minus}-{m_plus}" if mileage and m_pct_plusminus is not None else None
                    }
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error in CarCompareApi: {e}")
            return {'error': 'Database error occurred'}, 500
        except Exception as e:
            logger.error(f"Unexpected error in CarCompareApi: {e}")
            return {'error': 'An unexpected error occurred'}, 500

# Register API resources
api = Api(app)

api.add_resource(CarListApi, '/api/cars')
api.add_resource(CarApi, '/api/cars/<int:car_id>')
api.add_resource(CarStatApi, '/api/car-stats/<string:brand>/<string:model>')
api.add_resource(CarCompareApi, '/api/car-compare/<string:brand>/<string:model>/<int:price>')


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429


# Teardown handler to remove session
@app.teardown_appcontext
def shutdown_session(exception=None):
    DBSession.remove()


# Initialize database tables
try:
    init_database()
    logger.info("✓ Database initialized")
except Exception as e:
    logger.warning(f"Database initialization failed: {e}")
    logger.warning("App will start but database operations may fail")


if __name__ == '__main__':
    app.run(debug=config.DEBUG)
    