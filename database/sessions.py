"""
Tipikus Database - Sessions Module
===================================
Session tracking and statistics functions
"""

from datetime import datetime, timedelta
from typing import Dict, List
from .core import get_db
from .users import get_all_users


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
            'nom': user['display_name'],
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
