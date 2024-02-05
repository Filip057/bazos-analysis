from app import db

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
