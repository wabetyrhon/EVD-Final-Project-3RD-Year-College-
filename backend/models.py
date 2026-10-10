from datetime import datetime

from backend import app, db
from backend.utils import generate_random_id


class Reservation(db.Model):
    reservation_id = db.Column(db.String(8), primary_key=True, default=generate_random_id)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(254), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    pickup_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime(), default=datetime.now)

    items = db.relationship("ReservationItem", back_populates="reservation")

class ReservationItem(db.Model):
    item_id = db.Column(db.Integer, primary_key=True)

    reservation_id = db.Column(db.String(8), db.ForeignKey("reservation.reservation_id"), nullable=False)
    reservation = db.relationship("Reservation", back_populates="items")

    product_id = db.Column(db.Integer, db.ForeignKey("product.product_id"), nullable=False)
    product = db.relationship("Product", back_populates="reservation_items")

    quantity = db.Column(db.Integer, nullable=False)

class Product(db.Model):
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Integer, nullable=False)

    reservation_items = db.relationship("ReservationItem", back_populates="product")

