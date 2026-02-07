"""
Tipikus Database Module - Multi-Provider Auth Version
======================================================

This module handles all database operations for the Tipikus application
with support for multiple authentication providers (local, Google, GitHub, etc.)

Database Schema:
    - users: User identity (display_name, email, is_admin, avatar_url)
    - auth_providers: Authentication methods (local password, OAuth providers)
    - decks, mots, sessions, lessons, exercices: Unchanged
"""

import sqlite3
import os
import json
from typing import Optional, Dict, List, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'tipikus.db'

# Available levels (unchanged)
AVAILABLE_LEVELS = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']


# ========== DATABASE CONNECTION ==========

def get_db():
    """Get database connection with Row factory"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with all necessary tables"""
    conn = get_db()
    
    # Users table (identity)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            email TEXT UNIQUE,
            avatar_url TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Auth providers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auth_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_type TEXT NOT NULL,
            provider_user_id TEXT,
            email TEXT,
            password_hash TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (provider_type, provider_user_id),
            UNIQUE (provider_type, email)
        )
    ''')
    
    # Indexes for auth_providers
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_user ON auth_providers(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_type ON auth_providers(provider_type)')
    
    # Lessons table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niveau TEXT NOT NULL,
            numero INTEGER NOT NULL,
            titre TEXT NOT NULL,
            content_markdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(niveau, numero)
        )
    ''')
    
    # Decks table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            niveau TEXT NOT NULL,
            is_commun BOOLEAN DEFAULT 0,
            lesson_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (lesson_id) REFERENCES lessons (id)
        )
    ''')
    
    # Words table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            mot_francais TEXT NOT NULL,
            traduction TEXT NOT NULL,
            FOREIGN KEY (deck_id) REFERENCES decks (id)
        )
    ''')
    
    # Sessions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type_session TEXT NOT NULL,
            date_session TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nombre_mots_vus INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            duree_secondes INTEGER DEFAULT 0,
            complete BOOLEAN DEFAULT 0,
            FOREIGN KEY (deck_id) REFERENCES decks (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Exercises table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            type_exercice TEXT NOT NULL,
            titre TEXT NOT NULL,
            description TEXT,
            ordre INTEGER DEFAULT 0,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    ''')
    
    # Exercise content table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercices_contenu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            contenu TEXT NOT NULL,
            ordre INTEGER DEFAULT 0,
            FOREIGN KEY (exercice_id) REFERENCES exercices (id) ON DELETE CASCADE
        )
    ''')
    
    # Exercise results table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercices_resultats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            temps_secondes INTEGER DEFAULT 0,
            complete BOOLEAN DEFAULT 0,
            date_completion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exercice_id) REFERENCES exercices (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


# ========== USER MANAGEMENT ==========

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


def get_user_by_name(name: str) -> Optional[Dict]:
    """
    Legacy function for backward compatibility
    Now searches by display_name
    """
    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE display_name = ?',
        (name,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


"""
Tipikus Database Module - Part 2
=================================
Decks, Lessons, Sessions, Stats, Exercises
"""

# ========== NIVEAU/LEVEL FUNCTIONS ==========

def get_niveaux_with_counts(user_id):
    """Returns a dictionary of levels with deck counts (common + personal)"""
    conn = get_db()
    
    # Count common decks + user's personal decks
    niveaux = conn.execute(
        '''SELECT niveau, COUNT(*) as count FROM decks 
        WHERE is_commun = 1 OR user_id = ?
        GROUP BY niveau ORDER BY niveau''', 
        (user_id,)
    ).fetchall()
    
    conn.close()
    return {niveau['niveau']: niveau['count'] for niveau in niveaux}


# ========== DECK FUNCTIONS ==========

def get_decks_by_niveau(niveau, user_id, include_in_lessons=False):
    """Returns all decks for a level
    
    For admin users (is_admin=True): ALL decks
    For others: common decks + their personal decks only
    """
    conn = get_db()
    
    # Check if user is admin
    user = get_user_by_id(user_id)
    is_admin = user and user.get('is_admin', False)
    
    if include_in_lessons:
        # Get ALL decks (including those in lessons)
        if is_admin:
            decks = conn.execute(
                '''SELECT d.*, u.display_name as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ?
                ORDER BY d.is_commun DESC, u.display_name, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            decks = conn.execute(
                '''SELECT d.*, u.display_name as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND (d.is_commun = 1 OR d.user_id = ?)
                ORDER BY d.is_commun DESC, d.nom''',
                (niveau, user_id)
            ).fetchall()
    else:
        # Get only decks OUTSIDE lessons
        if is_admin:
            decks = conn.execute(
                '''SELECT d.*, u.display_name as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND d.lesson_id IS NULL
                ORDER BY d.is_commun DESC, u.display_name, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            decks = conn.execute(
                '''SELECT d.*, u.display_name as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND (d.is_commun = 1 OR d.user_id = ?)
                AND d.lesson_id IS NULL
                ORDER BY d.is_commun DESC, d.nom''',
                (niveau, user_id)
            ).fetchall()
    
    conn.close()
    return [dict(deck) for deck in decks]


def create_deck(nom, niveau, user_id, is_commun=False):
    """Creates a new deck"""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO decks (nom, niveau, user_id, is_commun) VALUES (?, ?, ?, ?)',
        (nom, niveau, user_id, 1 if is_commun else 0)
    )
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deck_id


def get_deck_by_id(deck_id):
    """Returns a deck by ID"""
    conn = get_db()
    deck = conn.execute('SELECT * FROM decks WHERE id = ?', (deck_id,)).fetchone()
    conn.close()
    return dict(deck) if deck else None


def add_mots_to_deck(deck_id, mots_dict):
    """Adds words to a deck from a dictionary"""
    conn = get_db()
    
    # Clear old words from deck
    conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Add new words
    for mot_francais, traduction in mots_dict.items():
        conn.execute(
            'INSERT INTO mots (deck_id, mot_francais, traduction) VALUES (?, ?, ?)',
            (deck_id, mot_francais, traduction)
        )
    
    conn.commit()
    conn.close()


def get_mots_by_deck(deck_id):
    """Returns all words from a deck (randomized)"""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM mots WHERE deck_id = ? ORDER BY RANDOM()',
        (deck_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_mots_by_deck_ordered(deck_id):
    """Returns all words from a deck in alphabetical order"""
    conn = get_db()
    rows = conn.execute(
        'SELECT mot_francais, traduction FROM mots WHERE deck_id = ? ORDER BY mot_francais',
        (deck_id,)
    ).fetchall()
    conn.close()
    return {row['mot_francais']: row['traduction'] for row in rows}


def delete_deck(deck_id):
    """Deletes a deck and all associated words"""
    conn = get_db()
    
    # Delete words
    conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Delete sessions
    conn.execute('DELETE FROM sessions WHERE deck_id = ?', (deck_id,))
    
    # Delete deck
    conn.execute('DELETE FROM decks WHERE id = ?', (deck_id,))
    
    conn.commit()
    conn.close()


def can_delete_deck(deck_id, user_id):
    """Checks if a user can delete a deck"""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return False
    
    user = get_user_by_id(user_id)
    if not user:
        return False
    
    # Admin can delete anything
    if user.get('is_admin'):
        return True
    
    # User can delete their own personal decks
    if deck['user_id'] == user_id and not deck['is_commun']:
        return True
    
    return False


# ========== LESSON FUNCTIONS ==========

def get_lessons_by_niveau(niveau):
    """Returns all lessons for a level, sorted by number"""
    conn = get_db()
    lessons = conn.execute(
        '''SELECT l.*, COUNT(d.id) as nb_decks
        FROM lessons l
        LEFT JOIN decks d ON l.id = d.lesson_id
        WHERE l.niveau = ?
        GROUP BY l.id
        ORDER BY l.numero''',
        (niveau,)
    ).fetchall()
    conn.close()
    return [dict(lesson) for lesson in lessons]


def get_lesson_by_id(lesson_id):
    """Returns a lesson by ID"""
    conn = get_db()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    return dict(lesson) if lesson else None


def create_lesson(niveau, numero, titre, content_markdown):
    """Creates a new lesson"""
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO lessons (niveau, numero, titre, content_markdown) VALUES (?, ?, ?, ?)',
            (niveau, numero, titre, content_markdown)
        )
        lesson_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return lesson_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def update_lesson(lesson_id, titre, content_markdown):
    """Updates an existing lesson"""
    conn = get_db()
    conn.execute(
        'UPDATE lessons SET titre = ?, content_markdown = ? WHERE id = ?',
        (titre, content_markdown, lesson_id)
    )
    conn.commit()
    conn.close()


def delete_lesson(lesson_id):
    """Deletes a lesson (CASCADE will handle exercices)"""
    conn = get_db()
    # Detach decks from this lesson
    conn.execute('UPDATE decks SET lesson_id = NULL WHERE lesson_id = ?', (lesson_id,))
    # Delete the lesson
    conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
    conn.commit()
    conn.close()


def get_decks_by_lesson(lesson_id):
    """Returns all decks for a lesson"""
    conn = get_db()
    decks = conn.execute(
        'SELECT * FROM decks WHERE lesson_id = ? ORDER BY nom',
        (lesson_id,)
    ).fetchall()
    conn.close()
    return [dict(deck) for deck in decks]


def associate_deck_to_lesson(deck_id, lesson_id):
    """Associates a deck with a lesson"""
    conn = get_db()
    conn.execute('UPDATE decks SET lesson_id = ? WHERE id = ?', (lesson_id, deck_id))
    conn.commit()
    conn.close()


def detach_deck_from_lesson(deck_id):
    """Detaches a deck from its lesson"""
    conn = get_db()
    conn.execute('UPDATE decks SET lesson_id = NULL WHERE id = ?', (deck_id,))
    conn.commit()
    conn.close()


# ========== SESSION FUNCTIONS ==========

def create_session(deck_id, user_id, type_session, nombre_mots_vus, score, duree_secondes, complete):
    """Records a new learning session"""
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO sessions 
        (deck_id, user_id, type_session, nombre_mots_vus, score, duree_secondes, complete) 
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (deck_id, user_id, type_session, nombre_mots_vus, score, duree_secondes, complete)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_stats_deck(deck_id, user_id, days=30):
    """Calculates deck statistics for a specific user"""
    conn = get_db()
    
    stats = conn.execute(
        '''SELECT 
            COUNT(*) as total_sessions,
            SUM(nombre_mots_vus) as total_mots,
            SUM(CASE WHEN type_session = 'quiz' THEN score ELSE 0 END) as total_score,
            SUM(CASE WHEN type_session = 'quiz' THEN nombre_mots_vus ELSE 0 END) as total_questions_quiz,
            SUM(duree_secondes) as total_duree,
            AVG(duree_secondes) as duree_moyenne
        FROM sessions
        WHERE deck_id = ?
        AND user_id = ?
        AND date_session >= datetime('now', '-' || ? || ' days')''',
        (deck_id, user_id, days)
    ).fetchone()
    
    dernieres_sessions = conn.execute(
        '''SELECT type_session, duree_secondes, nombre_mots_vus, score, date_session
        FROM sessions
        WHERE deck_id = ?
        AND user_id = ?
        ORDER BY date_session DESC
        LIMIT 5''',
        (deck_id, user_id)
    ).fetchall()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(date_session) as jour
        FROM sessions
        WHERE deck_id = ?
        AND user_id = ?
        AND date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (deck_id, user_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['dernieres_sessions'] = [dict(row) for row in dernieres_sessions]
    result['jours_utilises'] = [row['jour'] for row in jours]
    
    return result


def get_stats_niveau(niveau, user_id, days=30):
    """Calculates level statistics for a user"""
    conn = get_db()
    
    stats = conn.execute(
        '''SELECT 
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
            SUM(s.duree_secondes) as total_duree,
            AVG(s.duree_secondes) as duree_moyenne
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.niveau = ?
        AND s.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (niveau, user_id, days)
    ).fetchone()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(s.date_session) as jour
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.niveau = ?
        AND s.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (niveau, user_id, days)
    ).fetchall()
    
    dernieres_sessions = conn.execute(
        '''SELECT 
            s.type_session,
            s.duree_secondes,
            s.nombre_mots_vus,
            s.score,
            s.date_session,
            s.complete,
            d.nom as deck_nom
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.niveau = ?
        AND s.user_id = ?
        ORDER BY s.date_session DESC
        LIMIT 10''',
        (niveau, user_id)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['jours_utilises'] = [row['jour'] for row in jours]
    result['dernieres_sessions'] = [dict(row) for row in dernieres_sessions]
    
    return result


def get_stats_globales(user_id, days=30):
    """Calculates global statistics for a user"""
    conn = get_db()
    
    stats = conn.execute(
        '''SELECT 
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
            SUM(s.duree_secondes) as total_duree
        FROM sessions s
        WHERE s.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (user_id, days)
    ).fetchone()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(date_session) as jour
        FROM sessions
        WHERE user_id = ?
        AND date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (user_id, days)
    ).fetchall()
    
    dernieres_sessions = conn.execute(
        '''SELECT 
            s.type_session,
            s.duree_secondes,
            s.nombre_mots_vus,
            s.score,
            s.date_session,
            s.complete,
            d.nom as deck_nom,
            d.niveau as niveau
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        ORDER BY s.date_session DESC
        LIMIT 10''',
        (user_id,)
    ).fetchall()
    
    stats_niveaux = conn.execute(
        '''SELECT 
            d.niveau,
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        GROUP BY d.niveau''',
        (user_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['jours_utilises'] = [row['jour'] for row in jours]
    result['dernieres_sessions'] = [dict(row) for row in dernieres_sessions]
    
    stats_par_niveau = {}
    for row in stats_niveaux:
        niveau = row['niveau']
        niveau_stats = get_stats_niveau(niveau, user_id, days)
        stats_par_niveau[niveau] = {
            'total_sessions': row['total_sessions'],
            'total_mots': row['total_mots'],
            'total_score': row['total_score'],
            'total_questions_quiz': row['total_questions_quiz'],
            'streak': calculer_streak(niveau_stats.get('jours_utilises', []))
        }
    
    result['stats_par_niveau'] = stats_par_niveau
    
    return result


def calculer_streak(jours_utilises):
    """Calculates the number of consecutive days of use"""
    if not jours_utilises:
        return 0
    
    from datetime import datetime, timedelta
    
    dates = [datetime.strptime(jour, '%Y-%m-%d').date() for jour in jours_utilises]
    dates.sort(reverse=True)
    
    streak = 1
    for i in range(len(dates) - 1):
        diff = (dates[i] - dates[i + 1]).days
        if diff == 1:
            streak += 1
        else:
            break
    
    return streak


def get_users_with_stats():
    """Returns all users with their statistics"""
    conn = get_db()
    
    users = get_all_users()
    users_stats = []
    
    for user in users:
        stats = conn.execute(
            '''SELECT 
                COUNT(*) as total_sessions,
                SUM(s.nombre_mots_vus) as total_mots_vus,
                SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
                SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
                MAX(s.date_session) as derniere_activite
            FROM sessions s
            WHERE s.user_id = ?''',
            (user['id'],)
        ).fetchone()
        
        jours = conn.execute(
            '''SELECT DISTINCT DATE(s.date_session) as jour
            FROM sessions s
            WHERE s.user_id = ?
            ORDER BY jour DESC''',
            (user['id'],)
        ).fetchall()
        
        streak = calculer_streak([row['jour'] for row in jours])
        
        total_quiz = stats['total_questions_quiz'] or 0
        taux_reussite = None
        if total_quiz > 0:
            taux_reussite = round((stats['total_score'] / total_quiz) * 100, 1)
        
        users_stats.append({
            'id': user['id'],
            'nom': user['display_name'],  # Changed from 'nom' to match new schema
            'total_sessions': stats['total_sessions'] or 0,
            'total_mots_vus': stats['total_mots_vus'] or 0,
            'streak': streak,
            'taux_reussite': taux_reussite,
            'derniere_activite': stats['derniere_activite'][:16] if stats['derniere_activite'] else None
        })
    
    conn.close()
    return users_stats


def get_recent_sessions(limit=10):
    """Returns the N most recent sessions"""
    conn = get_db()
    
    sessions = conn.execute(
        '''SELECT 
            s.id,
            s.date_session,
            s.type_session,
            s.nombre_mots_vus,
            s.score,
            s.duree_secondes,
            d.nom as deck_nom,
            u.display_name as user_nom
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        JOIN users u ON s.user_id = u.id
        ORDER BY s.date_session DESC
        LIMIT ?''',
        (limit,)
    ).fetchall()
    
    conn.close()
    return [dict(session) for session in sessions]


# ========== EXERCISE FUNCTIONS ==========

def create_exercice(lesson_id, type_exercice, titre, description='', ordre=0, config=None):
    """Creates a new exercise"""
    import json
    conn = get_db()
    
    config_json = json.dumps(config) if config else None
    
    cursor = conn.execute(
        '''INSERT INTO exercices (lesson_id, type_exercice, titre, description, ordre, config)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (lesson_id, type_exercice, titre, description, ordre, config_json)
    )
    exercice_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return exercice_id


def get_exercices_by_lesson(lesson_id):
    """Returns all exercises for a lesson"""
    import json
    conn = get_db()
    exercices = conn.execute(
        'SELECT * FROM exercices WHERE lesson_id = ? ORDER BY ordre',
        (lesson_id,)
    ).fetchall()
    conn.close()
    
    result = []
    for ex in exercices:
        ex_dict = dict(ex)
        if ex_dict.get('config'):
            try:
                ex_dict['config'] = json.loads(ex_dict['config'])
            except:
                ex_dict['config'] = {}
        else:
            ex_dict['config'] = {}
        result.append(ex_dict)
    
    return result


def get_exercice_by_id(exercice_id):
    """Returns an exercise by ID"""
    import json
    conn = get_db()
    exercice = conn.execute(
        'SELECT * FROM exercices WHERE id = ?',
        (exercice_id,)
    ).fetchone()
    conn.close()
    
    if not exercice:
        return None
    
    ex_dict = dict(exercice)
    if ex_dict.get('config'):
        try:
            ex_dict['config'] = json.loads(ex_dict['config'])
        except:
            ex_dict['config'] = {}
    else:
        ex_dict['config'] = {}
    
    return ex_dict


def delete_exercice(exercice_id):
    """Deletes an exercise (CASCADE will handle content and results)"""
    conn = get_db()
    conn.execute('DELETE FROM exercices WHERE id = ?', (exercice_id,))
    conn.commit()
    conn.close()


def add_exercice_contenu(exercice_id, contenu_list):
    """Adds content to an exercise"""
    import json
    conn = get_db()
    
    for i, contenu in enumerate(contenu_list):
        contenu_json = json.dumps(contenu, ensure_ascii=False)
        conn.execute(
            'INSERT INTO exercices_contenu (exercice_id, contenu, ordre) VALUES (?, ?, ?)',
            (exercice_id, contenu_json, i)
        )
    
    conn.commit()
    conn.close()


def get_exercice_contenu(exercice_id):
    """Returns all content for an exercise"""
    import json
    conn = get_db()
    contenus = conn.execute(
        'SELECT * FROM exercices_contenu WHERE exercice_id = ? ORDER BY ordre',
        (exercice_id,)
    ).fetchall()
    conn.close()
    
    result = []
    for c in contenus:
        c_dict = dict(c)
        try:
            c_dict['contenu'] = json.loads(c_dict['contenu'])
        except:
            c_dict['contenu'] = {}
        result.append(c_dict)
    
    return result


def create_exercice_resultat(exercice_id, user_id, score, total_questions, temps_secondes, complete):
    """Records an exercise result"""
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO exercices_resultats 
        (exercice_id, user_id, score, total_questions, temps_secondes, complete)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (exercice_id, user_id, score, total_questions, temps_secondes, complete)
    )
    resultat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return resultat_id


def get_exercice_stats(exercice_id, user_id):
    """Returns exercise statistics for a user"""
    conn = get_db()
    
    meilleur = conn.execute(
        '''SELECT * FROM exercices_resultats
        WHERE exercice_id = ? AND user_id = ?
        ORDER BY score DESC, date_completion DESC
        LIMIT 1''',
        (exercice_id, user_id)
    ).fetchone()
    
    nb_tentatives = conn.execute(
        'SELECT COUNT(*) as count FROM exercices_resultats WHERE exercice_id = ? AND user_id = ?',
        (exercice_id, user_id)
    ).fetchone()
    
    conn.close()
    
    meilleur_dict = dict(meilleur) if meilleur else None
    
    return {
        'meilleur_score': meilleur_dict['score'] if meilleur_dict else 0,
        'meilleur_total': meilleur_dict['total_questions'] if meilleur_dict else 0,
        'meilleur_pourcentage': round((meilleur_dict['score'] / meilleur_dict['total_questions']) * 100) if meilleur_dict and meilleur_dict['total_questions'] > 0 else 0,
        'nb_tentatives': nb_tentatives['count'],
        'complete': meilleur_dict['complete'] if meilleur_dict else False
    }


def calculate_niveau_total_xp(niveau):
    """
    Calcule l'XP total possible pour un niveau
    
    XP Total = Flashcards (10/mot) + Quiz (20/mot) + Exercices (25/question)
    """
    conn = get_db()
    
    total_xp = 0
    
    # 1. XP des decks (flashcards + quiz)
    # Tous les decks du niveau (communs + personnels, dans leçons ou libres)
    decks = conn.execute(
        '''SELECT d.id, COUNT(m.id) as nb_mots
        FROM decks d
        LEFT JOIN mots m ON d.id = m.deck_id
        WHERE d.niveau = ?
        GROUP BY d.id''',
        (niveau,)
    ).fetchall()
    
    for deck in decks:
        nb_mots = deck['nb_mots'] or 0
        # Flashcards : 10 XP par mot
        total_xp += nb_mots * 10
        # Quiz : 20 XP par mot
        total_xp += nb_mots * 20
    
    # 2. XP des exercices
    exercices = conn.execute(
        '''SELECT e.id, COUNT(ec.id) as nb_questions
        FROM exercices e
        JOIN lessons l ON e.lesson_id = l.id
        LEFT JOIN exercices_contenu ec ON e.id = ec.exercice_id
        WHERE l.niveau = ?
        GROUP BY e.id''',
        (niveau,)
    ).fetchall()
    
    for exercice in exercices:
        nb_questions = exercice['nb_questions'] or 0
        # Exercices : 25 XP par question
        total_xp += nb_questions * 25
    
    conn.close()
    return total_xp


def calculate_user_xp_for_niveau(user_id, niveau):
    """
    Calcule l'XP gagné par un utilisateur pour un niveau
    
    Retourne un dictionnaire avec détails :
    {
        'xp_flashcards': int,
        'xp_quiz': int,
        'xp_exercices': int,
        'xp_total': int,
        'bonus_quiz': int,
        'bonus_exercices': int
    }
    """
    conn = get_db()
    
    xp_flashcards = 0
    xp_quiz = 0
    xp_exercices = 0
    bonus_quiz = 0
    bonus_exercices = 0
    
    # 1. XP FLASHCARDS
    # On compte le nombre maximum de cartes vues dans une session complète
    flashcard_sessions = conn.execute(
        '''SELECT s.deck_id, MAX(s.nombre_mots_vus) as max_vus
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        AND d.niveau = ?
        AND s.type_session = 'flashcard'
        AND s.complete = 1
        GROUP BY s.deck_id''',
        (user_id, niveau)
    ).fetchall()
    
    for session in flashcard_sessions:
        cartes_vues = session['max_vus'] or 0
        xp_flashcards += cartes_vues * 10
    
    # 2. XP QUIZ
    # On compte toutes les sessions de quiz (bonnes et mauvaises réponses)
    quiz_sessions = conn.execute(
        '''SELECT s.score, s.nombre_mots_vus
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        AND d.niveau = ?
        AND s.type_session = 'quiz'
        AND s.nombre_mots_vus > 0''',
        (user_id, niveau)
    ).fetchall()
    
    for session in quiz_sessions:
        score = session['score'] or 0
        total_questions = session['nombre_mots_vus'] or 0
        
        if total_questions == 0:
            continue
        
        # Bonnes réponses : 20 XP
        xp_quiz += score * 20
        # Mauvaises réponses : 5 XP (tentative)
        xp_quiz += (total_questions - score) * 5
        
        # Bonus >= 80%
        if score / total_questions >= 0.8:
            bonus_quiz += 10
        
        # Bonus 100%
        if score == total_questions:
            bonus_quiz += 20
    
    # 3. XP EXERCICES
    # On prend le meilleur résultat par exercice
    exercice_results = conn.execute(
        '''SELECT er.exercice_id, 
               MAX(er.score) as best_score,
               (SELECT ec.total_questions 
                FROM exercices_resultats ec 
                WHERE ec.exercice_id = er.exercice_id 
                AND ec.user_id = er.user_id 
                ORDER BY ec.score DESC 
                LIMIT 1) as total_questions,
               MAX(CASE WHEN er.complete = 1 THEN 1 ELSE 0 END) as completed
        FROM exercices_resultats er
        JOIN exercices e ON er.exercice_id = e.id
        JOIN lessons l ON e.lesson_id = l.id
        WHERE er.user_id = ?
        AND l.niveau = ?
        GROUP BY er.exercice_id''',
        (user_id, niveau)
    ).fetchall()
    
    exercices_completed = set()
    
    for result in exercice_results:
        exercice_id = result['exercice_id']
        best_score = result['best_score'] or 0
        total_questions = result['total_questions'] or 0
        completed = result['completed']
        
        if total_questions == 0:
            continue
        
        # Bonnes réponses : 25 XP
        xp_exercices += best_score * 25
        # Mauvaises réponses : 8 XP (sur meilleur essai)
        xp_exercices += (total_questions - best_score) * 8
        
        # Bonus >= 80%
        if best_score / total_questions >= 0.8:
            bonus_exercices += 25
        
        # Bonus 100%
        if best_score == total_questions:
            bonus_exercices += 50
        
        # Marquer comme complété
        if completed:
            exercices_completed.add(exercice_id)
    
    # Bonus premier exercice complet par leçon
    if exercices_completed:
        lessons_completed = conn.execute(
            '''SELECT DISTINCT l.id
            FROM lessons l
            JOIN exercices e ON l.id = e.lesson_id
            WHERE l.niveau = ?
            AND e.id IN ({})'''.format(','.join('?' * len(exercices_completed))),
            (niveau, *exercices_completed)
        ).fetchall()
        
        # 100 XP par leçon avec au moins un exercice complet
        bonus_exercices += len(lessons_completed) * 100
    
    conn.close()
    
    xp_total = xp_flashcards + xp_quiz + xp_exercices + bonus_quiz + bonus_exercices
    
    return {
        'xp_flashcards': xp_flashcards,
        'xp_quiz': xp_quiz,
        'xp_exercices': xp_exercices,
        'bonus_quiz': bonus_quiz,
        'bonus_exercices': bonus_exercices,
        'xp_total': xp_total
    }


def calculate_niveau_progress_xp(user_id, niveau):
    """
    Calcule la progression d'un niveau basée sur l'XP (0-100%)
    """
    xp_total_possible = calculate_niveau_total_xp(niveau)
    
    if xp_total_possible == 0:
        return 100.0  # Niveau vide = 100%
    
    xp_data = calculate_user_xp_for_niveau(user_id, niveau)
    xp_gagne = xp_data['xp_total']
    
    progression = (xp_gagne / xp_total_possible) * 100
    return min(progression, 100.0)


def get_xp_breakdown(user_id, niveau):
    """
    Retourne un résumé détaillé de l'XP pour un niveau
    
    Retourne :
    {
        'xp_total_possible': int,
        'xp_gagne': {
            'xp_flashcards': int,
            'xp_quiz': int,
            'xp_exercices': int,
            'bonus_quiz': int,
            'bonus_exercices': int,
            'xp_total': int
        },
        'progression': float (0-100),
        'details': {
            'flashcards': {'actuel': int, 'max': int, 'pourcentage': float},
            'quiz': {'actuel': int, 'max': int, 'pourcentage': float},
            'exercices': {'actuel': int, 'max': int, 'pourcentage': float}
        }
    }
    """
    conn = get_db()
    
    xp_total_possible = calculate_niveau_total_xp(niveau)
    xp_gagne = calculate_user_xp_for_niveau(user_id, niveau)
    
    # Calculer XP max par catégorie
    # Flashcards
    total_mots = conn.execute(
        '''SELECT COUNT(m.id) as total
        FROM mots m
        JOIN decks d ON m.deck_id = d.id
        WHERE d.niveau = ?''',
        (niveau,)
    ).fetchone()['total'] or 0
    
    xp_flashcards_max = total_mots * 10
    
    # Quiz
    xp_quiz_max = total_mots * 20
    
    # Exercices
    total_questions = conn.execute(
        '''SELECT COUNT(ec.id) as total
        FROM exercices_contenu ec
        JOIN exercices e ON ec.exercice_id = e.id
        JOIN lessons l ON e.lesson_id = l.id
        WHERE l.niveau = ?''',
        (niveau,)
    ).fetchone()['total'] or 0
    
    xp_exercices_max = total_questions * 25
    
    conn.close()
    
    # Calculer pourcentages
    progression = (xp_gagne['xp_total'] / xp_total_possible * 100) if xp_total_possible > 0 else 100.0
    
    flashcards_pct = (xp_gagne['xp_flashcards'] / xp_flashcards_max * 100) if xp_flashcards_max > 0 else 0
    quiz_pct = ((xp_gagne['xp_quiz'] + xp_gagne['bonus_quiz']) / (xp_quiz_max + 100) * 100) if xp_quiz_max > 0 else 0
    exercices_pct = ((xp_gagne['xp_exercices'] + xp_gagne['bonus_exercices']) / (xp_exercices_max + 500) * 100) if xp_exercices_max > 0 else 0
    
    return {
        'xp_total_possible': xp_total_possible,
        'xp_gagne': xp_gagne,
        'progression': min(progression, 100.0),
        'details': {
            'flashcards': {
                'actuel': xp_gagne['xp_flashcards'],
                'max': xp_flashcards_max,
                'pourcentage': min(flashcards_pct, 100.0)
            },
            'quiz': {
                'actuel': xp_gagne['xp_quiz'] + xp_gagne['bonus_quiz'],
                'max': xp_quiz_max,
                'pourcentage': min(quiz_pct, 100.0)
            },
            'exercices': {
                'actuel': xp_gagne['xp_exercices'] + xp_gagne['bonus_exercices'],
                'max': xp_exercices_max,
                'pourcentage': min(exercices_pct, 100.0)
            }
        }
    }


def get_unlocked_niveaux_xp(user_id):
    """
    Retourne les niveaux déverrouillés basés sur le système XP
    
    Un niveau est déverrouillé si :
    - C'est A1 (toujours déverrouillé - premier niveau)
    - C'est Custom (toujours déverrouillé - niveau libre)
    - OU le niveau précédent >= 80% (XP) - REQUIS pour accès
    - OU l'utilisateur est admin ('c')
    
    RÈGLE STRICTE : Les niveaux A1+, A2, A2+, B1, B1+ sont VERROUILLÉS
    tant que le niveau précédent n'atteint pas 80% d'XP
    """
    # Vérifier si admin
    user = get_user_by_id(user_id)
    if user and user.get('is_admin') == True:
        return AVAILABLE_LEVELS.copy()
    
    unlocked = []
    
    for i, niveau in enumerate(AVAILABLE_LEVELS):
        # A1 : toujours déverrouillé (premier niveau)
        if niveau == 'A1':
            unlocked.append(niveau)
            continue
        
        # Custom : toujours déverrouillé (niveau libre)
        if niveau == 'Custom':
            unlocked.append(niveau)
            continue
        
        # Pour tous les autres niveaux (A1+, A2, A2+, B1, B1+)
        # OBLIGATOIRE : niveau précédent >= 80%
        if i > 0:
            niveau_precedent = AVAILABLE_LEVELS[i - 1]
            
            # Si le précédent est Custom, on cherche le niveau normal avant
            if niveau_precedent == 'Custom':
                if i > 1:
                    niveau_precedent = AVAILABLE_LEVELS[i - 2]
                else:
                    # Cas spécial : si Custom est avant dans la liste
                    # On déverrouille quand même (ne devrait pas arriver)
                    unlocked.append(niveau)
                    continue
            
            # Calculer progression du niveau précédent avec XP
            progression_precedent = calculate_niveau_progress_xp(user_id, niveau_precedent)
            
            # DÉVERROUILLAGE STRICT : >= 80% REQUIS
            if progression_precedent >= 80.0:
                unlocked.append(niveau)
            # Sinon le niveau reste VERROUILLÉ (ne pas l'ajouter à unlocked)
    
    return unlocked

def has_user_seen_all_cards(user_id, deck_id):
    """Checks if a user has seen all cards in a deck at least once"""
    total_words = get_deck_total_words(deck_id)
    if total_words == 0:
        return True  # No words = considered "seen"
    
    conn = get_db()
    # Check if there's at least one complete flashcard session with all cards
    complete_sessions = conn.execute(
        '''SELECT COUNT(*) FROM sessions 
        WHERE deck_id = ? 
        AND type_session = 'flashcard' 
        AND complete = 1 
        AND nombre_mots_vus >= ?''',
        (deck_id, total_words)
    ).fetchone()[0]
    conn.close()
    
    return complete_sessions > 0

def get_deck_total_words(deck_id):
    """Returns the total number of words in a deck"""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM mots WHERE deck_id = ?', (deck_id,)).fetchone()[0]
    conn.close()
    return count

def calculate_lesson_progress(user_id, lesson_id):
    """Calculates lesson progress (0-100%)
    
    50% = All cards seen in all decks
    50% = Success rate >80% in all deck quizzes
    """
    decks = get_decks_by_lesson(lesson_id)
    
    if not decks:
        return 100.0  # Lesson without decks = 100%
    
    # 1. Check if all cards have been seen (50%)
    all_cards_seen = all(has_user_seen_all_cards(user_id, deck['id']) for deck in decks)
    cards_progress = 50.0 if all_cards_seen else 0.0
    
    # 2. Calculate average quiz success rate (50%)
    quiz_rates = [get_quiz_success_rate(user_id, deck['id']) for deck in decks]
    avg_quiz_rate = sum(quiz_rates) / len(quiz_rates) if quiz_rates else 0.0
    
    # If average rate is >80%, get 50%
    quiz_progress = 50.0 if avg_quiz_rate >= 80.0 else 0.0
    
    return cards_progress + quiz_progress

def get_quiz_success_rate(user_id, deck_id):
    """Returns the average quiz success rate for a deck (%)"""
    conn = get_db()
    stats = conn.execute(
        '''SELECT 
            SUM(score) as total_score,
            SUM(nombre_mots_vus) as total_questions
        FROM sessions
        WHERE deck_id = ? AND type_session = 'quiz' ''',
        (deck_id,)
    ).fetchone()
    conn.close()
    
    if not stats or not stats['total_questions'] or stats['total_questions'] == 0:
        return 0.0
    
    return (stats['total_score'] / stats['total_questions']) * 100


if __name__ == '__main__':
    init_db()