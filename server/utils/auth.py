from flask_jwt_extended import create_access_token
from datetime import timedelta

def generate_token(user_id):
    """
    Generates a JWT for a given user ID, valid for 24 hours.
    """
    # String identities satisfy flask-jwt-extended's subject requirements. The
    # bounded lifetime limits exposure while allowing a full day of normal use.
    return create_access_token(
        identity=str(user_id), 
        expires_delta=timedelta(hours=24)
    )
