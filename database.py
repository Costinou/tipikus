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
    if user and user['nom'] == 'c':
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

if __name__ == '__main__':
    init_db()