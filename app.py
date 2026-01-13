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

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from database.model import Base, Car
from config import get_config

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
   

@app.route('/car-compare', methods=['GET', 'POST'])
def car_comparison():
    form = CarComparisonForm()
    if form.validate_on_submit():
        brand = form.brand.data
        model = form.model.data
        price = form.price.data
        year = form.year.data
        y_plusminus = form.y_plusminus.data
        mileage = form.mileage.data
        m_pct_plusminus = form.m_pct_plusminus.data
        # Redirect to the comparison route with form data as query parameters
        return redirect(url_for('get_comparison', brand=brand, model=model, price=price, year=year, y_plusminus=y_plusminus, mileage=mileage, m_pct_plusminus=m_pct_plusminus))
    return render_template('car_comparison.html', form=form)


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


if __name__ == '__main__':
    app.run(debug=config.DEBUG)
    