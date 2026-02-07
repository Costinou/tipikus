"""
Tipikus Routes Package
======================
Blueprint registration for modular Flask application
"""

from .auth import auth_bp
from .admin import admin_bp
from .main import main_bp
from .lessons import lessons_bp
from .decks import decks_bp
from .exercises import exercises_bp
from .api import api_bp
from .stats import stats_bp


def register_blueprints(app):
    """Register all application blueprints"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(lessons_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stats_bp)


__all__ = [
    'auth_bp',
    'admin_bp',
    'main_bp',
    'lessons_bp',
    'decks_bp',
    'exercises_bp',
    'api_bp',
    'stats_bp',
    'register_blueprints'
]
