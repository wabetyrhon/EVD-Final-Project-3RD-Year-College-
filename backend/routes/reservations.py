from datetime import datetime
from flask import Blueprint, jsonify, request, session
from backend import db
from backend.utils import admin_required
from backend.models import Product, Reservation, ReservationItem


reservations_bp = Blueprint("reservations", __name__)


@reservations_bp.route("/api/reservations", methods=["GET"])
def get_reservations():
    """Read all reservations (Accessible to anyone)."""
    reservations = Reservation.query.all()
    result = []
    for res in reservations:
        result.append({
            "reservation_id": res.reservation_id,
            "customer_name": res.customer_name,
            "customer_email": res.customer_email,
            "customer_phone": res.customer_phone,
            "pickup_date": res.pickup_date.isoformat() if res.pickup_date else None,
            "created_at": res.created_at.isoformat() if res.created_at else None,
            "items": [{
                "item_id": item.item_id,
                "product_id": item.product_id,
                "quantity": item.quantity
                } for item in res.items]
            })
    return jsonify(result), 200


@reservations_bp.route("/api/reservations/<string:reservation_id>", methods=["GET"])
def get_reservation(reservation_id):
    """Read a single reservation by ID (Accessible to anyone)."""
    res = Reservation.query.get_or_404(reservation_id)
    return jsonify({
        "reservation_id": res.reservation_id,
        "customer_name": res.customer_name,
        "customer_email": res.customer_email,
        "customer_phone": res.customer_phone,
        "pickup_date": res.pickup_date.isoformat() if res.pickup_date else None,
        "created_at": res.created_at.isoformat() if res.created_at else None,
        "items": [{
            "item_id": item.item_id,
            "product_id": item.product_id,
            "quantity": item.quantity
            } for item in res.items]
        }), 200


@reservations_bp.route("/api/reservations", methods=["POST"])
def create_reservation():
    """Create a new reservation with items (Accessible to anyone)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ["customer_name", "customer_email", "customer_phone", "items"]
    if not all(k in data for k in required_fields):
        return jsonify({"error": f"Missing required fields: {required_fields}"}), 400

    try:
        pickup_date = datetime.strptime(data["pickup_date"], "%Y-%m-%d").date() if data.get("pickup_date") else None
    except ValueError:
        return jsonify({"error": "Invalid date format for pickup_date. Use YYYY-MM-DD."}), 400

    new_reservation = Reservation(
            customer_name=data["customer_name"],
            customer_email=data["customer_email"],
            customer_phone=data["customer_phone"],
            pickup_date=pickup_date
            )
    db.session.add(new_reservation)
    db.session.flush()

    for item_data in data["items"]:
        if not all(k in item_data for k in ("product_id", "quantity")):
            db.session.rollback()
            return jsonify({"error": "Each item must have product_id and quantity"}), 400

        product = Product.query.get(item_data["product_id"])
        if not product:
            db.session.rollback()
            return jsonify({"error": f"Product with ID {item_data['product_id']} not found"}), 404

        res_item = ReservationItem(
                reservation_id=new_reservation.reservation_id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"]
                )
        db.session.add(res_item)

    db.session.commit()
    return jsonify({
        "message": "Reservation created successfully",
        "reservation_id": new_reservation.reservation_id
        }), 201


@reservations_bp.route("/api/reservations/<string:reservation_id>", methods=["PUT", "PATCH"])
def update_reservation(reservation_id):
    """Update a reservation (Accessible to anyone)."""
    res = Reservation.query.get_or_404(reservation_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    res.customer_name = data.get("customer_name", res.customer_name)
    res.customer_email = data.get("customer_email", res.customer_email)
    res.customer_phone = data.get("customer_phone", res.customer_phone)

    if "pickup_date" in data:
        try:
            res.pickup_date = datetime.strptime(data["pickup_date"], "%Y-%m-%d").date() if data["pickup_date"] else None
        except ValueError:
            return jsonify({"error": "Invalid date format for pickup_date. Use YYYY-MM-DD."}), 400

    db.session.commit()
    return jsonify({"message": "Reservation updated successfully"}), 200


@reservations_bp.route("/api/reservations/<string:reservation_id>", methods=["DELETE"])
@admin_required
def delete_reservation(reservation_id):
    """Delete a reservation (Admin only)."""
    res = Reservation.query.get_or_404(reservation_id)

    ReservationItem.query.filter_by(reservation_id=reservation_id).delete()
    db.session.delete(res)
    db.session.commit()
    return jsonify({"message": "Reservation deleted successfully"}), 200
