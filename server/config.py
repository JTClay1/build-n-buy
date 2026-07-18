import os

class Config:
    # SQLite keeps local setup zero-configuration; deployments override this
    # with their managed database connection string.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # The checked-in value is development-only. Production must inject a stable,
    # private secret so issued tokens survive restarts and cannot be forged.
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-dev-key-change-later')
