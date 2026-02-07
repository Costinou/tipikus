"""
Tipikus - Language Learning Platform
=====================================
Lightweight Flask application using modular blueprints

Main application file - all routes have been moved to routes/ package
"""

import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from database import init_db
from routes import register_blueprints

# Load environment variables
load_dotenv()

# Create Flask application
app = Flask(__name__)
app.secret_key = 'tipikus_secret_key_2024'

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 year
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ========== OAUTH CONFIGURATION ==========

# Initialize OAuth
oauth = OAuth(app)

# Google OAuth
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# GitHub OAuth
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Make OAuth clients available to blueprints
app.config['OAUTH_GOOGLE'] = google
app.config['OAUTH_GITHUB'] = github

# ========== BLUEPRINT REGISTRATION ==========

# Register all application blueprints
register_blueprints(app)

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def page_not_found(e):
    """Redirect 404 errors to index"""
    return redirect(url_for('main.index'))


# ========== APPLICATION INITIALIZATION ==========

if __name__ == '__main__':
    # Initialize database
    init_db()

    # Run application
    app.run(debug=True, host='0.0.0.0', port=5000)
