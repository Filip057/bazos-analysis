from dotenv import load_dotenv
import os
import secrets

from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_restful import Api, Resource
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect

from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional


from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker


from database.model import Base, Car

# MySQL connection settings
load_dotenv()
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')

# MySQL connection string
DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost:3306/bazos_cars'


app = Flask(__name__)

# Generate a secret key
secret_key = secrets.token_hex(16)

# Set the secret key in the Flask app configuration
app.config['SECRET_KEY'] = secret_key

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Connect to the database
engine = create_engine(DATABASE_URI)
Base.metadata.bind = engine


@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route('/cars', methods=['GET'])
def get_cars():
    
    

@app.route('/cars/<int:car_id>', methods=['GET'])
def get_car(car_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    car = session.query(Car).filter_by(id=car_id).one()
    return jsonify(car.serialize())

@app.route('/car-stats/<brand>/<model>', methods=['GET'])
def get_car_stats(brand, model):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # Base query
    query = session.query(func.avg(Car.price).label('average_price'),
                           func.max(Car.price).label('highest_price'),
                           func.min(Car.price).label('lowest_price'))

    # Filter by brand and model
    query = query.filter(Car.brand == brand, Car.model == model)

    # Optional filters
    year_from = request.args.get('year_from')
    year_to = request.args.get('year_to')
    mileage_from = request.args.get('mileage_from')
    mileage_to = request.args.get('mileage_to')

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

    # Format the response
    response = {
        'brand': brand,
        'model': model,
        'average_price': result.average_price,
        'highest_price': result.highest_price,
        'lowest_price': result.lowest_price
    }
    return jsonify(response)
   

@app.route('/car-compare/<brand>/<model>/<int:price>', methods=['GET'])
def get_comparison(brand, model, price):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # Filter cars by brand and model
    cars_query = session.query(Car).filter_by(brand=brand, model=model)
    
    
    year = request.args.get('year')
    y_plusminus = request.args.get('y_plusminus')
    if year and y_plusminus:
        y_plus = int(year) + int(y_plusminus)
        y_minus = int(year) - int(y_plusminus)
        cars_query = cars_query.filter(Car.year_manufacture.between(y_minus, y_plus))


    mileage = request.args.get('mileage')
    m_pct_plusminus = request.args.get('m_pct_plusminus')
    if mileage and y_plusminus:
        m_plus = int(mileage) * ((100 + int(m_pct_plusminus)) / 100)
        m_minus = int(mileage) * ((100 - int(m_pct_plusminus)) / 100)
        cars_query = cars_query.filter(Car.mileage.between(m_minus, m_plus))

    
    # Calculate the percentile
    count_cars = cars_query.count()
    count_lower_price = cars_query.filter(Car.price < price).count()
    percentile = (count_lower_price / count_cars) * 100
    
    return f"Your given offer is more expensive than {percentile:.2f}% of similar car offers."

@app.route('/car-comparison', methods=['GET', 'POST'])
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


# FORM CLASS

class CarComparisonForm(FlaskForm):
    brand = StringField('Brand', validators=[DataRequired()])
    model = StringField('Model', validators=[DataRequired()])
    price = IntegerField('Price (CZK)', validators=[DataRequired()])
    year = IntegerField('Year', validators=[Optional()])
    y_plusminus = IntegerField('Year Plus/Minus', validators=[Optional()])
    mileage = IntegerField('Mileage', validators=[Optional()])
    m_pct_plusminus = IntegerField('Mileage Percentage Plus/Minus', validators=[Optional()])
    submit = SubmitField('Compare')


class CarListApi(Resource):
    def get(self):
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        cars = session.query(Car).all()
        return {'cars': [car.serialize() for car in cars]}

class CarApi()

class CarCompare(Resource):
    pass

class CarStats(Resource):
    pass

if __name__ == '__main__':
    app.run(debug=True)
    