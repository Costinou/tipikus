import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'tipikus.db'

# Available levels
AVAILABLE_LEVELS = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']

def get_db():
    """Database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with necessary tables"""
    conn = get_db()
    
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Decks table (with level and is_common)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            niveau TEXT NOT NULL,
            is_commun BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
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
            type_session TEXT NOT NULL,
            date_session TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nombre_mots_vus INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            duree_secondes INTEGER DEFAULT 0,
            complete BOOLEAN DEFAULT 0,
            FOREIGN KEY (deck_id) REFERENCES decks (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# ========== USER FUNCTIONS ==========

def get_all_users():
    """Returns all users"""
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY nom').fetchall()
    conn.close()
    return [dict(user) for user in users]

def get_user_by_id(user_id):
    """Returns a user by ID"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_name(nom):
    """Returns a user by name"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE nom = ?', (nom,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(nom, password):
    """Creates a new user with password"""
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.execute('INSERT INTO users (nom, password_hash) VALUES (?, ?)', (nom, password_hash))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None  # User already exists

def verify_user_password(nom, password):
    """Verifies username and password"""
    user = get_user_by_name(nom)
    if not user:
        return None
    
    if check_password_hash(user['password_hash'], password):
        return user
    return None

def update_user_password(user_id, new_password):
    """Updates a user's password"""
    conn = get_db()
    password_hash = generate_password_hash(new_password)
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Deletes a user and all associated data"""
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
    
    # Delete the user
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()

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
        return None  # This lesson already exists (unique level + number)

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
    """Deletes a lesson (and detaches associated decks)"""
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

# ========== PROGRESS FUNCTIONS ==========

def get_deck_total_words(deck_id):
    """Returns the total number of words in a deck"""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM mots WHERE deck_id = ?', (deck_id,)).fetchone()[0]
    conn.close()
    return count

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

def get_user_seen_cards_count(user_id, deck_id):
    """Returns the number of cards seen by a user in a deck
    (based on max words seen in a complete flashcard session)"""
    conn = get_db()
    max_seen = conn.execute(
        '''SELECT MAX(nombre_mots_vus) as max_seen
        FROM sessions
        WHERE deck_id = ? 
        AND type_session = 'flashcard'
        AND complete = 1''',
        (deck_id,)
    ).fetchone()
    conn.close()
    
    if max_seen and max_seen['max_seen']:
        return max_seen['max_seen']
    return 0

def calculate_niveau_progress(user_id, niveau):
    """Calculates overall progress for a level (0-100%)
    
    50% = Average lesson progress (granular)
    50% = Cards seen in decks outside lessons (linear)
    """
    # 1. Get all lessons for the level
    lessons = get_lessons_by_niveau(niveau)
    
    lessons_progress = 0.0
    if lessons:
        # Calculate average progress of all lessons
        total_lessons_progress = sum(calculate_lesson_progress(user_id, lesson['id']) for lesson in lessons)
        lessons_progress = (total_lessons_progress / len(lessons)) * 0.5  # 50% of total
    else:
        # No lessons = automatic 50%
        lessons_progress = 50.0
    
    # 2. Get decks OUTSIDE lessons
    all_decks = get_decks_by_niveau(niveau, user_id, include_in_lessons=True)
    decks_outside_lessons = [d for d in all_decks if d['lesson_id'] is None]
    
    cards_progress = 0.0
    if decks_outside_lessons:
        # Calculate total number of cards and number seen
        total_cards = 0
        seen_cards = 0
        
        for deck in decks_outside_lessons:
            deck_total = get_deck_total_words(deck['id'])
            deck_seen = get_user_seen_cards_count(user_id, deck['id'])
            
            total_cards += deck_total
            seen_cards += min(deck_seen, deck_total)  # Don't exceed total
        
        if total_cards > 0:
            # Linear progress: (cards seen / total cards) * 50%
            cards_progress = (seen_cards / total_cards) * 50.0
        else:
            # No cards = automatic 50%
            cards_progress = 50.0
    else:
        # No decks outside lessons = automatic 50%
        cards_progress = 50.0
    
    return lessons_progress + cards_progress

# ========== LEVEL FUNCTIONS ==========

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
    
    For admin 'c': ALL decks (common + all personal decks)
    For others: common decks + their personal decks only
    
    By default, excludes decks that are in lessons
    """
    conn = get_db()
    
    # Check if user is admin
    user = get_user_by_id(user_id)
    is_admin = user and user['nom'] == 'c'
    
    if include_in_lessons:
        # Get ALL decks (including those in lessons)
        if is_admin:
            # Admin sees ALL decks
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ?
                ORDER BY d.is_commun DESC, u.nom, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            # Normal user sees only common decks + their personal decks
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND (d.is_commun = 1 OR d.user_id = ?)
                ORDER BY d.is_commun DESC, d.nom''',
                (niveau, user_id)
            ).fetchall()
    else:
        # Get only decks OUTSIDE lessons
        if is_admin:
            # Admin sees ALL decks outside lessons
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND d.lesson_id IS NULL
                ORDER BY d.is_commun DESC, u.nom, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            # Normal user sees only common decks + their personal decks (outside lessons)
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
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
    deck = conn.execute(
        'SELECT * FROM decks WHERE id = ?', 
        (deck_id,)
    ).fetchone()
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
    """Returns all words from a deck"""
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

def can_delete_deck(deck_id, user_nom):
    """Checks if a user can delete a deck"""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return False
    
    # If it's a common deck, only user 'c' can delete it
    if deck['is_commun']:
        return user_nom == 'c'
    
    # Otherwise, check that they're the owner
    # (this verification will be done in app.py)
    return True

# ========== SESSION FUNCTIONS ==========

def create_session(deck_id, user_id, type_session, nombre_mots_vus, score, duree_secondes, complete):
    """Records a new learning session with user_id"""
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
    
    # Get recent sessions with deck name
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
    
    # Get recent sessions with deck name and level
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

def get_all_users_stats():
    """Returns statistics for all users for the admin
    
    Only counts sessions done by each user
    (thanks to the user_id column in sessions)
    """
    conn = get_db()
    
    # Get all users
    users = conn.execute('SELECT * FROM users ORDER BY nom').fetchall()
    
    users_stats = []
    
    for user in users:
        user_id = user['id']
        
        # Statistics for this user's sessions only
        stats = conn.execute(
            '''SELECT 
                COUNT(*) as total_sessions,
                SUM(nombre_mots_vus) as total_mots_vus,
                SUM(CASE WHEN type_session = 'quiz' THEN score ELSE 0 END) as total_score,
                SUM(CASE WHEN type_session = 'quiz' THEN nombre_mots_vus ELSE 0 END) as total_questions,
                SUM(duree_secondes) as total_duree,
                MAX(DATE(date_session)) as derniere_activite
            FROM sessions
            WHERE user_id = ?''',
            (user_id,)
        ).fetchone()
        
        # Number of personal decks
        nb_decks = conn.execute(
            'SELECT COUNT(*) as count FROM decks WHERE user_id = ? AND is_commun = 0',
            (user_id,)
        ).fetchone()['count']
        
        # Activity days to calculate streak
        jours = conn.execute(
            '''SELECT DISTINCT DATE(date_session) as jour
            FROM sessions
            WHERE user_id = ?
            ORDER BY jour DESC''',
            (user_id,)
        ).fetchall()
        
        jours_liste = [row['jour'] for row in jours]
        streak = calculer_streak(jours_liste)
        
        # Calculate success rate
        taux_reussite = None
        if stats['total_questions'] and stats['total_questions'] > 0:
            taux_reussite = (stats['total_score'] / stats['total_questions']) * 100
        
        users_stats.append({
            'id': user['id'],
            'nom': user['nom'],
            'total_sessions': stats['total_sessions'] or 0,
            'total_mots_vus': stats['total_mots_vus'] or 0,
            'total_score': stats['total_score'] or 0,
            'total_questions': stats['total_questions'] or 0,
            'taux_reussite': taux_reussite,
            'total_duree': stats['total_duree'] or 0,
            'streak': streak,
            'nb_decks_perso': nb_decks,
            'derniere_activite': stats['derniere_activite']
        })
    
    conn.close()
    return users_stats

def get_users_with_stats():
    """Returns all users with their statistics"""
    conn = get_db()
    
    users = get_all_users()
    users_stats = []
    
    for user in users:
        # Stats for this user
        stats = conn.execute(
            '''SELECT 
                COUNT(*) as total_sessions,
                SUM(s.nombre_mots_vus) as total_mots_vus,
                SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
                SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
                MAX(s.date_session) as derniere_activite
            FROM sessions s
            JOIN decks d ON s.deck_id = d.id
            WHERE d.user_id = ? OR d.is_commun = 1''',
            (user['id'],)
        ).fetchone()
        
        # Calculate streak
        jours = conn.execute(
            '''SELECT DISTINCT DATE(s.date_session) as jour
            FROM sessions s
            JOIN decks d ON s.deck_id = d.id
            WHERE d.user_id = ? OR d.is_commun = 1
            ORDER BY jour DESC''',
            (user['id'],)
        ).fetchall()
        
        streak = calculer_streak([row['jour'] for row in jours])
        
        # Calculate success rate
        total_quiz = stats['total_questions_quiz'] or 0
        taux_reussite = None
        if total_quiz > 0:
            taux_reussite = round((stats['total_score'] / total_quiz) * 100, 1)
        
        users_stats.append({
            'id': user['id'],
            'nom': user['nom'],
            'total_sessions': stats['total_sessions'] or 0,
            'total_mots_vus': stats['total_mots_vus'] or 0,
            'streak': streak,
            'taux_reussite': taux_reussite,
            'derniere_activite': stats['derniere_activite'][:16] if stats['derniere_activite'] else None
        })
    
    conn.close()
    return users_stats

def get_recent_sessions(limit=10):
    """Returns the N most recent sessions with username and deck"""
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
            u.nom as user_nom
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        JOIN users u ON d.user_id = u.id
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
    """Returns all exercises for a lesson, sorted by order"""
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
        # Parse JSON config
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
    # Parse JSON config
    if ex_dict.get('config'):
        try:
            ex_dict['config'] = json.loads(ex_dict['config'])
        except:
            ex_dict['config'] = {}
    else:
        ex_dict['config'] = {}
    
    return ex_dict


def delete_exercice(exercice_id):
    """Deletes an exercise and all its content"""
    conn = get_db()
    # Content and results will be deleted automatically (CASCADE)
    conn.execute('DELETE FROM exercices WHERE id = ?', (exercice_id,))
    conn.commit()
    conn.close()


def add_exercice_contenu(exercice_id, contenu_list):
    """Adds content to an exercise
    
    contenu_list: list of dictionaries with content
    Example for fill_blank:
    [
        {
            "phrase": "Én {0} magyarul.",
            "reponses_valides": ["tanulok", "Tanulok"],
            "traduction": "J'étudie le hongrois.",
            "indice": "tanul + ok"
        },
        ...
    ]
    """
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
    """Returns all content for an exercise, sorted by order"""
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
        # Parse JSON content
        try:
            c_dict['contenu'] = json.loads(c_dict['contenu'])
        except:
            c_dict['contenu'] = {}
        result.append(c_dict)
    
    return result


def delete_exercice_contenu(exercice_id):
    """Deletes all content for an exercise"""
    conn = get_db()
    conn.execute('DELETE FROM exercices_contenu WHERE exercice_id = ?', (exercice_id,))
    conn.commit()
    conn.close()


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


def get_exercice_meilleur_resultat(exercice_id, user_id):
    """Returns a user's best result for an exercise"""
    conn = get_db()
    resultat = conn.execute(
        '''SELECT * FROM exercices_resultats
        WHERE exercice_id = ? AND user_id = ?
        ORDER BY score DESC, date_completion DESC
        LIMIT 1''',
        (exercice_id, user_id)
    ).fetchone()
    conn.close()
    return dict(resultat) if resultat else None


def is_exercice_completed(exercice_id, user_id):
    """Checks if an exercise is completed by a user"""
    conn = get_db()
    result = conn.execute(
        '''SELECT complete FROM exercices_resultats
        WHERE exercice_id = ? AND user_id = ?
        ORDER BY date_completion DESC
        LIMIT 1''',
        (exercice_id, user_id)
    ).fetchone()
    conn.close()
    return result['complete'] if result else False


def get_exercice_stats(exercice_id, user_id):
    """Returns exercise statistics for a user"""
    conn = get_db()
    
    # Best score
    meilleur = get_exercice_meilleur_resultat(exercice_id, user_id)
    
    # Number of attempts
    nb_tentatives = conn.execute(
        'SELECT COUNT(*) as count FROM exercices_resultats WHERE exercice_id = ? AND user_id = ?',
        (exercice_id, user_id)
    ).fetchone()
    
    conn.close()
    
    return {
        'meilleur_score': meilleur['score'] if meilleur else 0,
        'meilleur_total': meilleur['total_questions'] if meilleur else 0,
        'meilleur_pourcentage': round((meilleur['score'] / meilleur['total_questions']) * 100) if meilleur and meilleur['total_questions'] > 0 else 0,
        'nb_tentatives': nb_tentatives['count'],
        'complete': meilleur['complete'] if meilleur else False
    }


if __name__ == '__main__':
    init_db()