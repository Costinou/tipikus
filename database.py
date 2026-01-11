import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'tipikus.db'

# Niveaux disponibles
NIVEAUX_DISPONIBLES = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']

def get_db():
    """Connexion à la base de données"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db()
    
    # Table des utilisateurs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des decks (avec niveau et is_commun)
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
    
    # Table des mots
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            mot_francais TEXT NOT NULL,
            traduction TEXT NOT NULL,
            FOREIGN KEY (deck_id) REFERENCES decks (id)
        )
    ''')
    
    # Table des sessions
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
    print("Base de données initialisée avec succès!")

# ========== FONCTIONS POUR LES UTILISATEURS ==========

def get_all_users():
    """Retourne tous les utilisateurs"""
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY nom').fetchall()
    conn.close()
    return [dict(user) for user in users]

def get_user_by_id(user_id):
    """Retourne un utilisateur par son ID"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_name(nom):
    """Retourne un utilisateur par son nom"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE nom = ?', (nom,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(nom, password):
    """Crée un nouvel utilisateur avec mot de passe"""
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
        return None  # L'utilisateur existe déjà

def verify_user_password(nom, password):
    """Vérifie le nom d'utilisateur et le mot de passe"""
    user = get_user_by_name(nom)
    if not user:
        return None
    
    if check_password_hash(user['password_hash'], password):
        return user
    return None

def update_user_password(user_id, new_password):
    """Met à jour le mot de passe d'un utilisateur"""
    conn = get_db()
    password_hash = generate_password_hash(new_password)
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Supprime un utilisateur et toutes ses données associées"""
    conn = get_db()
    
    # Récupérer tous les decks de l'utilisateur
    decks = conn.execute('SELECT id FROM decks WHERE user_id = ?', (user_id,)).fetchall()
    deck_ids = [deck['id'] for deck in decks]
    
    # Supprimer les sessions des decks de l'utilisateur
    for deck_id in deck_ids:
        conn.execute('DELETE FROM sessions WHERE deck_id = ?', (deck_id,))
    
    # Supprimer les mots des decks de l'utilisateur
    for deck_id in deck_ids:
        conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Supprimer les decks de l'utilisateur
    conn.execute('DELETE FROM decks WHERE user_id = ?', (user_id,))
    
    # Supprimer l'utilisateur
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()

# ========== FONCTIONS POUR LES LESSONS ==========

def get_lessons_by_niveau(niveau):
    """Retourne toutes les lessons d'un niveau, triées par numéro"""
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
    """Retourne une lesson par son ID"""
    conn = get_db()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    return dict(lesson) if lesson else None

def create_lesson(niveau, numero, titre, content_markdown):
    """Crée une nouvelle lesson"""
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
        return None  # Cette lesson existe déjà (niveau + numéro unique)

def update_lesson(lesson_id, titre, content_markdown):
    """Met à jour une lesson existante"""
    conn = get_db()
    conn.execute(
        'UPDATE lessons SET titre = ?, content_markdown = ? WHERE id = ?',
        (titre, content_markdown, lesson_id)
    )
    conn.commit()
    conn.close()

def delete_lesson(lesson_id):
    """Supprime une lesson (et détache les decks associés)"""
    conn = get_db()
    # Détacher les decks de cette lesson
    conn.execute('UPDATE decks SET lesson_id = NULL WHERE lesson_id = ?', (lesson_id,))
    # Supprimer la lesson
    conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
    conn.commit()
    conn.close()

def get_decks_by_lesson(lesson_id):
    """Retourne tous les decks d'une lesson"""
    conn = get_db()
    decks = conn.execute(
        'SELECT * FROM decks WHERE lesson_id = ? ORDER BY nom',
        (lesson_id,)
    ).fetchall()
    conn.close()
    return [dict(deck) for deck in decks]

def associate_deck_to_lesson(deck_id, lesson_id):
    """Associe un deck à une lesson"""
    conn = get_db()
    conn.execute('UPDATE decks SET lesson_id = ? WHERE id = ?', (lesson_id, deck_id))
    conn.commit()
    conn.close()

def detach_deck_from_lesson(deck_id):
    """Détache un deck de sa lesson"""
    conn = get_db()
    conn.execute('UPDATE decks SET lesson_id = NULL WHERE id = ?', (deck_id,))
    conn.commit()
    conn.close()

# ========== FONCTIONS POUR LA PROGRESSION ==========

def get_deck_total_words(deck_id):
    """Retourne le nombre total de mots dans un deck"""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM mots WHERE deck_id = ?', (deck_id,)).fetchone()[0]
    conn.close()
    return count

