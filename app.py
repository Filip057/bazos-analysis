from flask import Flask
from sqlalchemy.orm import DeclarativeBase
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship




app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bazos_cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'


class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

db.init_app(app)

class Car(Base):
    __tablename__ = 'cars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(length=50))
    model = Column(String(length=50))
    year_manufacture = Column(Integer, nullable=True)
    mileage = Column(Integer, nullable=True)
    power = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"



if __name__ == '__main__':
    with app.app_context():
        # Create the database tables
        db.create_all()
    app.run(debug=True)
    