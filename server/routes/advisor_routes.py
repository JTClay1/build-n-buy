from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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


def build_price_context_for_goal(goal):
    active_prices = [
        retailer_price
        for retailer_price in goal.retailer_prices
        if retailer_price.is_active
    ]

    if not active_prices:
        return {
            "has_tracked_prices": False,
            "price_count": 0,
            "lowest_price": None,
            "highest_price": None,
            "preferred_price": None,
            "average_total_price": 0,
            "target_vs_lowest_difference": None,
            "preferred_vs_lowest_difference": None,
            "tracked_prices": []
        }

    lowest_price = min(
        active_prices,
        key=lambda retailer_price: retailer_price.total_price()
    )

    highest_price = max(
        active_prices,
        key=lambda retailer_price: retailer_price.total_price()
    )

    preferred_price = next(
        (
            retailer_price
            for retailer_price in active_prices
            if retailer_price.is_preferred
        ),
        None
    )

    average_total_price = sum(
        retailer_price.total_price() for retailer_price in active_prices
    ) / len(active_prices)

    preferred_vs_lowest_difference = None

    if preferred_price:
        preferred_vs_lowest_difference = round(
            preferred_price.total_price() - lowest_price.total_price(),
            2
        )

    return {
        "has_tracked_prices": True,
        "price_count": len(active_prices),
        "lowest_price": lowest_price.to_dict(),
        "highest_price": highest_price.to_dict(),
        "preferred_price": preferred_price.to_dict() if preferred_price else None,
        "average_total_price": round(average_total_price, 2),
        "target_vs_lowest_difference": round(
            goal.target_amount - lowest_price.total_price(),
            2
        ),
        "preferred_vs_lowest_difference": preferred_vs_lowest_difference,
        "tracked_prices": [
            retailer_price.to_dict() for retailer_price in active_prices
        ]
    }


def build_price_recommendations_for_goal(price_context):
    recommendations = []
    action_items = []

    if not price_context["has_tracked_prices"]:
        recommendations.append(
            "Add a few retailer prices for this goal so Smart Advisor can compare stores and spot better deals."
        )
        action_items.append(
            "Add prices from at least two stores on the goal detail page."
        )

        return recommendations, action_items

    lowest_price = price_context["lowest_price"]
    preferred_price = price_context["preferred_price"]
    target_vs_lowest_difference = price_context["target_vs_lowest_difference"]
    preferred_vs_lowest_difference = price_context["preferred_vs_lowest_difference"]

    recommendations.append(
        f"The lowest tracked price is {format_currency(lowest_price['total_price'])} at {lowest_price['retailer_name']}."
    )

    if preferred_price:
        if preferred_price["id"] == lowest_price["id"]:
            recommendations.append(
                f"Your preferred retailer, {preferred_price['retailer_name']}, is currently also the lowest tracked option."
            )
        elif preferred_vs_lowest_difference and preferred_vs_lowest_difference > 0:
            recommendations.append(
                f"{lowest_price['retailer_name']} is currently {format_currency(preferred_vs_lowest_difference)} cheaper than your preferred retailer, {preferred_price['retailer_name']}."
            )
        else:
            recommendations.append(
                "Your preferred retailer is close to the lowest tracked price, so compare return policy, warranty, and pickup/shipping convenience before choosing."
            )
    else:
        recommendations.append(
            "Mark one tracked store as preferred so Smart Advisor can compare your preferred retailer against the lowest price."
        )

    if target_vs_lowest_difference is not None:
        if target_vs_lowest_difference > 0:
            recommendations.append(
                f"Your goal target is {format_currency(target_vs_lowest_difference)} higher than the lowest tracked price, so you may be able to finish this goal sooner or keep the extra cushion."
            )
        elif target_vs_lowest_difference < 0:
            recommendations.append(
                f"The lowest tracked price is {format_currency(abs(target_vs_lowest_difference))} higher than your goal target, so consider updating the target amount."
            )
        else:
            recommendations.append(
                "Your goal target matches the current lowest tracked price."
            )

    action_items.append(
        "Verify the lowest price still includes shipping, tax, and the correct product version before buying."
    )

    if price_context["price_count"] < 3:
        action_items.append(
            "Add one more retailer price to make the comparison more reliable."
        )

    return recommendations, action_items


def build_dashboard_price_context(goals):
    active_goals = [goal for goal in goals if goal.status == "active"]

    goal_price_contexts = []

    for goal in active_goals:
        price_context = build_price_context_for_goal(goal)

        if price_context["has_tracked_prices"]:
            goal_price_contexts.append({
                "goal_id": goal.id,
                "item_name": goal.item_name,
                "monthly_target": goal.calculated_monthly_target(),
                "price_context": price_context
            })

    potential_preferred_savings = 0

    for goal_context in goal_price_contexts:
        difference = goal_context["price_context"]["preferred_vs_lowest_difference"]

        if difference and difference > 0:
            potential_preferred_savings += difference

    goals_with_target_cushion = [
        goal_context
        for goal_context in goal_price_contexts
        if goal_context["price_context"]["target_vs_lowest_difference"] is not None
        and goal_context["price_context"]["target_vs_lowest_difference"] > 0
    ]

    goals_with_target_cushion.sort(
        key=lambda goal_context: goal_context["price_context"]["target_vs_lowest_difference"],
        reverse=True
    )

    return {
        "goals_with_prices": len(goal_price_contexts),
        "potential_preferred_savings": round(potential_preferred_savings, 2),
        "goals_with_target_cushion": goals_with_target_cushion[:3],
        "goal_price_contexts": goal_price_contexts
    }


