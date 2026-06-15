from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Goal, Contribution

contribution_bp = Blueprint("contributions", __name__)


@contribution_bp.route("/goals/<int:goal_id>/contributions", methods=["POST"])
@jwt_required()
def create_contribution(goal_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    amount = data.get("amount")
    note = data.get("note")

    if amount is None:
        return jsonify({"error": "Contribution amount is required"}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Contribution amount must be a number"}), 400

    if amount <= 0:
        return jsonify({"error": "Contribution amount must be greater than zero"}), 400

    new_contribution = Contribution(
        goal_id=goal.id,
        amount=amount,
        note=note
    )

    goal.saved_amount += amount

    if goal.saved_amount >= goal.target_amount:
        goal.saved_amount = goal.target_amount
        goal.status = "completed"

    remaining_amount = goal.target_amount - goal.saved_amount

    if goal.status != "completed":
        goal.monthly_target = round(remaining_amount / goal.months_to_goal, 2)
    else:
        goal.monthly_target = 0.0

    db.session.add(new_contribution)
    db.session.commit()

    return jsonify({
        "message": "Contribution added successfully",
        "contribution": new_contribution.to_dict(),
        "goal": goal.to_dict()
    }), 201


@contribution_bp.route("/contributions/<int:contribution_id>", methods=["DELETE"])
@jwt_required()
def delete_contribution(contribution_id):
    user_id = int(get_jwt_identity())

    contribution = Contribution.query.get(contribution_id)

    if not contribution:
        return jsonify({"error": "Contribution not found"}), 404

    goal = contribution.goal

    if goal.user_id != user_id:
        return jsonify({"error": "Contribution not found"}), 404

    goal.saved_amount -= contribution.amount

    if goal.saved_amount < 0:
        goal.saved_amount = 0.0

    if goal.saved_amount < goal.target_amount and goal.status == "completed":
        goal.status = "active"

    remaining_amount = goal.target_amount - goal.saved_amount
    goal.monthly_target = round(remaining_amount / goal.months_to_goal, 2)

    db.session.delete(contribution)
    db.session.commit()

    return jsonify({
        "message": "Contribution deleted successfully",
        "goal": goal.to_dict()
    }), 200