from app import app
from flask_migrate import upgrade


with app.app_context():
    print("Running database migrations...")
    upgrade()
    print("Database migrations complete.")