from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Contribution, Goal

contribution_bp = Blueprint("contributions", __name__)


def sync_goal_after_savings_change(goal):
    """
    Keeps goal savings status and timeline calculations consistent after
    deposits or withdrawals.
    """
    goal.saved_amount = max(goal.saved_amount, 0)

    if goal.saved_amount >= goal.target_amount:
        goal.saved_amount = goal.target_amount
        goal.status = "completed"
    elif goal.status == "completed":
        goal.status = "active"

    months_left = goal.months_remaining()
    goal.months_to_goal = max(months_left, 1)
    goal.monthly_target = goal.calculated_monthly_target()


@contribution_bp.route("/goals/<int:goal_id>/contributions", methods=["POST"])
@jwt_required()
def create_contribution(goal_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    amount = data.get("amount")
    note = data.get("note", "")
    entry_type = data.get("entry_type", "deposit")

    if entry_type not in ["deposit", "withdrawal"]:
        return jsonify({"error": "Entry type must be deposit or withdrawal"}), 400

    if amount is None:
        return jsonify({"error": "Amount is required"}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Amount must be a number"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    if entry_type == "withdrawal" and amount > goal.saved_amount:
        return jsonify({
            "error": "Withdrawal amount cannot be greater than saved amount"
        }), 400

    new_contribution = Contribution(
        goal_id=goal.id,
        amount=amount,
        entry_type=entry_type,
        note=note.strip() if note else None
    )

    if entry_type == "deposit":
        goal.saved_amount += amount
    else:
        goal.saved_amount -= amount

    sync_goal_after_savings_change(goal)

    db.session.add(new_contribution)
    db.session.commit()

    return jsonify({
        "message": "Savings activity added successfully",
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

    goal = Goal.query.filter_by(
        id=contribution.goal_id,
        user_id=user_id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    if contribution.entry_type == "deposit":
        goal.saved_amount -= contribution.amount
    else:
        goal.saved_amount += contribution.amount

    sync_goal_after_savings_change(goal)

    db.session.delete(contribution)
    db.session.commit()

    return jsonify({
        "message": "Savings activity deleted successfully",
        "goal": goal.to_dict()
    }), 200