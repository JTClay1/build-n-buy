from app import app
from extensions import db, bcrypt
from models import User, Goal, Contribution
from datetime import datetime, timedelta

with app.app_context():
    print("Clearing database...")
    db.session.query(Contribution).delete()
    db.session.query(Goal).delete()
    db.session.query(User).delete()

    print("Seeding test user...")
    # Hash the password just like we will in the actual auth route
    hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
    test_user = User(username='testbuilder', email='test@buildnbuy.com', password_hash=hashed_pw)
    
    db.session.add(test_user)
    db.session.commit() # Commit so we can get the user.id

    print("Seeding test goal (Build Plan)...")
    # A 6-month build plan for an $800 GPU
    target_date = datetime.utcnow() + timedelta(days=6*30)
    
    gpu_goal = Goal(
        user_id=test_user.id,
        item_name='RTX 4070 Super',
        target_amount=800.0,
        saved_amount=133.33, # Reflects one month's payment
        months_to_goal=6,
        monthly_target=133.33,
        target_date=target_date,
        status='active'
    )
    
    db.session.add(gpu_goal)
    db.session.commit()

    print("Seeding test contribution...")
    first_payment = Contribution(
        goal_id=gpu_goal.id,
        amount=133.33,
        note='First month down!'
    )
    
    db.session.add(first_payment)
    db.session.commit()

    print("Database seeded successfully! 🌱")