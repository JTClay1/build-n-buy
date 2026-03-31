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

class Contribution(db.Model):
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    contribution_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Contribution ${self.amount} to Goal {self.goal_id}>'