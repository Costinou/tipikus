"""
Tipikus Database - Authentication Module
=========================================
Authentication provider management and authentication functions
"""

import json
import sqlite3
from typing import Optional, Dict
from werkzeug.security import generate_password_hash, check_password_hash
from .core import get_db


# ========== AUTH PROVIDER MANAGEMENT ==========

def add_auth_provider(user_id: int, provider_type: str,
                      email: Optional[str] = None,
                      provider_user_id: Optional[str] = None,
                      password: Optional[str] = None,
                      metadata: Optional[Dict] = None) -> Optional[int]:
    """
    Add an authentication method to a user

    Args:
        user_id: The user to add auth to
        provider_type: 'local', 'google', 'github', etc.
        email: Email for this provider
        provider_user_id: ID from the OAuth provider
        password: Plain password (will be hashed) - only for 'local'
        metadata: Additional provider data as dict

    Returns:
        provider_id or None if already exists
    """
    conn = get_db()

    password_hash = None
    if password:
        password_hash = generate_password_hash(password)

    metadata_json = json.dumps(metadata) if metadata else None

    try:
        cursor = conn.execute(
            '''INSERT INTO auth_providers
            (user_id, provider_type, provider_user_id, email, password_hash, metadata, last_used)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (user_id, provider_type, provider_user_id, email, password_hash, metadata_json)
        )
        provider_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return provider_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def remove_auth_provider(user_id: int, provider_type: str) -> bool:
    """
    Remove an auth provider from a user

    Returns:
        True if removed, False if it was the last provider (can't remove)
    """
    conn = get_db()

    # Check user has at least 2 providers
    count = conn.execute(
        'SELECT COUNT(*) as count FROM auth_providers WHERE user_id = ?',
        (user_id,)
    ).fetchone()['count']

    if count <= 1:
        conn.close()
        return False  # Cannot remove last auth method

    conn.execute(
        'DELETE FROM auth_providers WHERE user_id = ? AND provider_type = ?',
        (user_id, provider_type)
    )
    conn.commit()
    conn.close()

    return True


def update_password(user_id: int, provider_type: str, new_password: str) -> bool:
    """Update password for a local auth provider"""
    conn = get_db()

    password_hash = generate_password_hash(new_password)

    result = conn.execute(
        '''UPDATE auth_providers
        SET password_hash = ?, last_used = CURRENT_TIMESTAMP
        WHERE user_id = ? AND provider_type = ?''',
        (password_hash, user_id, provider_type)
    )

    success = result.rowcount > 0
    conn.commit()
    conn.close()

    return success


# ========== AUTHENTICATION FUNCTIONS ==========

def authenticate_local(email: str, password: str) -> Optional[Dict]:
    """
    Authenticate with email + password

    Returns:
        User dict with keys: id, display_name, email, is_admin, avatar_url
        or None if authentication fails
    """
    conn = get_db()

    auth = conn.execute(
        '''SELECT ap.*, u.* FROM auth_providers ap
        JOIN users u ON ap.user_id = u.id
        WHERE ap.provider_type = 'local' AND ap.email = ?''',
        (email,)
    ).fetchone()

    if not auth:
        conn.close()
        return None

    auth_dict = dict(auth)

    if not check_password_hash(auth_dict['password_hash'], password):
        conn.close()
        return None

    # Update last_used and last_login
    conn.execute(
        'UPDATE auth_providers SET last_used = CURRENT_TIMESTAMP WHERE id = ?',
        (auth_dict['id'],)
    )
    conn.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
        (auth_dict['user_id'],)
    )
    conn.commit()
    conn.close()

    return {
        'id': auth_dict['user_id'],
        'display_name': auth_dict['display_name'],
        'email': auth_dict['email'],
        'is_admin': bool(auth_dict['is_admin']),
        'avatar_url': auth_dict.get('avatar_url')
    }


def authenticate_oauth(provider_type: str, provider_user_id: str,
                       email: str, display_name: str,
                       avatar_url: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict:
    """
    Authenticate or create user via OAuth provider

    Logic:
        1. Try to find existing auth by provider_type + provider_user_id
        2. If not found, try to find user by email
        3. If user exists, add new provider to existing user
        4. If user doesn't exist, create new user + provider

    Returns:
        User dict with keys: id, display_name, email, is_admin, avatar_url
    """
    conn = get_db()

    # Try to find existing auth
    auth = conn.execute(
        '''SELECT ap.*, u.* FROM auth_providers ap
        JOIN users u ON ap.user_id = u.id
        WHERE ap.provider_type = ? AND ap.provider_user_id = ?''',
        (provider_type, provider_user_id)
    ).fetchone()

    if auth:
        # Existing user - update last_used
        auth_dict = dict(auth)
        user_id = auth_dict['user_id']

        conn.execute(
            'UPDATE auth_providers SET last_used = CURRENT_TIMESTAMP WHERE id = ?',
            (auth_dict['id'],)
        )
        conn.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id,)
        )
        conn.commit()
        conn.close()

        return {
            'id': user_id,
            'display_name': auth_dict['display_name'],
            'email': auth_dict['email'],
            'is_admin': bool(auth_dict['is_admin']),
            'avatar_url': auth_dict.get('avatar_url')
        }

    # Try to find user by email
    user = conn.execute(
        'SELECT * FROM users WHERE email = ?',
        (email,)
    ).fetchone()

    if user:
        # Existing user, add new provider
        user_dict = dict(user)
        user_id = user_dict['id']
    else:
        # New user
        cursor = conn.execute(
            '''INSERT INTO users (display_name, email, avatar_url, last_login)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
            (display_name, email, avatar_url)
        )
        user_id = cursor.lastrowid

    # Add auth provider
    metadata_json = json.dumps(metadata) if metadata else None
    conn.execute(
        '''INSERT INTO auth_providers
        (user_id, provider_type, provider_user_id, email, metadata, last_used)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
        (user_id, provider_type, provider_user_id, email, metadata_json)
    )

    conn.commit()
    conn.close()

    return {
        'id': user_id,
        'display_name': display_name,
        'email': email,
        'is_admin': False,  # New users are never admin by default
        'avatar_url': avatar_url
    }


# ========== BACKWARD COMPATIBILITY HELPERS ==========

def verify_user_password(email: str, password: str) -> Optional[Dict]:
    """
    Legacy function for backward compatibility
    Now uses email instead of nom
    """
    return authenticate_local(email, password)


def update_user_password(user_id: int, new_password: str):
    """
    Legacy function for backward compatibility
    Updates the 'local' provider password
    """
    update_password(user_id, 'local', new_password)
