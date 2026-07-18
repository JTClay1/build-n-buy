from models import User


def test_signup_normalizes_user_data_and_returns_token(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "username": "  builder  ",
            "email": "  Builder@Example.COM ",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "User created successfully"
    assert body["token"]
    assert body["user"] == {
        "id": 1,
        "username": "builder",
        "email": "builder@example.com",
        "display_name": "builder",
        "monthly_budget": None,
    }

    stored_user = User.query.one()
    assert stored_user.password_hash != "secret123"


def test_signup_rejects_missing_and_duplicate_credentials(client):
    missing = client.post(
        "/api/auth/signup",
        json={"username": "   ", "email": "person@example.com", "password": "secret123"},
    )
    assert missing.status_code == 400
    assert missing.get_json()["error"] == "Missing required fields"

    first = client.post(
        "/api/auth/signup",
        json={"username": "person", "email": "Person@Example.com", "password": "secret123"},
    )
    duplicate = client.post(
        "/api/auth/signup",
        json={"username": "someone-else", "email": "person@example.COM", "password": "secret123"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"] == "Email already exists"


def test_login_accepts_normalized_email_and_rejects_bad_password(client, user_factory):
    user = user_factory(email="owner@example.com", password="correct-password")

    success = client.post(
        "/api/auth/login",
        json={"email": " OWNER@EXAMPLE.COM ", "password": "correct-password"},
    )
    failure = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert success.status_code == 200
    assert success.get_json()["user"]["id"] == user.id
    assert success.get_json()["token"]
    assert failure.status_code == 401
    assert failure.get_json()["error"] == "Invalid email or password"


def test_profile_and_password_updates_require_valid_values(client, auth):
    unauthorized = client.get("/api/auth/me")
    assert unauthorized.status_code == 401

    profile = client.patch(
        "/api/auth/profile",
        headers=auth["headers"],
        json={
            "username": "new-name",
            "display_name": "  New Name  ",
            "monthly_budget": "1250.50",
        },
    )
    assert profile.status_code == 200
    assert profile.get_json()["user"]["username"] == "new-name"
    assert profile.get_json()["user"]["display_name"] == "New Name"
    assert profile.get_json()["user"]["monthly_budget"] == 1250.5

    invalid_budget = client.patch(
        "/api/auth/profile",
        headers=auth["headers"],
        json={"monthly_budget": -1},
    )
    assert invalid_budget.status_code == 400
    assert invalid_budget.get_json()["error"] == "Monthly budget cannot be negative"

    changed = client.patch(
        "/api/auth/password",
        headers=auth["headers"],
        json={"current_password": auth["password"], "new_password": "new-secret"},
    )
    assert changed.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": auth["user"].email, "password": auth["password"]},
    )
    new_login = client.post(
        "/api/auth/login",
        json={"email": auth["user"].email, "password": "new-secret"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
