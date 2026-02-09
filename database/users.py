"""
Tipikus Database - Users Module
================================
User management functions
"""

from typing import Optional, Dict, List
from .core import get_db


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    Get user by ID with all auth providers

    Returns:
        Dict with user info + 'auth_providers' list, or None
    """
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if not user:
        conn.close()
        return None

    user_dict = dict(user)

    # Get all auth providers for this user
    providers = conn.execute(
        'SELECT provider_type, email, last_used FROM auth_providers WHERE user_id = ?',
        (user_id,)
    ).fetchall()

    user_dict['auth_providers'] = [dict(p) for p in providers]
    conn.close()

    return user_dict


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_all_users() -> List[Dict]:
    """Get all users"""
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY display_name').fetchall()
    conn.close()
    return [dict(user) for user in users]


def create_user(display_name: str, email: Optional[str] = None,
                is_admin: bool = False, avatar_url: Optional[str] = None) -> int:
    """
    Create a new user (identity only, no auth provider)

    Returns:
        user_id
    """
    conn = get_db()

    cursor = conn.execute(
        '''INSERT INTO users (display_name, email, is_admin, avatar_url)
        VALUES (?, ?, ?, ?)''',
        (display_name, email, 1 if is_admin else 0, avatar_url)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id


def update_user(user_id: int, display_name: Optional[str] = None,
                email: Optional[str] = None, avatar_url: Optional[str] = None) -> bool:
    """Update user information"""
    conn = get_db()

    updates = []
    params = []

    if display_name is not None:
        updates.append('display_name = ?')
        params.append(display_name)

    if email is not None:
        updates.append('email = ?')
        params.append(email)

    if avatar_url is not None:
        updates.append('avatar_url = ?')
        params.append(avatar_url)

    if not updates:
        conn.close()
        return False

    params.append(user_id)

    conn.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    conn.close()

    return True


def delete_user(user_id: int):
    """
    Delete a user and all associated data

    CASCADE will automatically delete:
    - auth_providers
    - exercices_resultats

    Manual deletion needed for:
    - decks (and their mots, sessions)
    """
    conn = get_db()

    # Get all user's decks
    decks = conn.execute('SELECT id FROM decks WHERE user_id = ?', (user_id,)).fetchall()
    deck_ids = [deck['id'] for deck in decks]

    # Delete sessions for user's decks
    for deck_id in deck_ids:
        conn.execute('DELETE FROM sessions WHERE deck_id = ?', (deck_id,))

    # Delete words from user's decks
    for deck_id in deck_ids:
        conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))

    # Delete user's decks
    conn.execute('DELETE FROM decks WHERE user_id = ?', (user_id,))

    # Delete the user (CASCADE will handle auth_providers and exercices_resultats)
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))

    conn.commit()
    conn.close()


def get_user_by_name(name: str) -> Optional[Dict]:
    """Get user by display name (backward compatibility)"""
    conn = get_db()

    # Try exact match first
    user = conn.execute(
        'SELECT * FROM users WHERE display_name = ?',
        (name,)
    ).fetchone()

    # If not found, try case-insensitive
    if not user:
        user = conn.execute(
            'SELECT * FROM users WHERE LOWER(display_name) = LOWER(?)',
            (name,)
        ).fetchone()

    conn.close()
    return dict(user) if user else None


def mark_tour_completed(user_id: int) -> bool:
    """Mark the onboarding tour as completed for a user"""
    conn = get_db()
    conn.execute('UPDATE users SET tour_completed = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True


def mark_lesson_tour_completed(user_id: int) -> bool:
    """Mark the lesson tour as completed for a user"""
    conn = get_db()
    conn.execute('UPDATE users SET lesson_tour_completed = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True
