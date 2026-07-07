from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json

from extensions import db
from models import Goal, SmartAdvisorResponse

advisor_bp = Blueprint("advisor", __name__)


def format_currency(amount):
    return f"${float(amount or 0):,.2f}"


def build_goal_advice(goal, message):
    progress = goal.progress_percentage()
    remaining = goal.remaining_amount()
    months_left = goal.months_remaining()
    monthly_target = goal.calculated_monthly_target()

    recommendations = []

    if progress >= 100:
        summary = f"{goal.item_name} is fully funded. You are ready to buy or compare final retailer options."
        recommendations.append(
            "Before purchasing, compare the final price, warranty, return policy, and any available discounts."
        )
    elif months_left <= 1:
        summary = (
            f"{goal.item_name} is close to the deadline. You still need "
            f"{format_currency(remaining)}, so this goal may need a short-term push."
        )
        recommendations.append(
            "Consider extending the target date unless this purchase is urgent."
        )
        recommendations.append(
            "Look for a cheaper alternative or sale if the monthly savings target feels too aggressive."
        )
    elif monthly_target > 250:
        summary = (
            f"{goal.item_name} has a fairly aggressive monthly target of "
            f"{format_currency(monthly_target)}."
        )
        recommendations.append(
            "Consider extending the target date by 1–3 months to lower monthly pressure."
        )
        recommendations.append(
            "Compare lower-cost alternatives before committing to this exact version."
        )
    else:
        summary = (
            f"{goal.item_name} looks realistic at about "
            f"{format_currency(monthly_target)} per month."
        )
        recommendations.append(
            "Stay on the current timeline if this monthly target fits your budget."
        )
        recommendations.append(
            "Set a small recurring contribution to keep progress consistent."
        )

    if goal.retailer:
        recommendations.append(
            f"Since your preferred retailer is {goal.retailer}, check that retailer first, then compare at least two other stores before buying."
        )
    else:
        recommendations.append(
            "Add a preferred retailer so future price tracking and sale alerts can be more useful."
        )

    recommendations.append(
        "If the purchase is flexible, wait for a sale before buying and keep saving in the meantime."
    )

    action_items = [
        f"Save {format_currency(monthly_target)} this month if possible.",
        "Review whether the target date still feels realistic.",
        "Compare at least one cheaper alternative and one premium alternative."
    ]

    return {
        "summary": summary,
        "context_used": {
            "type": "goal",
            "goal_id": goal.id,
            "item_name": goal.item_name,
            "retailer": goal.retailer,
            "target_amount": goal.target_amount,
            "saved_amount": goal.saved_amount,
            "remaining_amount": remaining,
            "progress_percentage": progress,
            "months_remaining": months_left,
            "monthly_target": monthly_target,
            "target_date": goal.target_date.isoformat() if goal.target_date else None
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation, not financial advice. "
            "Use it to compare tradeoffs before purchasing."
        )
    }