def has_user_seen_all_cards(user_id, deck_id):
    """Vérifie si un utilisateur a vu toutes les cartes d'un deck au moins une fois"""
    total_words = get_deck_total_words(deck_id)
    if total_words == 0:
        return True  # Pas de mots = considéré comme "vu"
    
    conn = get_db()
    # Vérifier s'il y a au moins une session flashcard complète avec toutes les cartes
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
    """Retourne le taux de réussite moyen aux quiz d'un deck (%)"""
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
    """Calcule la progression d'une lesson (0-100%)
    
    50% = Toutes les cartes vues dans tous les decks
    50% = Taux de réussite >80% aux quiz de tous les decks
    """
    decks = get_decks_by_lesson(lesson_id)
    
    if not decks:
        return 100.0  # Lesson sans decks = 100%
    
    # 1. Vérifier si toutes les cartes ont été vues (50%)
    all_cards_seen = all(has_user_seen_all_cards(user_id, deck['id']) for deck in decks)
    cards_progress = 50.0 if all_cards_seen else 0.0
    
    # 2. Calculer le taux de réussite moyen aux quiz (50%)
    quiz_rates = [get_quiz_success_rate(user_id, deck['id']) for deck in decks]
    avg_quiz_rate = sum(quiz_rates) / len(quiz_rates) if quiz_rates else 0.0
    
    # Si le taux moyen est >80%, on obtient 50%
    quiz_progress = 50.0 if avg_quiz_rate >= 80.0 else 0.0
    
    return cards_progress + quiz_progress

def get_user_seen_cards_count(user_id, deck_id):
    """Retourne le nombre de cartes vues par un utilisateur dans un deck
    (basé sur le max de mots vus dans une session flashcard complète)"""
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
    """Calcule la progression globale d'un niveau (0-100%)
    
    50% = Progression moyenne des lessons (granulaire)
    50% = Cartes vues dans les decks hors lessons (linéaire)
    """
    # 1. Récupérer toutes les lessons du niveau
    lessons = get_lessons_by_niveau(niveau)
    
    lessons_progress = 0.0
    if lessons:
        # Calculer la progression moyenne de toutes les lessons
        total_lessons_progress = sum(calculate_lesson_progress(user_id, lesson['id']) for lesson in lessons)
        lessons_progress = (total_lessons_progress / len(lessons)) * 0.5  # 50% du total
    else:
        # Pas de lessons = 50% automatique
        lessons_progress = 50.0
    
    # 2. Récupérer les decks HORS lessons
    all_decks = get_decks_by_niveau(niveau, user_id, include_in_lessons=True)
    decks_hors_lessons = [d for d in all_decks if d['lesson_id'] is None]
    
    cards_progress = 0.0
    if decks_hors_lessons:
        # Calculer le nombre total de cartes et le nombre vu
        total_cards = 0
        seen_cards = 0
        
        for deck in decks_hors_lessons:
            deck_total = get_deck_total_words(deck['id'])
            deck_seen = get_user_seen_cards_count(user_id, deck['id'])
            
            total_cards += deck_total
            seen_cards += min(deck_seen, deck_total)  # Ne pas dépasser le total
        
        if total_cards > 0:
            # Progression linéaire : (cartes vues / cartes totales) * 50%
            cards_progress = (seen_cards / total_cards) * 50.0
        else:
            # Pas de cartes = 50% automatique
            cards_progress = 50.0
    else:
        # Pas de decks hors lessons = 50% automatique
        cards_progress = 50.0
    
    return lessons_progress + cards_progress

# ========== FONCTIONS POUR LES NIVEAUX ==========

def get_niveaux_with_counts(user_id):
    """Retourne un dictionnaire des niveaux avec le nombre de decks (communs + perso)"""
    conn = get_db()
    
    # Compter les decks communs + decks personnels de l'user
    niveaux = conn.execute(
        '''SELECT niveau, COUNT(*) as count FROM decks 
        WHERE is_commun = 1 OR user_id = ?
        GROUP BY niveau ORDER BY niveau''', 
        (user_id,)
    ).fetchall()
    
    conn.close()
    return {niveau['niveau']: niveau['count'] for niveau in niveaux}

# ========== FONCTIONS POUR LES DECKS ==========

