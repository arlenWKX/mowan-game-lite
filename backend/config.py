import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mowan-game-secret-key-2024'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'mowan-jwt-secret-key-2024'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    DATABASE = os.path.join(os.path.dirname(__file__), 'mowan_game.db')
    DEBUG = True