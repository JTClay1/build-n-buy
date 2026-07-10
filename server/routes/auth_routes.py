from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db, bcrypt
from models import User
from utils.auth import generate_token

# Create a Blueprint for our auth routes
auth_bp = Blueprint('auth', __name__)


def get_authenticated_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name')

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    username = username.strip()
    email = email.strip().lower()
    display_name = display_name.strip() if display_name else username

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(
        username=username,
        email=email,
        display_name=display_name,
        password_hash=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    token = generate_token(new_user.id)

    return jsonify({
        "message": "User created successfully",
        "token": token,
        "user": new_user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    email = email.strip().lower()

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        token = generate_token(user.id)

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": user.to_dict()
        }), 200

    return jsonify({"error": "Invalid email or password"}), 401


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user = get_authenticated_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": user.to_dict()
    }), 200


@auth_bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    user = get_authenticated_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    if "username" in data:
        username = data["username"].strip()

        if not username:
            return jsonify({"error": "Username cannot be empty"}), 400

        existing_user = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()

        if existing_user:
            return jsonify({"error": "Username already exists"}), 409

        user.username = username

    if "email" in data:
        email = data["email"].strip().lower()

        if not email:
            return jsonify({"error": "Email cannot be empty"}), 400

        existing_user = User.query.filter(
            User.email == email,
            User.id != user.id
        ).first()

        if existing_user:
            return jsonify({"error": "Email already exists"}), 409

        user.email = email

    if "display_name" in data:
        display_name = data["display_name"]

        if display_name:
            display_name = display_name.strip()

        user.display_name = display_name or None

    if "monthly_budget" in data:
        monthly_budget = data["monthly_budget"]

        if monthly_budget in ["", None]:
            user.monthly_budget = None
        else:
            try:
                monthly_budget = float(monthly_budget)
            except ValueError:
                return jsonify({"error": "Monthly budget must be a number"}), 400

            if monthly_budget < 0:
                return jsonify({"error": "Monthly budget cannot be negative"}), 400

            user.monthly_budget = monthly_budget

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "user": user.to_dict()
    }), 200


@auth_bp.route('/password', methods=['PATCH'])
@jwt_required()
def update_password():
    user = get_authenticated_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    if not bcrypt.check_password_hash(user.password_hash, current_password):
        return jsonify({"error": "Current password is incorrect"}), 401

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()

    return jsonify({
        "message": "Password updated successfully"
    }), 200