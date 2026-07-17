from app import app
from extensions import db

try:
    from flask_migrate import upgrade
except ImportError:
    upgrade = None


def run_deploy_tasks():
    with app.app_context():
        if upgrade and "migrate" in app.extensions:
            try:
                print("Running database migrations...")
                upgrade()
                print("Database migrations complete.")
                return
            except Exception as error:
                print(f"Migration failed, falling back to db.create_all(): {error}")

        print("Creating database tables with db.create_all()...")
        db.create_all()
        print("Database tables ready.")


if __name__ == "__main__":
    run_deploy_tasks()