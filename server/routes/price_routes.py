from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Goal, RetailerPrice

price_bp = Blueprint("prices", __name__)


def get_user_goal(goal_id, user_id):
    return Goal.query.filter_by(id=goal_id, user_id=user_id).first()


def parse_money(value, field_name, default=None):
    if value in [None, ""]:
        return default

    try:
        value = float(value)
    except ValueError:
        raise ValueError(f"{field_name} must be a number")

    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")

    return value


def build_price_summary(goal):
    active_prices = [
        retailer_price
        for retailer_price in goal.retailer_prices
        if retailer_price.is_active
    ]

    if not active_prices:
        return {
            "price_count": 0,
            "lowest_price": None,
            "highest_price": None,
            "average_total_price": 0,
            "target_vs_lowest_difference": None
        }

    lowest_price = min(
        active_prices,
        key=lambda retailer_price: retailer_price.total_price()
    )

    highest_price = max(
        active_prices,
        key=lambda retailer_price: retailer_price.total_price()
    )

    average_total_price = sum(
        retailer_price.total_price() for retailer_price in active_prices
    ) / len(active_prices)

    return {
        "price_count": len(active_prices),
        "lowest_price": lowest_price.to_dict(),
        "highest_price": highest_price.to_dict(),
        "average_total_price": round(average_total_price, 2),
        "target_vs_lowest_difference": round(goal.target_amount - lowest_price.total_price(), 2)
    }


@price_bp.route("/goals/<int:goal_id>/prices", methods=["GET"])
@jwt_required()
def get_goal_prices(goal_id):
    user_id = int(get_jwt_identity())
    goal = get_user_goal(goal_id, user_id)

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    prices = (
        RetailerPrice.query
        .filter_by(goal_id=goal.id)
        .order_by(RetailerPrice.is_active.desc(), RetailerPrice.retailer_name)
        .all()
    )

    return jsonify({
        "prices": [price.to_dict() for price in prices],
        "summary": build_price_summary(goal)
    }), 200


@price_bp.route("/goals/<int:goal_id>/prices", methods=["POST"])
@jwt_required()
def create_goal_price(goal_id):
    user_id = int(get_jwt_identity())
    goal = get_user_goal(goal_id, user_id)

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    data = request.get_json() or {}

    retailer_name = data.get("retailer_name", "").strip()
    product_url = data.get("product_url", "")
    note = data.get("note", "")

    if not retailer_name:
        return jsonify({"error": "Retailer name is required"}), 400

    try:
        price = parse_money(data.get("price"), "Price")
        shipping_cost = parse_money(data.get("shipping_cost"), "Shipping cost", 0.0)
        tax_estimate = parse_money(data.get("tax_estimate"), "Tax estimate", 0.0)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    retailer_price = RetailerPrice(
        goal_id=goal.id,
        retailer_name=retailer_name,
        product_url=product_url.strip() if product_url else None,
        price=price,
        shipping_cost=shipping_cost,
        tax_estimate=tax_estimate,
        is_preferred=bool(data.get("is_preferred", False)),
        note=note.strip() if note else None,
        last_checked_at=datetime.utcnow()
    )

    if retailer_price.is_preferred:
        RetailerPrice.query.filter_by(goal_id=goal.id).update({
            "is_preferred": False
        })

    db.session.add(retailer_price)
    db.session.commit()

    return jsonify({
        "message": "Retailer price created successfully",
        "price": retailer_price.to_dict(),
        "summary": build_price_summary(goal)
    }), 201


@price_bp.route("/prices/<int:price_id>", methods=["PATCH"])
@jwt_required()
def update_goal_price(price_id):
    user_id = int(get_jwt_identity())

    retailer_price = (
        RetailerPrice.query
        .join(Goal)
        .filter(
            RetailerPrice.id == price_id,
            Goal.user_id == user_id
        )
        .first()
    )

    if not retailer_price:
        return jsonify({"error": "Retailer price not found"}), 404

    data = request.get_json() or {}

    if "retailer_name" in data:
        retailer_name = data["retailer_name"].strip()

        if not retailer_name:
            return jsonify({"error": "Retailer name cannot be empty"}), 400

        retailer_price.retailer_name = retailer_name

    if "product_url" in data:
        product_url = data["product_url"]
        retailer_price.product_url = product_url.strip() if product_url else None

    if "price" in data:
        try:
            retailer_price.price = parse_money(data["price"], "Price")
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        retailer_price.last_checked_at = datetime.utcnow()

    if "shipping_cost" in data:
        try:
            retailer_price.shipping_cost = parse_money(
                data["shipping_cost"],
                "Shipping cost",
                0.0
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    if "tax_estimate" in data:
        try:
            retailer_price.tax_estimate = parse_money(
                data["tax_estimate"],
                "Tax estimate",
                0.0
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    if "is_preferred" in data:
        retailer_price.is_preferred = bool(data["is_preferred"])

        if retailer_price.is_preferred:
            RetailerPrice.query.filter_by(
                goal_id=retailer_price.goal_id
            ).filter(
                RetailerPrice.id != retailer_price.id
            ).update({
                "is_preferred": False
            })

    if "is_active" in data:
        retailer_price.is_active = bool(data["is_active"])

    if "note" in data:
        note = data["note"]
        retailer_price.note = note.strip() if note else None

    db.session.commit()

    return jsonify({
        "message": "Retailer price updated successfully",
        "price": retailer_price.to_dict(),
        "summary": build_price_summary(retailer_price.goal)
    }), 200


@price_bp.route("/prices/<int:price_id>", methods=["DELETE"])
@jwt_required()
def delete_goal_price(price_id):
    user_id = int(get_jwt_identity())

    retailer_price = (
        RetailerPrice.query
        .join(Goal)
        .filter(
            RetailerPrice.id == price_id,
            Goal.user_id == user_id
        )
        .first()
    )

    if not retailer_price:
        return jsonify({"error": "Retailer price not found"}), 404

    goal = retailer_price.goal

    db.session.delete(retailer_price)
    db.session.commit()

    return jsonify({
        "message": "Retailer price deleted successfully",
        "summary": build_price_summary(goal)
    }), 200