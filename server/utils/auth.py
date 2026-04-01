from flask_jwt_extended import create_access_token
from datetime import timedelta

def generate_token(user_id):
    """
    Generates a JWT for a given user ID, valid for 24 hours.
    """
    # We encode the user's database ID inside the token as the 'identity'.
    # A 24-hour expiration is standard for a web app MVP.
    return create_access_token(
        identity=str(user_id), 
        expires_delta=timedelta(hours=24)
    )