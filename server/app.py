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

# Register Blueprints with a URL prefix
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# A simple health check route
@app.route('/')
def index():
    return {"message": "Welcome to the Build n' Buy API!"}

if __name__ == '__main__':
    app.run(port=5555, debug=True)