def build_dashboard_price_recommendations(price_context):
    recommendations = []
    action_items = []

    if price_context["goals_with_prices"] == 0:
        recommendations.append(
            "None of your active goals have tracked store prices yet."
        )
        action_items.append(
            "Open your highest-priority goal and add prices from at least two retailers."
        )

        return recommendations, action_items

    recommendations.append(
        f"{price_context['goals_with_prices']} active goal(s) have tracked retailer prices."
    )

    if price_context["potential_preferred_savings"] > 0:
        recommendations.append(
            f"You could save about {format_currency(price_context['potential_preferred_savings'])} by choosing the current lowest tracked stores instead of preferred retailers."
        )

    if price_context["goals_with_target_cushion"]:
        best_cushion_goal = price_context["goals_with_target_cushion"][0]
        cushion = best_cushion_goal["price_context"]["target_vs_lowest_difference"]

        recommendations.append(
            f"{best_cushion_goal['item_name']} has the biggest target cushion: its goal target is {format_currency(cushion)} above the lowest tracked price."
        )

    action_items.append(
        "Review tracked prices before adding extra savings to a goal."
    )

    return recommendations, action_items


def build_goal_advice(goal, message, budget_context, price_context):
    progress = goal.progress_percentage()
    remaining = goal.remaining_amount()
    months_left = goal.months_remaining()
    monthly_target = goal.calculated_monthly_target()

    budget_summary = budget_context["summary"]

    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

    price_recommendations, price_action_items = build_price_recommendations_for_goal(
        price_context
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
                "This goal's monthly target is higher than your available cash flow before goals, so the timeline is probably too aggressive."
            )
        elif (
            monthly_target > budget_summary["available_after_goals"]
            and budget_summary["available_after_goals"] > 0
        ):
            recommendations.append(
                "This goal's monthly target is larger than your remaining cushion after all goals, so speeding it up could strain your budget."
            )
        else:
            recommendations.append(
                "Your budget context does not show an immediate affordability problem for this goal."
            )

    recommendations.extend(budget_recommendations)
    recommendations.extend(price_recommendations)

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
    action_items.extend(price_action_items)

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
            "budget": budget_context,
            "prices": price_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation, not financial advice. "
            "Use it to compare tradeoffs before purchasing."
        )
    }


def build_dashboard_advice(goals, message, budget_context, price_context):
    active_goals = [goal for goal in goals if goal.status == "active"]
    completed_goals = [goal for goal in goals if goal.status == "completed"]

    budget_summary = budget_context["summary"]

    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

    price_recommendations, price_action_items = build_dashboard_price_recommendations(
        price_context
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
                "budget": budget_context,
                "prices": price_context
            },
            "recommendations": [
                "Create one realistic starter goal.",
                "Choose a target date instead of guessing a monthly amount.",
                "Add a retailer so future price tracking can be more useful.",
                *budget_recommendations,
                *price_recommendations
            ],
            "action_items": [
                "Create your first goal.",
                "Add the target amount and target date.",
                "Make your first deposit.",
                *budget_action_items,
                *price_action_items
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
    recommendations.extend(price_recommendations)

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
    action_items.extend(price_action_items)

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
            "budget": budget_context,
            "prices": price_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": (
            "This is a planning recommendation based on your saved goals, budget context, and tracked prices, "
            "not financial advice."
        )
    }


