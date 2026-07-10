from flask import Flask
from config import Config
from extensions import db, migrate, bcrypt, jwt, cors

# Import models so Flask-Migrate knows about them!
import models

app = Flask(__name__)
app.config.from_object(Config)

# Initialize all extensions with the app
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
jwt.init_app(app)
cors.init_app(app)

# Import Blueprints
from routes.auth_routes import auth_bp
from routes.goal_routes import goal_bp
from routes.contribution_routes import contribution_bp
from routes.dashboard_routes import dashboard_bp
from routes.advisor_routes import advisor_bp
from routes.notification_routes import notification_bp
from routes.budget_routes import budget_bp

# Register Blueprints with a URL prefix
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(goal_bp, url_prefix='/api/goals')
app.register_blueprint(contribution_bp, url_prefix="/api")
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(advisor_bp, url_prefix="/api")
app.register_blueprint(notification_bp, url_prefix="/api")
app.register_blueprint(budget_bp, url_prefix="/api")

# A simple health check route
@app.route('/')
def index():
    return {"message": "Welcome to the Build n' Buy API!"}

if __name__ == '__main__':
    app.run(port=5555, debug=True)