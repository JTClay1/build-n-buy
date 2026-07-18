from extensions import db
from models import Contribution


def add_activity(client, headers, goal_id, amount, entry_type="deposit", note=None):
    return client.post(
        f"/api/goals/{goal_id}/contributions",
        headers=headers,
        json={"amount": amount, "entry_type": entry_type, "note": note},
    )


def test_deposit_updates_progress_and_completes_goal(client, auth, goal_factory):
    goal = goal_factory(user_id=auth["user"].id, target_amount=500)

    first = add_activity(client, auth["headers"], goal.id, 125, note="Payday")
    assert first.status_code == 201
    assert first.get_json()["contribution"]["signed_amount"] == 125.0
    assert first.get_json()["contribution"]["note"] == "Payday"
    assert first.get_json()["goal"]["saved_amount"] == 125.0
    assert first.get_json()["goal"]["progress_percentage"] == 25.0

    completed = add_activity(client, auth["headers"], goal.id, 375)
    assert completed.status_code == 201
    assert completed.get_json()["goal"]["saved_amount"] == 500.0
    assert completed.get_json()["goal"]["status"] == "completed"
    assert completed.get_json()["goal"]["monthly_target"] == 0.0


def test_withdrawal_reopens_completed_goal_and_cannot_overdraw(
    client, auth, goal_factory
):
    goal = goal_factory(
        user_id=auth["user"].id,
        target_amount=500,
        saved_amount=500,
        status="completed",
    )

    withdrawn = add_activity(
        client, auth["headers"], goal.id, 100, entry_type="withdrawal"
    )
    assert withdrawn.status_code == 201
    body = withdrawn.get_json()
    assert body["contribution"]["signed_amount"] == -100.0
    assert body["goal"]["saved_amount"] == 400.0
    assert body["goal"]["status"] == "active"

    overdrawn = add_activity(
        client, auth["headers"], goal.id, 401, entry_type="withdrawal"
    )
    assert overdrawn.status_code == 400
    assert overdrawn.get_json()["error"] == (
        "Withdrawal amount cannot be greater than saved amount"
    )


def test_contribution_rejects_invalid_activity(client, auth, goal_factory):
    goal = goal_factory(user_id=auth["user"].id)

    invalid_type = add_activity(
        client, auth["headers"], goal.id, 10, entry_type="refund"
    )
    zero_amount = add_activity(client, auth["headers"], goal.id, 0)
    non_numeric = add_activity(client, auth["headers"], goal.id, "many")

    assert invalid_type.status_code == 400
    assert invalid_type.get_json()["error"] == "Entry type must be deposit or withdrawal"
    assert zero_amount.status_code == 400
    assert zero_amount.get_json()["error"] == "Amount must be greater than zero"
    assert non_numeric.status_code == 400
    assert non_numeric.get_json()["error"] == "Amount must be a number"


def test_deleting_activity_reverses_its_effect(client, auth, goal_factory):
    goal = goal_factory(user_id=auth["user"].id)
    created = add_activity(client, auth["headers"], goal.id, 150)
    contribution_id = created.get_json()["contribution"]["id"]

    deleted = client.delete(
        f"/api/contributions/{contribution_id}", headers=auth["headers"]
    )

    assert deleted.status_code == 200
    assert deleted.get_json()["goal"]["saved_amount"] == 0.0
    assert db.session.get(Contribution, contribution_id) is None


def test_users_cannot_add_or_delete_activity_for_another_users_goal(
    client, auth, user_factory, goal_factory
):
    other_user = user_factory()
    other_goal = goal_factory(user_id=other_user.id, saved_amount=100)
    contribution = Contribution(
        goal_id=other_goal.id,
        amount=100,
        entry_type="deposit",
    )
    db.session.add(contribution)
    db.session.commit()

    create_response = add_activity(client, auth["headers"], other_goal.id, 25)
    delete_response = client.delete(
        f"/api/contributions/{contribution.id}", headers=auth["headers"]
    )

    assert create_response.status_code == 404
    assert delete_response.status_code == 404
    assert db.session.get(Contribution, contribution.id) is not None
