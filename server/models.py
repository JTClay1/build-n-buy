from datetime import datetime
from math import ceil
import json

from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(80))
    monthly_budget = db.Column(db.Float)

    # User-owned records are lifecycle data: deleting an account should not leave
    # goals or advisor artifacts that can no longer be reached.
    goals = db.relationship(
        'Goal',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )

    advisor_responses = db.relationship(
        'SmartAdvisorResponse',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )

    notifications = db.relationship(
        'Notification',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )    

    budget_items = db.relationship(
        'BudgetItem',
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
            "email": self.email,
            "display_name": self.display_name,
            "monthly_budget": self.monthly_budget
        }


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    item_name = db.Column(db.String(100), nullable=False)
    retailer = db.Column(db.String(120))
    target_amount = db.Column(db.Float, nullable=False)
    saved_amount = db.Column(db.Float, default=0.0)

    # target_date is the planning source of truth. The two numeric fields remain
    # persisted for compatibility with older clients and migrations.
    months_to_goal = db.Column(db.Integer, nullable=False)
    monthly_target = db.Column(db.Float, nullable=False)
    target_date = db.Column(db.DateTime, nullable=False)

    # Route validation constrains this value to active, completed, or scrapped.
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Contributions and price/advisor records have no meaning after their goal is
    # removed, so the ORM owns and deletes them as one aggregate.
    contributions = db.relationship(
        'Contribution',
        backref='goal',
        lazy=True,
        cascade="all, delete-orphan"
    )

    advisor_responses = db.relationship(
        'SmartAdvisorResponse',
        backref='goal',
        lazy=True,
        cascade="all, delete-orphan"
    )
    retailer_prices = db.relationship(
        'RetailerPrice',
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
        # Older rows may predate target_date; retain a usable plan rather than
        # breaking serialization while those rows are migrated.
        if not self.target_date:
            return max(self.months_to_goal or 1, 1)

        today = datetime.utcnow().date()
        target_day = self.target_date.date()
        days_remaining = (target_day - today).days

        if days_remaining <= 0:
            return 0

        # The product defines a planning month as 30 days across API and UI.
        return ceil(days_remaining / 30)

    def calculated_monthly_target(self):
        if self.status == "completed":
            return 0.0

        remaining = self.remaining_amount()

        if remaining <= 0:
            return 0.0

        months_left = self.months_remaining()

        if months_left <= 0:
            # An overdue goal still needs the full remainder immediately.
            return round(remaining, 2)

        return round(remaining / months_left, 2)
    
    def lowest_retailer_price(self):
        # Disabled comparisons remain in history but cannot influence purchase
        # recommendations or the displayed best price.
        active_prices = [
            retailer_price
            for retailer_price in self.retailer_prices
            if retailer_price.is_active
        ]

        if not active_prices:
            return None

        return min(
            active_prices,
            key=lambda retailer_price: retailer_price.total_price()
        )

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

            # Preserve the legacy field while clients transition to date-based data.
            "months_to_goal": self.months_to_goal,

            # These values are derived at response time so aging goals stay current.
            "months_remaining": self.months_remaining(),
            "monthly_target": self.calculated_monthly_target(),
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "lowest_retailer_price": self.lowest_retailer_price().to_dict() if self.lowest_retailer_price() else None,

            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        # Summary endpoints can omit the nested ledger to keep dashboard payloads
        # small; detail endpoints use the complete representation by default.
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
    entry_type = db.Column(
        db.String(20),
        nullable=False,
        default="deposit",
        server_default="deposit"
    )
    note = db.Column(db.String(255))
    contribution_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Contribution {self.entry_type} ${self.amount} to Goal {self.goal_id}>'

    def signed_amount(self):
        # Store positive magnitudes in the database and expose direction separately
        # so totals can be reconstructed without negative input values.
        if self.entry_type == "withdrawal":
            return -self.amount

        return self.amount

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "amount": self.amount,
            "signed_amount": self.signed_amount(),
            "entry_type": self.entry_type,
            "note": self.note,
            "contribution_date": self.contribution_date.isoformat() if self.contribution_date else None
        }


class SmartAdvisorResponse(db.Model):
    __tablename__ = 'smart_advisor_responses'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=True)

    context_type = db.Column(db.String(30), nullable=False, default="general")
    user_message = db.Column(db.Text, nullable=False)
    response_json = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SmartAdvisorResponse user={self.user_id} context={self.context_type}>'

    def parsed_response(self):
        try:
            return json.loads(self.response_json)
        except json.JSONDecodeError:
            # Historical/plain-text rows remain readable even if their payload was
            # saved before structured advisor responses were introduced.
            return {
                "summary": self.response_json,
                "recommendations": [],
                "action_items": []
            }

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "goal_id": self.goal_id,
            "context_type": self.context_type,
            "user_message": self.user_message,
            "response": self.parsed_response(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=True)

    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.String(30),
        nullable=False,
        default="info",
        server_default="info"
    )

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Notification {self.title} user={self.user_id}>'

    def mark_read(self):
        # Keep the timestamp coupled to the flag for auditability and UI display.
        self.is_read = True
        self.read_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "goal_id": self.goal_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }
    
class BudgetItem(db.Model):
    __tablename__ = 'budget_items'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    # Route validation limits this discriminator to income or expense.
    item_type = db.Column(db.String(20), nullable=False)

    category = db.Column(db.String(80))
    note = db.Column(db.String(255))

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f'<BudgetItem {self.item_type} {self.title} ${self.amount}>'

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "amount": self.amount,
            "item_type": self.item_type,
            "category": self.category,
            "note": self.note,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
class RetailerPrice(db.Model):
    __tablename__ = 'retailer_prices'

    id = db.Column(db.Integer, primary_key=True)

    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)

    retailer_name = db.Column(db.String(120), nullable=False)
    product_url = db.Column(db.String(500))

    price = db.Column(db.Float, nullable=False)
    shipping_cost = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
        server_default="0"
    )
    tax_estimate = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
        server_default="0"
    )

    is_preferred = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1"
    )

    note = db.Column(db.String(255))

    last_checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f'<RetailerPrice {self.retailer_name} ${self.price} goal={self.goal_id}>'

    def total_price(self):
        # Comparisons use the checkout estimate, not the advertised shelf price.
        return round(
            float(self.price or 0)
            + float(self.shipping_cost or 0)
            + float(self.tax_estimate or 0),
            2
        )

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "retailer_name": self.retailer_name,
            "product_url": self.product_url,
            "price": self.price,
            "shipping_cost": self.shipping_cost,
            "tax_estimate": self.tax_estimate,
            "total_price": self.total_price(),
            "is_preferred": self.is_preferred,
            "is_active": self.is_active,
            "note": self.note,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