def get_decks_by_niveau(niveau, user_id, include_in_lessons=False):
    """Retourne tous les decks d'un niveau
    
    Pour l'admin 'c': TOUS les decks (communs + tous les decks perso)
    Pour les autres: decks communs + leurs decks perso uniquement
    
    Par défaut, exclut les decks qui sont dans des lessons
    """
    conn = get_db()
    
    # Vérifier si l'utilisateur est l'admin
    user = get_user_by_id(user_id)
    is_admin = user and user['nom'] == 'c'
    
    if include_in_lessons:
        # Récupérer TOUS les decks (y compris ceux dans des lessons)
        if is_admin:
            # Admin voit TOUS les decks
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ?
                ORDER BY d.is_commun DESC, u.nom, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            # Utilisateur normal voit seulement les decks communs + ses decks perso
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND (d.is_commun = 1 OR d.user_id = ?)
                ORDER BY d.is_commun DESC, d.nom''',
                (niveau, user_id)
            ).fetchall()
    else:
        # Récupérer uniquement les decks HORS lessons
        if is_admin:
            # Admin voit TOUS les decks hors lessons
            decks = conn.execute(
                '''SELECT d.*, u.nom as createur_nom 
                FROM decks d
                JOIN users u ON d.user_id = u.id
                WHERE d.niveau = ? AND d.lesson_id IS NULL
                ORDER BY d.is_commun DESC, u.nom, d.nom''',
                (niveau,)
            ).fetchall()
        else:
            # Utilisateur normal voit seulement les decks communs + ses decks perso (hors lessons)
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
    """Crée un nouveau deck"""
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
    """Retourne un deck par son ID"""
    conn = get_db()
    deck = conn.execute(
        'SELECT * FROM decks WHERE id = ?', 
        (deck_id,)
    ).fetchone()
    conn.close()
    return dict(deck) if deck else None

def add_mots_to_deck(deck_id, mots_dict):
    """Ajoute des mots à un deck depuis un dictionnaire"""
    conn = get_db()
    
    # Vider les anciens mots du deck
    conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Ajouter les nouveaux mots
    for mot_francais, traduction in mots_dict.items():
        conn.execute(
            'INSERT INTO mots (deck_id, mot_francais, traduction) VALUES (?, ?, ?)',
            (deck_id, mot_francais, traduction)
        )
    
    conn.commit()
    conn.close()

def get_mots_by_deck(deck_id):
    """Retourne tous les mots d'un deck"""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM mots WHERE deck_id = ? ORDER BY RANDOM()',
        (deck_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_mots_by_deck_ordered(deck_id):
    """Retourne tous les mots d'un deck dans l'ordre alphabétique"""
    conn = get_db()
    rows = conn.execute(
        'SELECT mot_francais, traduction FROM mots WHERE deck_id = ? ORDER BY mot_francais',
        (deck_id,)
    ).fetchall()
    conn.close()
    return {row['mot_francais']: row['traduction'] for row in rows}

def delete_deck(deck_id):
    """Supprime un deck et tous ses mots associés"""
    conn = get_db()
    
    # Supprimer les mots
    conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Supprimer les sessions
    conn.execute('DELETE FROM sessions WHERE deck_id = ?', (deck_id,))
    
    # Supprimer le deck
    conn.execute('DELETE FROM decks WHERE id = ?', (deck_id,))
    
    conn.commit()
    conn.close()

def can_delete_deck(deck_id, user_nom):
    """Vérifie si un utilisateur peut supprimer un deck"""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return False
    
    # Si c'est un deck commun, seul l'user 'c' peut le supprimer
    if deck['is_commun']:
        return user_nom == 'c'
    
    # Sinon, on vérifie que c'est le propriétaire
    # (cette vérification sera faite dans app.py)
    return True

# ========== FONCTIONS POUR LES SESSIONS ==========

def create_session(deck_id, type_session, nombre_mots_vus, score, duree_secondes, complete):
    """Enregistre une nouvelle session d'apprentissage"""
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO sessions 
        (deck_id, type_session, nombre_mots_vus, score, duree_secondes, complete) 
        VALUES (?, ?, ?, ?, ?, ?)''',
        (deck_id, type_session, nombre_mots_vus, score, duree_secondes, complete)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_stats_deck(deck_id, days=30):
    """Calcule les statistiques d'un deck"""
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
        AND date_session >= datetime('now', '-' || ? || ' days')''',
        (deck_id, days)
    ).fetchone()
    
    dernieres_sessions = conn.execute(
        '''SELECT type_session, duree_secondes, nombre_mots_vus, score, date_session
        FROM sessions
        WHERE deck_id = ?
        ORDER BY date_session DESC
        LIMIT 5''',
        (deck_id,)
    ).fetchall()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(date_session) as jour
        FROM sessions
        WHERE deck_id = ?
        AND date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (deck_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['dernieres_sessions'] = [dict(row) for row in dernieres_sessions]
    result['jours_utilises'] = [row['jour'] for row in jours]
    
    return result

def get_stats_niveau(niveau, user_id, days=30):
    """Calcule les statistiques d'un niveau pour un utilisateur"""
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
        AND (d.is_commun = 1 OR d.user_id = ?)
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (niveau, user_id, days)
    ).fetchone()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(s.date_session) as jour
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.niveau = ?
        AND (d.is_commun = 1 OR d.user_id = ?)
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (niveau, user_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['jours_utilises'] = [row['jour'] for row in jours]
    
    return result

def calculer_streak(jours_utilises):
    """Calcule le nombre de jours consécutifs d'utilisation"""
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
    """Calcule les statistiques globales"""
    conn = get_db()
    
    stats = conn.execute(
        '''SELECT 
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
            SUM(s.duree_secondes) as total_duree
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.user_id = ? OR d.is_commun = 1
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (user_id, days)
    ).fetchone()
    
    jours = conn.execute(
        '''SELECT DISTINCT DATE(s.date_session) as jour
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.user_id = ? OR d.is_commun = 1
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (user_id, days)
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
        WHERE d.user_id = ? OR d.is_commun = 1
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        GROUP BY d.niveau''',
        (user_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['jours_utilises'] = [row['jour'] for row in jours]
    
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

if __name__ == '__main__':
    init_db()