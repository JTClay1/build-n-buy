from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from math import ceil

from extensions import db
from models import Goal

goal_bp = Blueprint("goals", __name__)


def parse_target_date(target_date_value):
    if not target_date_value:
        return None

    try:
        # Handles frontend date input format: "YYYY-MM-DD"
        return datetime.strptime(target_date_value, "%Y-%m-%d")
    except ValueError:
        try:
            # Fallback for ISO datetime strings
            return datetime.fromisoformat(target_date_value)
        except ValueError:
            return None


def calculate_months_from_target_date(target_date):
    today = datetime.utcnow().date()
    target_day = target_date.date()
    days_remaining = (target_day - today).days

    if days_remaining <= 0:
        return 0

    return ceil(days_remaining / 30)


def sync_goal_timeline(goal):
    """
    Keeps legacy database fields updated while target_date stays the source of truth.
    """
    months_remaining = goal.months_remaining()

    goal.months_to_goal = max(months_remaining, 1)
    goal.monthly_target = goal.calculated_monthly_target()

    if goal.saved_amount >= goal.target_amount:
        goal.saved_amount = goal.target_amount
        goal.status = "completed"
        goal.monthly_target = 0.0


@goal_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_goals():
    user_id = int(get_jwt_identity())

    goals = Goal.query.filter_by(user_id=user_id).all()

    return jsonify({
        "goals": [goal.to_dict() for goal in goals]
    }), 200


@goal_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_goal():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    item_name = data.get("item_name")
    retailer = data.get("retailer")
    target_amount = data.get("target_amount")
    target_date_value = data.get("target_date")
    months_to_goal = data.get("months_to_goal")

    if not item_name or not target_amount:
        return jsonify({"error": "Item name and target amount are required"}), 400

    item_name = item_name.strip()

    if not item_name:
        return jsonify({"error": "Item name cannot be empty"}), 400

    if retailer:
        retailer = retailer.strip()

    try:
        target_amount = float(target_amount)
    except ValueError:
        return jsonify({"error": "Target amount must be a number"}), 400

    if target_amount <= 0:
        return jsonify({"error": "Target amount must be greater than zero"}), 400

    target_date = parse_target_date(target_date_value)

    # Backward-compatible fallback while frontend is being converted
    if not target_date and months_to_goal:
        try:
            months_to_goal = int(months_to_goal)
        except ValueError:
            return jsonify({"error": "Months to goal must be an integer"}), 400

        if months_to_goal <= 0:
            return jsonify({"error": "Months to goal must be greater than zero"}), 400

        target_date = datetime.utcnow() + timedelta(days=months_to_goal * 30)

    if not target_date:
        return jsonify({"error": "Target date is required"}), 400

    calculated_months = calculate_months_from_target_date(target_date)

    if calculated_months <= 0:
        return jsonify({"error": "Target date must be in the future"}), 400

    new_goal = Goal(
        user_id=user_id,
        item_name=item_name,
        retailer=retailer,
        target_amount=target_amount,
        saved_amount=0.0,
        months_to_goal=calculated_months,
        monthly_target=round(target_amount / calculated_months, 2),
        target_date=target_date,
        status="active"
    )

    sync_goal_timeline(new_goal)

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        "message": "Goal created successfully",
        "goal": new_goal.to_dict()
    }), 201


@goal_bp.route("/<int:goal_id>", methods=["GET"])
@jwt_required()
def get_goal(goal_id):
    user_id = int(get_jwt_identity())

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    sync_goal_timeline(goal)
    db.session.commit()

    return jsonify({"goal": goal.to_dict()}), 200


@goal_bp.route("/<int:goal_id>", methods=["PATCH"])
@jwt_required()
def update_goal(goal_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    if "item_name" in data:
        item_name = data["item_name"].strip()

        if not item_name:
            return jsonify({"error": "Item name cannot be empty"}), 400

        goal.item_name = item_name

    if "retailer" in data:
        retailer = data["retailer"]

        if retailer:
            retailer = retailer.strip()

        goal.retailer = retailer

    if "target_amount" in data:
        try:
            target_amount = float(data["target_amount"])
        except ValueError:
            return jsonify({"error": "Target amount must be a number"}), 400

        if target_amount <= 0:
            return jsonify({"error": "Target amount must be greater than zero"}), 400

        goal.target_amount = target_amount

    if "target_date" in data:
        target_date = parse_target_date(data["target_date"])

        if not target_date:
            return jsonify({"error": "Target date must use YYYY-MM-DD format"}), 400

        calculated_months = calculate_months_from_target_date(target_date)

        if calculated_months <= 0:
            return jsonify({"error": "Target date must be in the future"}), 400

        goal.target_date = target_date

    # Backward-compatible support for old frontend/month-based requests
    if "months_to_goal" in data and "target_date" not in data:
        try:
            months_to_goal = int(data["months_to_goal"])
        except ValueError:
            return jsonify({"error": "Months to goal must be an integer"}), 400

        if months_to_goal <= 0:
            return jsonify({"error": "Months to goal must be greater than zero"}), 400

        goal.target_date = datetime.utcnow() + timedelta(days=months_to_goal * 30)

    if "status" in data:
        allowed_statuses = ["active", "completed", "scrapped"]
        status = data["status"]

        if status not in allowed_statuses:
            return jsonify({"error": "Invalid goal status"}), 400

        goal.status = status

    sync_goal_timeline(goal)

    db.session.commit()

    return jsonify({
        "message": "Goal updated successfully",
        "goal": goal.to_dict()
    }), 200


@goal_bp.route("/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    user_id = int(get_jwt_identity())

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    db.session.delete(goal)
    db.session.commit()

    return jsonify({"message": "Goal deleted successfully"}), 200