from flask import Flask

from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bazos_cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class CarBrand(db.Model):
    __tablename__ = 'car_brands'
    
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50))

class BrandModel(db.Model):
    __tablename__ = 'brand_models'

    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(50))

    # Relationship with BrandModel
    models = db.relationship('BrandModel', backref='brand', lazy='joined')
    brand_id = db.Column(db.Integer, db.ForeignKey('car_brands.id'), nullable=False)
    
    # Relationship with ModelInstance
    instances = db.relationship('ModelInstance', backref='model', lazy='joined')

class ModelInstance(db.Model):
    __tablename__ = 'car_details'

    id = db.Column(db.Integer, primary_key=True)
    year_manufacture = db.Column(db.Integer)
    mileage = db.Column(db.Integer)
    power = db.Column(db.Integer)
    price = db.Column(db.Integer)

    model_id = db.Column(db.Integer, db.ForeignKey('brand_models.id'), nullable=False)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == '__main__':
    app.run(debug=True)
    db.create_all()