from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Goal, Notification, RetailerPrice
from services.price_scraper import PriceScrapeError, scrape_price_from_url

price_bp = Blueprint("prices", __name__)


def get_user_goal(goal_id, user_id):
    return Goal.query.filter_by(id=goal_id, user_id=user_id).first()


def parse_money(value, field_name, default=None):
    if value in [None, ""]:
        return default

    try:
        value = float(value)
    except (TypeError, ValueError):
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
        "target_vs_lowest_difference": round(
            goal.target_amount - lowest_price.total_price(),
            2
        )
    }


def create_price_notification(user_id, goal, retailer_price, old_price, new_price):
    price_difference = round(new_price - old_price, 2)

    if price_difference < 0:
        title = f"Price drop: {goal.item_name}"
        message = (
            f"{retailer_price.retailer_name} dropped from "
            f"${old_price:,.2f} to ${new_price:,.2f}."
        )
        notification_type = "price_drop"
    elif price_difference > 0:
        title = f"Price updated: {goal.item_name}"
        message = (
            f"{retailer_price.retailer_name} increased from "
            f"${old_price:,.2f} to ${new_price:,.2f}."
        )
        notification_type = "price_update"
    else:
        title = f"Price checked: {goal.item_name}"
        message = (
            f"{retailer_price.retailer_name} is still listed at "
            f"${new_price:,.2f}."
        )
        notification_type = "price_check"

    notification = Notification(
        user_id=user_id,
        goal_id=goal.id,
        title=title,
        message=message,
        notification_type=notification_type
    )

    db.session.add(notification)

    return notification


def refresh_retailer_price(retailer_price, user_id, render=None):
    if not retailer_price.product_url:
        raise PriceScrapeError("This retailer price does not have a product URL.")

    old_price = float(retailer_price.price)

    scrape_result = scrape_price_from_url(
        retailer_price.product_url,
        render=render,
        previous_price=old_price
    )

    new_price = float(scrape_result["price"])

    retailer_price.price = new_price
    retailer_price.last_checked_at = datetime.utcnow()

    notification = create_price_notification(
        user_id=user_id,
        goal=retailer_price.goal,
        retailer_price=retailer_price,
        old_price=old_price,
        new_price=new_price
    )

    db.session.flush()

    return {
        "price_id": retailer_price.id,
        "retailer_name": retailer_price.retailer_name,
        "old_price": round(old_price, 2),
        "new_price": round(new_price, 2),
        "difference": round(new_price - old_price, 2),
        "scrape": scrape_result,
        "notification": notification.to_dict()
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


@price_bp.route("/prices/<int:price_id>/refresh", methods=["PATCH"])
@jwt_required()
def refresh_single_price(price_id):
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
    render = data.get("render")

    try:
        refresh_result = refresh_retailer_price(
            retailer_price,
            user_id=user_id,
            render=render
        )
    except PriceScrapeError as error:
        return jsonify({"error": str(error)}), 422

    db.session.commit()

    return jsonify({
        "message": "Live price refreshed successfully",
        "result": refresh_result,
        "price": retailer_price.to_dict(),
        "summary": build_price_summary(retailer_price.goal)
    }), 200


@price_bp.route("/goals/<int:goal_id>/prices/refresh", methods=["POST"])
@jwt_required()
def refresh_goal_prices(goal_id):
    user_id = int(get_jwt_identity())
    goal = get_user_goal(goal_id, user_id)

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    data = request.get_json() or {}
    render = data.get("render")

    prices_to_refresh = [
        retailer_price
        for retailer_price in goal.retailer_prices
        if retailer_price.is_active and retailer_price.product_url
    ]

    if not prices_to_refresh:
        return jsonify({
            "error": "No active retailer prices with product URLs to refresh."
        }), 400

    results = []

    for retailer_price in prices_to_refresh:
        try:
            refresh_result = refresh_retailer_price(
                retailer_price,
                user_id=user_id,
                render=render
            )

            results.append({
                "price_id": retailer_price.id,
                "retailer_name": retailer_price.retailer_name,
                "status": "updated",
                "result": refresh_result
            })
        except PriceScrapeError as error:
            results.append({
                "price_id": retailer_price.id,
                "retailer_name": retailer_price.retailer_name,
                "status": "failed",
                "error": str(error)
            })

    db.session.commit()

    updated_count = len([
        result for result in results
        if result["status"] == "updated"
    ])

    failed_count = len([
        result for result in results
        if result["status"] == "failed"
    ])

    prices = (
        RetailerPrice.query
        .filter_by(goal_id=goal.id)
        .order_by(RetailerPrice.is_active.desc(), RetailerPrice.retailer_name)
        .all()
    )

    return jsonify({
        "message": "Live price refresh completed",
        "updated_count": updated_count,
        "failed_count": failed_count,
        "results": results,
        "prices": [price.to_dict() for price in prices],
        "summary": build_price_summary(goal)
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