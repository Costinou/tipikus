"""
Tipikus Database - Decks Module
================================
Deck and vocabulary (mots) management functions
"""

from typing import Dict, List
from .core import get_db
from .users import get_user_by_id


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
