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

    items = db.relationship("Item", back_populates="reservation")

class Item(db.Model):
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reservation_id = db.Column(db.String(8), db.ForeignKey("reservation.reservation_id"), nullable=False)
    reservation = db.relationship("Reservation", back_populates="items")