def build_dashboard_advice(goals, message):
    active_goals = [goal for goal in goals if goal.status == "active"]
    completed_goals = [goal for goal in goals if goal.status == "completed"]

    total_monthly_target = sum(
        goal.calculated_monthly_target()
        for goal in active_goals
    )

    total_remaining = sum(goal.remaining_amount() for goal in active_goals)

    if not goals:
        return {
            "summary": "You do not have any goals yet. Start by creating one purchase goal with a target date and retailer.",
            "context_used": {
                "type": "dashboard",
                "total_goals": 0
            },
            "recommendations": [
                "Create one realistic starter goal.",
                "Choose a target date instead of guessing a monthly amount.",
                "Add a retailer so future price tracking can be more useful."
            ],
            "action_items": [
                "Create your first goal.",
                "Add the target amount and target date.",
                "Make your first deposit."
            ],
            "advisor_note": "This is a planning recommendation, not financial advice."
        }

    highest_monthly_goal = None

    if active_goals:
        highest_monthly_goal = max(
            active_goals,
            key=lambda goal: goal.calculated_monthly_target()
        )

    recommendations = [
        f"Your active goals require about {format_currency(total_monthly_target)} per month combined.",
        f"You still have about {format_currency(total_remaining)} left to save across active goals."
    ]

    if highest_monthly_goal:
        recommendations.append(
            f"The goal putting the most pressure on your budget is {highest_monthly_goal.item_name} at about {format_currency(highest_monthly_goal.calculated_monthly_target())} per month."
        )

    if len(active_goals) >= 3:
        recommendations.append(
            "You may want to prioritize one or two goals instead of spreading savings across too many purchases."
        )
    else:
        recommendations.append(
            "Your number of active goals looks manageable. Keep monthly savings consistent."
        )

    action_items = [
        "Review the goal with the highest monthly target.",
        "Consider extending timelines for lower-priority purchases.",
        "Add retailers to any goals missing retailer details."
    ]

    return {
        "summary": (
            f"You have {len(active_goals)} active goal"
            f"{'' if len(active_goals) == 1 else 's'} and "
            f"{len(completed_goals)} completed goal"
            f"{'' if len(completed_goals) == 1 else 's'}."
        ),
        "context_used": {
            "type": "dashboard",
            "active_goals": len(active_goals),
            "completed_goals": len(completed_goals),
            "total_monthly_target": round(total_monthly_target, 2),
            "total_remaining": round(total_remaining, 2)
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation based on your saved goals, "
            "not financial advice."
        )
    }


def build_general_advice(message):
    return {
        "summary": "I can help you compare purchase goals, adjust timelines, and think through smarter buying decisions.",
        "context_used": {
            "type": "general"
        },
        "recommendations": [
            "Ask about a specific goal for the best advice.",
            "Use the dashboard context if you want help prioritizing multiple goals.",
            "Add target dates and retailers to make recommendations more useful."
        ],
        "action_items": [
            "Open a goal and ask whether the timeline is realistic.",
            "Ask which goal should be prioritized from the dashboard.",
            "Compare cheaper and premium alternatives before buying."
        ],
        "advisor_note": "This is a planning recommendation, not financial advice."
    }


@advisor_bp.route("/advisor", methods=["POST"])
@jwt_required()
def create_advisor_response():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    message = data.get("message", "").strip()
    context_type = data.get("context_type", "general")
    goal_id = data.get("goal_id")

    allowed_contexts = ["general", "goal", "dashboard"]

    if context_type not in allowed_contexts:
        return jsonify({"error": "Invalid advisor context type"}), 400

    if not message:
        return jsonify({"error": "Message is required"}), 400

    goal = None

    if context_type == "goal":
        if not goal_id:
            return jsonify({"error": "goal_id is required for goal context"}), 400

        goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

        if not goal:
            return jsonify({"error": "Goal not found"}), 404

        advisor_response = build_goal_advice(goal, message)

    elif context_type == "dashboard":
        goals = Goal.query.filter_by(user_id=user_id).all()
        advisor_response = build_dashboard_advice(goals, message)

    else:
        advisor_response = build_general_advice(message)

    saved_response = SmartAdvisorResponse(
        user_id=user_id,
        goal_id=goal.id if goal else None,
        context_type=context_type,
        user_message=message,
        response_json=json.dumps(advisor_response)
    )

    db.session.add(saved_response)
    db.session.commit()

    return jsonify({
        "message": "Advisor response created successfully",
        "advisor_response": saved_response.to_dict()
    }), 201


@advisor_bp.route("/advisor/history", methods=["GET"])
@jwt_required()
def get_advisor_history():
    user_id = int(get_jwt_identity())
    goal_id = request.args.get("goal_id")

    query = SmartAdvisorResponse.query.filter_by(user_id=user_id)

    if goal_id:
        query = query.filter_by(goal_id=goal_id)

    advisor_responses = (
        query
        .order_by(SmartAdvisorResponse.created_at.desc())
        .limit(20)
        .all()
    )

    return jsonify({
        "advisor_responses": [
            response.to_dict() for response in advisor_responses
        ]
    }), 200