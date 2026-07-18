from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import Goal

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_dashboard():
    user_id = int(get_jwt_identity())

    goals = Goal.query.filter_by(user_id=user_id).all()

    total_goals = len(goals)
    active_goals = len([goal for goal in goals if goal.status == "active"])
    completed_goals = len([goal for goal in goals if goal.status == "completed"])

    total_target_amount = sum(goal.target_amount for goal in goals)
    total_saved_amount = sum(goal.saved_amount for goal in goals)

    overall_progress = 0

    if total_target_amount > 0:
        # Defensive capping keeps imported or legacy overfunded rows from showing
        # more than 100% aggregate progress.
        overall_progress = min(
            round((total_saved_amount / total_target_amount) * 100, 1),
            100
        )

    # Recalculate rather than summing the persisted compatibility column so the
    # dashboard reflects today's remaining time and savings.
    total_monthly_target = sum(
        goal.calculated_monthly_target()
        for goal in goals
        if goal.status == "active"
    )

    return jsonify({
        "summary": {
            "total_goals": total_goals,
            "active_goals": active_goals,
            "completed_goals": completed_goals,
            "total_target_amount": round(total_target_amount, 2),
            "total_saved_amount": round(total_saved_amount, 2),
            "overall_progress": overall_progress,
            "total_monthly_target": round(total_monthly_target, 2)
        },
        "goals": [
            goal.to_dict(include_contributions=False)
            for goal in goals
        ]
    }), 200
