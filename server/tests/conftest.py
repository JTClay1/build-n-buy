import os
from datetime import UTC, datetime, timedelta
from itertools import count
from math import ceil

import pytest
from flask_jwt_extended import create_access_token

# Importing app.py creates tables when DATABASE_URL is present. Tests must never
# inherit a developer's production connection string during collection.
os.environ.pop("DATABASE_URL", None)

from app import app as flask_app
from extensions import bcrypt, db
from models import Goal, User


@pytest.fixture()
def app():
    """Provide an isolated in-memory application and database per test."""
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        JWT_SECRET_KEY="unit-test-secret-that-is-at-least-32-bytes-long",
    )

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_factory(app):
    sequence = count(1)

    def create_user(
        *,
        username=None,
        email=None,
        password="password123",
        display_name=None,
    ):
        suffix = next(sequence)
        username = username or f"user{suffix}"
        email = email or f"user{suffix}@example.com"
        user = User(
            username=username,
            email=email,
            display_name=display_name or username,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()
        return user

    return create_user


@pytest.fixture()
def auth(user_factory):
    password = "password123"
    user = user_factory(password=password)
    token = create_access_token(identity=str(user.id))
    return {
        "user": user,
        "password": password,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture()
def goal_factory(app):
    sequence = count(1)

    def create_goal(
        *,
        user_id,
        target_amount=900.0,
        saved_amount=0.0,
        status="active",
        target_date=None,
        item_name=None,
    ):
        suffix = next(sequence)
        now = datetime.now(UTC).replace(tzinfo=None)
        target_date = target_date or now + timedelta(days=90)
        months_to_goal = max(ceil((target_date.date() - now.date()).days / 30), 1)
        goal = Goal(
            user_id=user_id,
            item_name=item_name or f"Goal {suffix}",
            target_amount=target_amount,
            saved_amount=saved_amount,
            months_to_goal=months_to_goal,
            monthly_target=round((target_amount - saved_amount) / months_to_goal, 2),
            target_date=target_date,
            status=status,
        )
        db.session.add(goal)
        db.session.commit()
        return goal

    return create_goal
