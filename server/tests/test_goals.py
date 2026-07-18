from datetime import UTC, datetime, timedelta

import pytest

from extensions import db
from models import Goal


def future_date(days=90):
    return (datetime.now(UTC) + timedelta(days=days)).strftime("%Y-%m-%d")


def test_create_and_list_goal_calculates_savings_plan(client, auth):
    response = client.post(
        "/api/goals",
        headers=auth["headers"],
        json={
            "item_name": "  Gaming PC  ",
            "retailer": "  Local Store  ",
            "target_amount": "1200",
            "target_date": future_date(90),
        },
    )

    assert response.status_code == 201
    goal = response.get_json()["goal"]
    assert goal["item_name"] == "Gaming PC"
    assert goal["retailer"] == "Local Store"
    assert goal["target_amount"] == 1200.0
    assert goal["saved_amount"] == 0.0
    assert goal["months_remaining"] == 3
    assert goal["monthly_target"] == 400.0
    assert goal["progress_percentage"] == 0.0

    listed = client.get("/api/goals", headers=auth["headers"])
    assert listed.status_code == 200
    assert [item["id"] for item in listed.get_json()["goals"]] == [goal["id"]]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"target_amount": 100, "target_date": future_date()}, "Item name and target amount are required"),
        ({"item_name": "Laptop", "target_amount": 0, "target_date": future_date()}, "Item name and target amount are required"),
        ({"item_name": "Laptop", "target_amount": -1, "target_date": future_date()}, "Target amount must be greater than zero"),
        ({"item_name": "Laptop", "target_amount": 100, "target_date": "not-a-date"}, "Target date is required"),
        ({"item_name": "Laptop", "target_amount": 100, "target_date": "2000-01-01"}, "Target date must be in the future"),
    ],
)
def test_create_goal_rejects_invalid_inputs(client, auth, payload, message):
    response = client.post("/api/goals", headers=auth["headers"], json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == message


def test_update_goal_recalculates_timeline_and_validates_status(client, auth, goal_factory):
    goal = goal_factory(user_id=auth["user"].id, target_amount=600, saved_amount=120)

    response = client.patch(
        f"/api/goals/{goal.id}",
        headers=auth["headers"],
        json={"target_amount": 900, "target_date": future_date(180)},
    )

    assert response.status_code == 200
    updated = response.get_json()["goal"]
    assert updated["target_amount"] == 900.0
    assert updated["months_remaining"] == 6
    assert updated["monthly_target"] == 130.0

    invalid_status = client.patch(
        f"/api/goals/{goal.id}",
        headers=auth["headers"],
        json={"status": "paused"},
    )
    assert invalid_status.status_code == 400
    assert invalid_status.get_json()["error"] == "Invalid goal status"


def test_goal_routes_do_not_expose_another_users_goals(
    client, auth, user_factory, goal_factory
):
    other_user = user_factory()
    other_goal = goal_factory(user_id=other_user.id)

    get_response = client.get(
        f"/api/goals/{other_goal.id}", headers=auth["headers"]
    )
    update_response = client.patch(
        f"/api/goals/{other_goal.id}",
        headers=auth["headers"],
        json={"item_name": "Taken over"},
    )
    delete_response = client.delete(
        f"/api/goals/{other_goal.id}", headers=auth["headers"]
    )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    assert db.session.get(Goal, other_goal.id) is not None


def test_delete_goal_removes_it_from_the_users_list(client, auth, goal_factory):
    goal = goal_factory(user_id=auth["user"].id)

    deleted = client.delete(f"/api/goals/{goal.id}", headers=auth["headers"])
    listed = client.get("/api/goals", headers=auth["headers"])

    assert deleted.status_code == 200
    assert listed.get_json()["goals"] == []
