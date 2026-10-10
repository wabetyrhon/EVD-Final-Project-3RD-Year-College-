from flask import Blueprint, jsonify, request, session
from backend import db
from backend.utils import admin_required
from backend.models import Product


products_bp = Blueprint("products", __name__)


@products_bp.route("/api/products", methods=["GET"])
def get_products():
    """Read all products (Accessible to anyone)."""
    products = Product.query.all()
    result = [{
        "product_id": p.product_id,
        "name": p.name,
        "unit": p.unit,
        "price": p.price
        } for p in products]
    return jsonify(result), 200


@products_bp.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Read a single product by ID (Accessible to anyone)."""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        "product_id": product.product_id,
        "name": product.name,
        "unit": product.unit,
        "price": product.price
        }), 200


@products_bp.route("/api/products", methods=["POST"])
@admin_required
def create_product():
    """Create a new product (Admin only)."""
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "unit", "price")):
        return jsonify({"error": "Missing required fields (name, unit, price)"}), 400

    new_product = Product(
            name=data["name"],
            unit=data["unit"],
            price=data["price"]
            )
    db.session.add(new_product)
    db.session.commit()

    return jsonify({
        "message": "Product created successfully",
        "product_id": new_product.product_id
        }), 201


@products_bp.route("/api/products/<int:product_id>", methods=["PUT", "PATCH"])
@admin_required
def update_product(product_id):
    """Update a product (Admin only)."""
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    product.name = data.get("name", product.name)
    product.unit = data.get("unit", product.unit)
    product.price = data.get("price", product.price)

    db.session.commit()
    return jsonify({"message": "Product updated successfully"}), 200


@products_bp.route("/api/products/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    """Delete a product (Admin only)."""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200

