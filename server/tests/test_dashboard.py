from datetime import UTC, datetime, timedelta


def test_empty_dashboard_returns_zero_summary(client, auth):
    response = client.get("/api/dashboard", headers=auth["headers"])

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": {
            "total_goals": 0,
            "active_goals": 0,
            "completed_goals": 0,
            "total_target_amount": 0,
            "total_saved_amount": 0,
            "overall_progress": 0,
            "total_monthly_target": 0,
        },
        "goals": [],
    }


def test_dashboard_aggregates_only_the_authenticated_users_goals(
    client, auth, user_factory, goal_factory
):
    target_date = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=90)
    goal_factory(
        user_id=auth["user"].id,
        item_name="Active goal",
        target_amount=900,
        saved_amount=300,
        target_date=target_date,
    )
    goal_factory(
        user_id=auth["user"].id,
        item_name="Completed goal",
        target_amount=100,
        saved_amount=100,
        status="completed",
        target_date=target_date,
    )
    other_user = user_factory()
    goal_factory(
        user_id=other_user.id,
        target_amount=10_000,
        saved_amount=10_000,
        status="completed",
        target_date=target_date,
    )

    response = client.get("/api/dashboard", headers=auth["headers"])

    assert response.status_code == 200
    body = response.get_json()
    assert body["summary"] == {
        "total_goals": 2,
        "active_goals": 1,
        "completed_goals": 1,
        "total_target_amount": 1000.0,
        "total_saved_amount": 400.0,
        "overall_progress": 40.0,
        "total_monthly_target": 200.0,
    }
    assert {goal["item_name"] for goal in body["goals"]} == {
        "Active goal",
        "Completed goal",
    }
    assert all("contributions" not in goal for goal in body["goals"])


def test_dashboard_requires_authentication(client):
    response = client.get("/api/dashboard")

    assert response.status_code == 401
