from os import getenv

from werkzeug.security import check_password_hash
from flask import jsonify, request
from sqlalchemy import text

from backend import app, db
from backend.models import Reservation, ReservationItem, Product, Category

def reset_database():
    with app.app_context():
        with db.engine.connect() as conn:
            print("Testing database connection...")
            try:
                conn.execute(text("SELECT 1"))
                print("Database connection successful!")
            except Exception as e:
                print(f"Database connection failed: {e}")
                return False
            print("Dropping all existing tables...")

            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            db.metadata.drop_all(bind=conn)
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

            print("Creating new table schemas...")
            db.metadata.create_all(bind=conn)
            conn.commit()

            print("Adding default rows...")
            categories = ["Pork", "Chicken", "Hotdogs & Sausages", "Beef", "Fish"]
            db.session.add_all([Category(name=category) for category in categories])
            db.session.commit()

            print("Database ready!")
            return True


@app.route("/dev/resetdb", methods=["POST"])
def resetDB():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    password = request.json.get("password", None)
    if not password:
        return jsonify({"msg": "Missing password"}), 400

    if not check_password_hash(getenv("DEV_SECRET"), password):
        return jsonify({"msg": "Wrong password"}), 401

    if reset_database():
        return jsonify({"msg": "Database reset successful!"}), 200
    else:
        return jsonify({"msg": "Failed to reset database..."}), 200
