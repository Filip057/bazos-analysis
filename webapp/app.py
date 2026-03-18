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

from database.model import Base, Car, init_database
from webapp.config import get_config

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
    """Context manager for database sessions with automatic cleanup"""
    session = DBSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


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

            avg_price = session.query(func.avg(Car.price)).scalar()
            avg_mileage = session.query(func.avg(Car.mileage)).scalar()
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
            rows = (
                session.query(
                    Car.brand,
                    func.count(Car.id).label("count"),
                    func.avg(Car.price).label("avg_price"),
                    func.avg(Car.mileage).label("avg_mileage"),
                    func.avg(Car.year_manufacture).label("avg_year"),
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
            rows = (
                session.query(
                    Car.model,
                    func.count(Car.id).label("count"),
                    func.avg(Car.price).label("avg_price"),
                    func.avg(Car.mileage).label("avg_mileage"),
                    func.avg(Car.year_manufacture).label("avg_year"),
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
   

@app.route('/car-compare')
def car_comparison():
    return render_template('car-compare.html')


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
    