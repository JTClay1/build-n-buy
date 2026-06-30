from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from extensions import db
from models import Goal

goal_bp = Blueprint("goals", __name__)


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
    data = request.get_json()

    item_name = data.get("item_name")
    target_amount = data.get("target_amount")
    months_to_goal = data.get("months_to_goal")

    if not item_name or not target_amount or not months_to_goal:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        target_amount = float(target_amount)
        months_to_goal = int(months_to_goal)
    except ValueError:
        return jsonify({
            "error": "target_amount must be a number and months_to_goal must be an integer"
        }), 400

    if target_amount <= 0 or months_to_goal <= 0:
        return jsonify({
            "error": "target_amount and months_to_goal must be greater than zero"
        }), 400

    monthly_target = round(target_amount / months_to_goal, 2)
    target_date = datetime.utcnow() + timedelta(days=months_to_goal * 30)

    new_goal = Goal(
        user_id=user_id,
        item_name=item_name,
        target_amount=target_amount,
        saved_amount=0.0,
        months_to_goal=months_to_goal,
        monthly_target=monthly_target,
        target_date=target_date,
        status="active"
    )

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

    return jsonify({"goal": goal.to_dict()}), 200


@goal_bp.route("/<int:goal_id>", methods=["PATCH"])
@jwt_required()
def update_goal(goal_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    if "item_name" in data:
        item_name = data["item_name"].strip()

        if not item_name:
            return jsonify({"error": "Item name cannot be empty"}), 400

        goal.item_name = item_name

    if "target_amount" in data:
        try:
            target_amount = float(data["target_amount"])
        except ValueError:
            return jsonify({"error": "Target amount must be a number"}), 400

        if target_amount <= 0:
            return jsonify({"error": "Target amount must be greater than zero"}), 400

        goal.target_amount = target_amount

    if "months_to_goal" in data:
        try:
            months_to_goal = int(data["months_to_goal"])
        except ValueError:
            return jsonify({"error": "Months to goal must be an integer"}), 400

        if months_to_goal <= 0:
            return jsonify({"error": "Months to goal must be greater than zero"}), 400

        goal.months_to_goal = months_to_goal
        goal.target_date = datetime.utcnow() + timedelta(days=months_to_goal * 30)

    if "status" in data:
        allowed_statuses = ["active", "completed", "scrapped"]
        status = data["status"]

        if status not in allowed_statuses:
            return jsonify({"error": "Invalid goal status"}), 400

        goal.status = status

    if goal.saved_amount >= goal.target_amount:
        goal.saved_amount = goal.target_amount
        goal.status = "completed"

    remaining_amount = max(goal.target_amount - goal.saved_amount, 0)

    if goal.status == "completed":
        goal.monthly_target = 0.0
    else:
        goal.monthly_target = round(remaining_amount / goal.months_to_goal, 2)

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