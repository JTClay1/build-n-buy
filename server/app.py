import os

from flask import Flask, make_response, request
from sqlalchemy import create_engine

from config import Config
from extensions import db, migrate, bcrypt, jwt, cors

# Import models so Flask-Migrate / SQLAlchemy metadata knows about them.
import models

app = Flask(__name__)
app.config.from_object(Config)

# Use Render/Postgres DATABASE_URL in production, keep local config as fallback.
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Render/Postgres URLs can use postgres://, but SQLAlchemy expects postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Frontend URL for production CORS.
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://build-n-buy.vercel.app",
]

if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

# Initialize extensions.
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
jwt.init_app(app)

cors.init_app(
    app,
    resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
        }
    },
    supports_credentials=True,
)

@app.before_request
def handle_cors_preflight():
    if request.method == "OPTIONS":
        response = make_response("", 204)
        return response


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"

    return response

# Import Blueprints.
from routes.auth_routes import auth_bp
from routes.goal_routes import goal_bp
from routes.contribution_routes import contribution_bp
from routes.dashboard_routes import dashboard_bp
from routes.advisor_routes import advisor_bp
from routes.notification_routes import notification_bp
from routes.budget_routes import budget_bp
from routes.price_routes import price_bp

# Register Blueprints.
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(goal_bp, url_prefix="/api/goals")
app.register_blueprint(contribution_bp, url_prefix="/api")
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(advisor_bp, url_prefix="/api")
app.register_blueprint(notification_bp, url_prefix="/api")
app.register_blueprint(budget_bp, url_prefix="/api")
app.register_blueprint(price_bp, url_prefix="/api")

# Production table creation for Render Postgres.
# This bypasses Flask-Migrate/Flask app-context issues and uses SQLAlchemy metadata directly.
if database_url:
    print("Ensuring production database tables exist...")

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])

    db.metadata.create_all(bind=engine)

    engine.dispose()

    print("Production database tables ready.")


@app.route("/")
def index():
    return {"message": "Welcome to the Build n' Buy API!"}


@app.route("/api/health")
def health_check():
    return {"status": "ok", "message": "Build n' Buy API is healthy"}


if __name__ == "__main__":
    app.run(port=5555, debug=True)