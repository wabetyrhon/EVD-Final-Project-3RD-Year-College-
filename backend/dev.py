from os import getenv

from werkzeug.security import check_password_hash
from flask import jsonify, request
from sqlalchemy import text

from backend import app, db
from backend.models import Reservation, Item

def reset_database():
    with app.app_context():
        print("Testing database connection...")
        try:
            db.session.execute(text("SELECT 1"))
            print("Database connection successful!")
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

        print("Dropping all existing tables...")
        db.drop_all()
        print("Creating new table schemas...")
        db.create_all()
        print("Adding default rows...")

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
