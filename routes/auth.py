"""
Authentication Routes
=====================
Login, logout, OAuth, and password management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import verify_user_password, update_user_password, get_user_by_id, authenticate_local, authenticate_oauth

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login():
    """Login page"""
    # If already logged in, redirect to home
    if session.get('user_id'):
        return redirect(url_for('main.index'))

    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login_post():
    """Process login"""
    nom = request.form.get('nom', '').strip()
    password = request.form.get('password', '').strip()

    if not nom or not password:
        flash('Username and password required')
        return redirect(url_for('auth.login'))

    # Verify credentials
    user = verify_user_password(nom, password)

    if not user:
        flash('Incorrect username or password')
        return redirect(url_for('auth.login'))

    # Successful login
    session.clear()
    session.permanent = True
    session['user_id'] = user['id']
    session['user_name'] = user['nom']
    session['is_admin'] = user.get('is_admin', False)
    session.modified = True

    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET'])
def change_password():
    """Password change page"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = get_user_by_id(user_id)
    return render_template('change_password.html', user=user)


@auth_bp.route('/change-password', methods=['POST'])
def change_password_post():
    """Process password change"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')

    if not user_id:
        return redirect(url_for('auth.login'))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Validations
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required')
        return redirect(url_for('auth.change_password'))

    # Verify current password
    user = verify_user_password(user_name, current_password)
    if not user:
        flash('Current password is incorrect')
        return redirect(url_for('auth.change_password'))

    # Check that new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match')
        return redirect(url_for('auth.change_password'))

    # Check length
    if len(new_password) < 4:
        flash('Password must be at least 4 characters')
        return redirect(url_for('auth.change_password'))

    # Update password
    update_user_password(user_id, new_password)

    flash('Password changed successfully!')
    return redirect(url_for('main.index'))


# ========== OAUTH ROUTES ==========

@auth_bp.route('/login/google')
def login_google():
    """Initiate Google OAuth flow"""
    from flask import current_app
    google = current_app.extensions['authlib.integrations.flask_client']['google']
    redirect_uri = url_for('auth.auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def auth_google_callback():
    """Google OAuth callback"""
    from flask import current_app

    try:
        google = current_app.extensions['authlib.integrations.flask_client']['google']
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Google authentication failed')
            return redirect(url_for('auth.login'))

        # Authenticate or create user
        user = authenticate_oauth(
            provider_type='google',
            provider_user_id=user_info['sub'],
            email=user_info['email'],
            display_name=user_info.get('name', user_info['email'].split('@')[0]),
            avatar_url=user_info.get('picture'),
            metadata={
                'locale': user_info.get('locale'),
                'verified_email': user_info.get('email_verified')
            }
        )

        # Set session
        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['display_name'] = user['display_name']
        session['email'] = user['email']
        session['is_admin'] = user['is_admin']
        session['avatar_url'] = user.get('avatar_url')
        session.modified = True

        flash(f'Welcome, {user["display_name"]}!')
        return redirect(url_for('main.index'))

    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash(f'Authentication error: {str(e)}')
        return redirect(url_for('auth.login'))


@auth_bp.route('/login/github')
def login_github():
    """Initiate GitHub OAuth flow"""
    from flask import current_app
    github = current_app.extensions['authlib.integrations.flask_client']['github']
    redirect_uri = url_for('auth.auth_github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/github/callback')
def auth_github_callback():
    """GitHub OAuth callback"""
    from flask import current_app

    try:
        github = current_app.extensions['authlib.integrations.flask_client']['github']
        token = github.authorize_access_token()

        # Get user info
        resp = github.get('user', token=token)
        user_info = resp.json()

        # Get primary email
        resp_emails = github.get('user/emails', token=token)
        emails = resp_emails.json()
        primary_email = next((e['email'] for e in emails if e['primary']), user_info.get('email'))

        if not primary_email:
            flash('Could not retrieve email from GitHub')
            return redirect(url_for('auth.login'))

        # Authenticate or create user
        user = authenticate_oauth(
            provider_type='github',
            provider_user_id=str(user_info['id']),
            email=primary_email,
            display_name=user_info.get('name') or user_info['login'],
            avatar_url=user_info.get('avatar_url'),
            metadata={
                'login': user_info['login'],
                'company': user_info.get('company'),
                'location': user_info.get('location')
            }
        )

        # Set session
        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['display_name'] = user['display_name']
        session['email'] = user['email']
        session['is_admin'] = user['is_admin']
        session['avatar_url'] = user.get('avatar_url')
        session.modified = True

        flash(f'Welcome, {user["display_name"]}!')
        return redirect(url_for('main.index'))

    except Exception as e:
        print(f"GitHub OAuth error: {e}")
        flash(f'Authentication error: {str(e)}')
        return redirect(url_for('auth.login'))


@auth_bp.route('/login/local', methods=['POST'])
def login_local():
    """Local authentication with email + password"""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash('Email and password required')
        return redirect(url_for('auth.login'))

    # Authenticate
    user = authenticate_local(email, password)

    if not user:
        flash('Incorrect email or password')
        return redirect(url_for('auth.login'))

    # Set session
    session.clear()
    session.permanent = True
    session['user_id'] = user['id']
    session['display_name'] = user['display_name']
    session['email'] = user['email']
    session['is_admin'] = user['is_admin']
    session['avatar_url'] = user.get('avatar_url')
    session.modified = True

    flash(f'Welcome back, {user["display_name"]}!')
    return redirect(url_for('main.index'))
