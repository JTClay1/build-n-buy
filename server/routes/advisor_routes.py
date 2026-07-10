from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json

from extensions import db
from models import BudgetItem, Goal, SmartAdvisorResponse

advisor_bp = Blueprint("advisor", __name__)


def format_currency(amount):
    return f"${float(amount or 0):,.2f}"


def build_budget_context(user_id):
    budget_items = BudgetItem.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()

    active_goals = Goal.query.filter_by(
        user_id=user_id,
        status="active"
    ).all()

    income_items = [
        item for item in budget_items if item.item_type == "income"
    ]

    expense_items = [
        item for item in budget_items if item.item_type == "expense"
    ]

    monthly_income = sum(item.amount for item in income_items)
    monthly_expenses = sum(item.amount for item in expense_items)

    total_goal_monthly_targets = sum(
        goal.calculated_monthly_target() for goal in active_goals
    )

    available_before_goals = monthly_income - monthly_expenses
    available_after_goals = available_before_goals - total_goal_monthly_targets

    return {
        "has_budget_items": len(budget_items) > 0,
        "summary": {
            "monthly_income": round(monthly_income, 2),
            "monthly_expenses": round(monthly_expenses, 2),
            "available_before_goals": round(available_before_goals, 2),
            "total_goal_monthly_targets": round(total_goal_monthly_targets, 2),
            "available_after_goals": round(available_after_goals, 2)
        },
        "income_items": [
            item.to_dict() for item in income_items
        ],
        "expense_items": [
            item.to_dict() for item in expense_items
        ]
    }


def build_budget_recommendations(budget_context):
    recommendations = []
    action_items = []

    budget_summary = budget_context["summary"]

    if not budget_context["has_budget_items"]:
        recommendations.append(
            "Add monthly income and expense items to your profile so Smart Advisor can give better affordability advice."
        )
        action_items.append(
            "Go to Profile and add at least one income item and your major monthly expenses."
        )

        return recommendations, action_items

    available_after_goals = budget_summary["available_after_goals"]
    available_before_goals = budget_summary["available_before_goals"]
    total_goal_monthly_targets = budget_summary["total_goal_monthly_targets"]

    if available_after_goals < 0:
        recommendations.append(
            f"Your active goals currently exceed your budget context by about {format_currency(abs(available_after_goals))} per month."
        )
        recommendations.append(
            "Consider extending one or more target dates, pausing a lower-priority goal, or reducing expenses before adding another purchase goal."
        )
        action_items.append(
            "Review the goal with the highest monthly target and consider extending its deadline."
        )
    elif available_after_goals < 100:
        recommendations.append(
            f"Your budget has only about {format_currency(available_after_goals)} left after active goal targets, so there is not much cushion."
        )
        recommendations.append(
            "Avoid adding another aggressive goal unless you extend timelines or increase available monthly cash flow."
        )
        action_items.append(
            "Keep a small monthly cushion instead of assigning every available dollar to purchase goals."
        )
    else:
        recommendations.append(
            f"Based on your budget context, you have about {format_currency(available_after_goals)} left after monthly expenses and active goal targets."
        )
        action_items.append(
            "Use your available-after-goals number as the guardrail before adding or speeding up goals."
        )

    if total_goal_monthly_targets > 0 and available_before_goals > 0:
        goal_pressure_percentage = (
            total_goal_monthly_targets / available_before_goals
        ) * 100

        recommendations.append(
            f"Your active goals use about {round(goal_pressure_percentage, 1)}% of your available cash flow before goals."
        )

    return recommendations, action_items


def build_goal_advice(goal, message, budget_context):
    progress = goal.progress_percentage()
    remaining = goal.remaining_amount()
    months_left = goal.months_remaining()
    monthly_target = goal.calculated_monthly_target()

    budget_summary = budget_context["summary"]
    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

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

    if budget_context["has_budget_items"]:
        if budget_summary["available_after_goals"] < 0:
            recommendations.append(
                f"Budget warning: after expenses and active goals, your budget context is short by about {format_currency(abs(budget_summary['available_after_goals']))} per month."
            )
        elif monthly_target > budget_summary["available_before_goals"]:
            recommendations.append(
                f"This goal's monthly target is higher than your available cash flow before goals, so the timeline is probably too aggressive."
            )
        elif monthly_target > budget_summary["available_after_goals"] and budget_summary["available_after_goals"] > 0:
            recommendations.append(
                f"This goal's monthly target is larger than your remaining cushion after all goals, so speeding it up could strain your budget."
            )
        else:
            recommendations.append(
                "Your budget context does not show an immediate affordability problem for this goal."
            )

    recommendations.extend(budget_recommendations)

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

    action_items.extend(budget_action_items)

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
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "budget": budget_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation, not financial advice. "
            "Use it to compare tradeoffs before purchasing."
        )
    }


def build_dashboard_advice(goals, message, budget_context):
    active_goals = [goal for goal in goals if goal.status == "active"]
    completed_goals = [goal for goal in goals if goal.status == "completed"]

    budget_summary = budget_context["summary"]
    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

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
                "total_goals": 0,
                "budget": budget_context
            },
            "recommendations": [
                "Create one realistic starter goal.",
                "Choose a target date instead of guessing a monthly amount.",
                "Add a retailer so future price tracking can be more useful.",
                *budget_recommendations
            ],
            "action_items": [
                "Create your first goal.",
                "Add the target amount and target date.",
                "Make your first deposit.",
                *budget_action_items
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

    if budget_context["has_budget_items"]:
        recommendations.append(
            f"Your budget context shows {format_currency(budget_summary['available_before_goals'])} available before goals and {format_currency(budget_summary['available_after_goals'])} available after active goal targets."
        )

    recommendations.extend(budget_recommendations)

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

    action_items.extend(budget_action_items)

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
            "total_remaining": round(total_remaining, 2),
            "budget": budget_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation based on your saved goals and budget context, "
            "not financial advice."
        )
    }


def build_general_advice(message, budget_context):
    budget_summary = budget_context["summary"]
    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

    recommendations = [
        "Ask about a specific goal for the best advice.",
        "Use the dashboard context if you want help prioritizing multiple goals.",
        "Add target dates and retailers to make recommendations more useful."
    ]

    action_items = [
        "Open a goal and ask whether the timeline is realistic.",
        "Ask which goal should be prioritized from the dashboard.",
        "Compare cheaper and premium alternatives before buying."
    ]

    if budget_context["has_budget_items"]:
        recommendations.insert(
            0,
            f"Your budget context shows about {format_currency(budget_summary['available_after_goals'])} available after monthly expenses and active goal targets."
        )

    recommendations.extend(budget_recommendations)
    action_items.extend(budget_action_items)

    return {
        "summary": "I can help you compare purchase goals, adjust timelines, and think through smarter buying decisions using your saved budget context.",
        "context_used": {
            "type": "general",
            "budget": budget_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
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

    budget_context = build_budget_context(user_id)

    goal = None

    if context_type == "goal":
        if not goal_id:
            return jsonify({"error": "goal_id is required for goal context"}), 400

        goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

        if not goal:
            return jsonify({"error": "Goal not found"}), 404

        advisor_response = build_goal_advice(goal, message, budget_context)

    elif context_type == "dashboard":
        goals = Goal.query.filter_by(user_id=user_id).all()
        advisor_response = build_dashboard_advice(goals, message, budget_context)

    else:
        advisor_response = build_general_advice(message, budget_context)

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