from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Goal, Notification

notification_bp = Blueprint("notifications", __name__)


@notification_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())

    # Bound the feed payload while calculating unread_count across the complete
    # user inbox so the badge remains accurate.
    notifications = (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )

    unread_count = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()

    return jsonify({
        "notifications": [
            notification.to_dict() for notification in notifications
        ],
        "unread_count": unread_count
    }), 200


@notification_bp.route("/notifications/demo", methods=["POST"])
@jwt_required()
def create_demo_notification():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    goal_id = data.get("goal_id")
    goal = None

    # A supplied goal must belong to the caller; otherwise the generic advisor
    # notification is used without attaching another user's data.
    if goal_id:
        goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()

        if not goal:
            return jsonify({"error": "Goal not found"}), 404

    if goal:
        title = "Price Watch Ready"
        message = (
            f"We will notify you when {goal.item_name} has a better price"
            f"{' at ' + goal.retailer if goal.retailer else ''}."
        )
        notification_type = "price_watch"
    else:
        title = "Smart Advisor Ready"
        message = (
            "Your Smart Buy Advisor can now surface alerts for sales, "
            "price updates, and goal planning reminders."
        )
        notification_type = "advisor"

    notification = Notification(
        user_id=user_id,
        goal_id=goal.id if goal else None,
        title=title,
        message=message,
        notification_type=notification_type
    )

    db.session.add(notification)
    db.session.commit()

    return jsonify({
        "message": "Demo notification created successfully",
        "notification": notification.to_dict()
    }), 201


@notification_bp.route("/notifications/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_notification_read(notification_id):
    user_id = int(get_jwt_identity())

    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()

    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    notification.mark_read()
    db.session.commit()

    unread_count = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()

    return jsonify({
        "message": "Notification marked as read",
        "notification": notification.to_dict(),
        "unread_count": unread_count
    }), 200


@notification_bp.route("/notifications/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_notifications_read():
    user_id = int(get_jwt_identity())

    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).all()

    for notification in notifications:
        notification.mark_read()

    db.session.commit()

    return jsonify({
        "message": "All notifications marked as read",
        "updated_count": len(notifications),
        "unread_count": 0
    }), 200
