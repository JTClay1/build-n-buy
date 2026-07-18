from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import BudgetItem, Goal

budget_bp = Blueprint("budget", __name__)


def build_budget_summary(user_id):
    # Inactive items stay available for history/editing but must not affect the
    # affordability snapshot used by the dashboard and advisor.
    budget_items = BudgetItem.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()

    active_goals = Goal.query.filter_by(
        user_id=user_id,
        status="active"
    ).all()

    monthly_income = sum(
        item.amount for item in budget_items if item.item_type == "income"
    )

    monthly_expenses = sum(
        item.amount for item in budget_items if item.item_type == "expense"
    )

    # Goal commitments are treated like planned monthly outflow after recurring
    # expenses, producing the user's remaining discretionary cushion.
    total_goal_monthly_targets = sum(
        goal.calculated_monthly_target() for goal in active_goals
    )

    available_before_goals = monthly_income - monthly_expenses
    available_after_goals = available_before_goals - total_goal_monthly_targets

    return {
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "available_before_goals": round(available_before_goals, 2),
        "total_goal_monthly_targets": round(total_goal_monthly_targets, 2),
        "available_after_goals": round(available_after_goals, 2)
    }


@budget_bp.route("/budget-items", methods=["GET"])
@jwt_required()
def get_budget_items():
    user_id = int(get_jwt_identity())

    budget_items = (
        BudgetItem.query
        .filter_by(user_id=user_id)
        .order_by(BudgetItem.item_type, BudgetItem.title)
        .all()
    )

    return jsonify({
        "budget_items": [item.to_dict() for item in budget_items],
        "summary": build_budget_summary(user_id)
    }), 200


@budget_bp.route("/budget-items", methods=["POST"])
@jwt_required()
def create_budget_item():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    title = data.get("title", "").strip()
    amount = data.get("amount")
    item_type = data.get("item_type")
    category = data.get("category", "")
    note = data.get("note", "")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if item_type not in ["income", "expense"]:
        return jsonify({"error": "Item type must be income or expense"}), 400

    if amount is None:
        return jsonify({"error": "Amount is required"}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Amount must be a number"}), 400

    if amount < 0:
        return jsonify({"error": "Amount cannot be negative"}), 400

    budget_item = BudgetItem(
        user_id=user_id,
        title=title,
        amount=amount,
        item_type=item_type,
        category=category.strip() if category else None,
        note=note.strip() if note else None,
        is_active=True
    )

    db.session.add(budget_item)
    db.session.commit()

    return jsonify({
        "message": "Budget item created successfully",
        "budget_item": budget_item.to_dict(),
        "summary": build_budget_summary(user_id)
    }), 201


@budget_bp.route("/budget-items/<int:item_id>", methods=["PATCH"])
@jwt_required()
def update_budget_item(item_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    budget_item = BudgetItem.query.filter_by(
        id=item_id,
        user_id=user_id
    ).first()

    if not budget_item:
        return jsonify({"error": "Budget item not found"}), 404

    if "title" in data:
        title = data["title"].strip()

        if not title:
            return jsonify({"error": "Title cannot be empty"}), 400

        budget_item.title = title

    if "amount" in data:
        try:
            amount = float(data["amount"])
        except ValueError:
            return jsonify({"error": "Amount must be a number"}), 400

        if amount < 0:
            return jsonify({"error": "Amount cannot be negative"}), 400

        budget_item.amount = amount

    if "item_type" in data:
        item_type = data["item_type"]

        if item_type not in ["income", "expense"]:
            return jsonify({"error": "Item type must be income or expense"}), 400

        budget_item.item_type = item_type

    if "category" in data:
        category = data["category"]
        budget_item.category = category.strip() if category else None

    if "note" in data:
        note = data["note"]
        budget_item.note = note.strip() if note else None

    if "is_active" in data:
        budget_item.is_active = bool(data["is_active"])

    db.session.commit()

    return jsonify({
        "message": "Budget item updated successfully",
        "budget_item": budget_item.to_dict(),
        "summary": build_budget_summary(user_id)
    }), 200


@budget_bp.route("/budget-items/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_budget_item(item_id):
    user_id = int(get_jwt_identity())

    budget_item = BudgetItem.query.filter_by(
        id=item_id,
        user_id=user_id
    ).first()

    if not budget_item:
        return jsonify({"error": "Budget item not found"}), 404

    db.session.delete(budget_item)
    db.session.commit()

    return jsonify({
        "message": "Budget item deleted successfully",
        "summary": build_budget_summary(user_id)
    }), 200