def build_general_advice(message, budget_context, price_context):
    budget_summary = budget_context["summary"]

    budget_recommendations, budget_action_items = build_budget_recommendations(
        budget_context
    )

    price_recommendations, price_action_items = build_dashboard_price_recommendations(
        price_context
    )

    recommendations = [
        "Ask about a specific goal for the best advice.",
        "Use the dashboard context if you want help prioritizing multiple goals.",
        "Add target dates, retailers, and tracked prices to make recommendations more useful."
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
    recommendations.extend(price_recommendations)

    action_items.extend(budget_action_items)
    action_items.extend(price_action_items)

    return {
        "summary": "I can help you compare purchase goals, adjust timelines, compare tracked store prices, and think through smarter buying decisions.",
        "context_used": {
            "type": "general",
            "budget": budget_context,
            "prices": price_context
        },
        "recommendations": recommendations,
        "action_items": action_items,
        "advisor_note": "This is a planning recommendation, not financial advice."
    }


def build_rule_based_advisor_response(user_id, message, context_type, goal_id):
    budget_context = build_budget_context(user_id)

    all_user_goals = Goal.query.filter_by(user_id=user_id).all()
    dashboard_price_context = build_dashboard_price_context(all_user_goals)

    goal = None

    if context_type == "goal":
        if not goal_id:
            return None, None, ("goal_id is required for goal context", 400)

        goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

        if not goal:
            return None, None, ("Goal not found", 404)

        goal_price_context = build_price_context_for_goal(goal)

        advisor_response = build_goal_advice(
            goal,
            message,
            budget_context,
            goal_price_context
        )

    elif context_type == "dashboard":
        advisor_response = build_dashboard_advice(
            all_user_goals,
            message,
            budget_context,
            dashboard_price_context
        )

    else:
        advisor_response = build_general_advice(
            message,
            budget_context,
            dashboard_price_context
        )

    advisor_response["response_source"] = "rule_based"

    return advisor_response, goal, None


def get_response_text(openai_response):
    if hasattr(openai_response, "output_text") and openai_response.output_text:
        return openai_response.output_text

    try:
        response_dict = openai_response.model_dump()
    except AttributeError:
        return ""

    output_items = response_dict.get("output", [])

    for output_item in output_items:
        content_items = output_item.get("content", [])

        for content_item in content_items:
            if content_item.get("type") in ["output_text", "text"]:
                return content_item.get("text", "")

    return ""


def normalize_string_list(value, fallback_items, max_items=6):
    if not isinstance(value, list):
        return fallback_items[:max_items]

    cleaned_items = []

    for item in value:
        if isinstance(item, str) and item.strip():
            cleaned_items.append(item.strip())

    if not cleaned_items:
        return fallback_items[:max_items]

    return cleaned_items[:max_items]


def build_ai_advisor_response(message, context_type, rule_based_response):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_ADVISOR_MODEL", "gpt-5.6-luna")

    if not api_key or OpenAI is None:
        return None

    client = OpenAI(api_key=api_key, timeout=25)

    payload = {
        "user_message": message,
        "context_type": context_type,
        "rule_based_response": rule_based_response
    }

    system_prompt = """
You are Smart Advisor for Build n' Buy, a save-first purchase planning app.

Use the provided backend context as the source of truth.
Do not invent goals, prices, income, expenses, stores, dates, or savings amounts.
Do not tell the user to use credit cards, debt, loans, financing, or buy-now-pay-later.
Keep the advice practical, concise, and friendly.
The tone should sound human, not like a spreadsheet.
Mention tracked prices and retailer differences when relevant.
Mention budget pressure when relevant.
Return JSON only.

Required JSON shape:
{
  "summary": "string",
  "recommendations": ["string"],
  "action_items": ["string"],
  "advisor_note": "string"
}
"""

    user_prompt = json.dumps(payload, default=str)

    try:
        openai_response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "build_n_buy_advisor_response",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "summary",
                            "recommendations",
                            "action_items",
                            "advisor_note"
                        ],
                        "properties": {
                            "summary": {
                                "type": "string"
                            },
                            "recommendations": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 6,
                                "items": {
                                    "type": "string"
                                }
                            },
                            "action_items": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 5,
                                "items": {
                                    "type": "string"
                                }
                            },
                            "advisor_note": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            max_output_tokens=900
        )

        response_text = get_response_text(openai_response)

        if not response_text:
            return None

        ai_response = json.loads(response_text)

        fallback_recommendations = rule_based_response.get("recommendations", [])
        fallback_action_items = rule_based_response.get("action_items", [])

        return {
            "summary": ai_response.get(
                "summary",
                rule_based_response.get("summary", "")
            ),
            "recommendations": normalize_string_list(
                ai_response.get("recommendations"),
                fallback_recommendations,
                max_items=6
            ),
            "action_items": normalize_string_list(
                ai_response.get("action_items"),
                fallback_action_items,
                max_items=5
            ),
            "advisor_note": ai_response.get(
                "advisor_note",
                rule_based_response.get(
                    "advisor_note",
                    "This is a planning recommendation, not financial advice."
                )
            )
        }

    except Exception as error:
        print(f"OpenAI advisor fallback used: {error}")
        return None


def merge_ai_response(rule_based_response, ai_response):
    if not ai_response:
        return rule_based_response

    return {
        "summary": ai_response["summary"],
        "context_used": rule_based_response["context_used"],
        "recommendations": ai_response["recommendations"],
        "action_items": ai_response["action_items"],
        "advisor_note": ai_response["advisor_note"],
        "response_source": "openai"
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

    rule_based_response, goal, error_result = build_rule_based_advisor_response(
        user_id,
        message,
        context_type,
        goal_id
    )

    if error_result:
        error_message, status_code = error_result
        return jsonify({"error": error_message}), status_code

    ai_response = build_ai_advisor_response(
        message,
        context_type,
        rule_based_response
    )

    advisor_response = merge_ai_response(
        rule_based_response,
        ai_response
    )

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