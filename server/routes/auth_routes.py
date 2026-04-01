from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import User
from utils.auth import generate_token
from flask_jwt_extended import jwt_required, get_jwt_identity

# Create a Blueprint for our auth routes
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Basic validation to ensure they didn't send blank fields
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if a user with that email or username already exists
    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 409

    # Hash the password into a secure string
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Create the user and save to the database
    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    # Generate the JWT so they are instantly logged in upon signup
    token = generate_token(new_user.id)

    return jsonify({
        "message": "User created successfully",
        "token": token,
        "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    # Look up the user by their email
    user = User.query.filter_by(email=email).first()

    # If the user exists AND the password hashes match...
    if user and bcrypt.check_password_hash(user.password_hash, password):
        token = generate_token(user.id)
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email}
        }), 200

    # Return a generic 401 Unauthorized for bad credentials
    return jsonify({"error": "Invalid email or password"}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required() # This decorator acts as the bouncer! No token = no entry.
def get_current_user():
    # Extract the user ID that we encoded inside the token
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": {"id": user.id, "username": user.username, "email": user.email}
    }), 200