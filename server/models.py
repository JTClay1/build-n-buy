from datetime import datetime
from extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Relationship: One User can have many Goals
    goals = db.relationship('Goal', backref='user', lazy=True, cascade="all, delete-orphan")

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
    target_amount = db.Column(db.Float, nullable=False)
    saved_amount = db.Column(db.Float, default=0.0)
    
    # Build Plan specific fields
    months_to_goal = db.Column(db.Integer, nullable=False)
    monthly_target = db.Column(db.Float, nullable=False)
    target_date = db.Column(db.DateTime, nullable=False)
    
    # Status: 'active', 'completed', or 'scrapped'
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: One Goal can have many Contributions
    contributions = db.relationship('Contribution', backref='goal', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Goal {self.item_name} - ${self.target_amount}>'

    def to_dict(self, include_contributions=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "item_name": self.item_name,
            "target_amount": self.target_amount,
            "saved_amount": self.saved_amount,
            "months_to_goal": self.months_to_goal,
            "monthly_target": self.monthly_target,
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