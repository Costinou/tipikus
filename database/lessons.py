"""
Tipikus Database - Lessons Module
==================================
Lesson management and lesson-deck association functions
"""

import sqlite3
from typing import List, Dict, Optional
from .core import get_db


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
