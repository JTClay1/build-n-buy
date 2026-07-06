from datetime import datetime
from math import ceil
from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship: One User can have many Goals
    goals = db.relationship(
        'Goal',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    item_name = db.Column(db.String(100), nullable=False)
    retailer = db.Column(db.String(120))
    target_amount = db.Column(db.Float, nullable=False)
    saved_amount = db.Column(db.Float, default=0.0)

    # Build Plan specific fields
    # months_to_goal is kept for backwards compatibility, but target_date is now
    # the source of truth for timeline calculations.
    months_to_goal = db.Column(db.Integer, nullable=False)
    monthly_target = db.Column(db.Float, nullable=False)
    target_date = db.Column(db.DateTime, nullable=False)

    # Status: 'active', 'completed', or 'scrapped'
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: One Goal can have many Contributions
    contributions = db.relationship(
        'Contribution',
        backref='goal',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Goal {self.item_name} - ${self.target_amount}>'

    def remaining_amount(self):
        return max(self.target_amount - self.saved_amount, 0)

    def progress_percentage(self):
        if self.target_amount <= 0:
            return 0

        progress = (self.saved_amount / self.target_amount) * 100
        return min(round(progress, 1), 100)

    def months_remaining(self):
        if not self.target_date:
            return max(self.months_to_goal or 1, 1)

        today = datetime.utcnow().date()
        target_day = self.target_date.date()
        days_remaining = (target_day - today).days

        if days_remaining <= 0:
            return 0

        return ceil(days_remaining / 30)

    def calculated_monthly_target(self):
        if self.status == "completed":
            return 0.0

        remaining = self.remaining_amount()

        if remaining <= 0:
            return 0.0

        months_left = self.months_remaining()

        if months_left <= 0:
            return round(remaining, 2)

        return round(remaining / months_left, 2)

    def to_dict(self, include_contributions=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "item_name": self.item_name,
            "retailer": self.retailer,
            "target_amount": self.target_amount,
            "saved_amount": self.saved_amount,
            "remaining_amount": self.remaining_amount(),
            "progress_percentage": self.progress_percentage(),

            # Legacy field, still included so old frontend/backend code does not break
            "months_to_goal": self.months_to_goal,

            # New date-based timeline fields
            "months_remaining": self.months_remaining(),
            "monthly_target": self.calculated_monthly_target(),
            "target_date": self.target_date.isoformat() if self.target_date else None,

            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if include_contributions:
            data["contributions"] = [
                contribution.to_dict() for contribution in self.contributions
            ]

        return data


class Contribution(db.Model):
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    contribution_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Contribution ${self.amount} to Goal {self.goal_id}>'

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "amount": self.amount,
            "note": self.note,
            "contribution_date": self.contribution_date.isoformat() if self.contribution_date else None
        } 