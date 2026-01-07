import sqlite3
import os

DATABASE = 'tipikus.db'

def get_db():
    """Connexion à la base de données"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db()
    
    # Table des utilisateurs (nouveau)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des decks
    conn.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            langue TEXT NOT NULL,
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

def create_user(nom):
    """Crée un nouvel utilisateur"""
    conn = get_db()
    try:
        cursor = conn.execute('INSERT INTO users (nom) VALUES (?)', (nom,))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None  # L'utilisateur existe déjà

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

# ========== FONCTIONS MODIFIÉES POUR INCLURE USER_ID ==========

def get_langues(user_id):
    """Retourne un dictionnaire des langues avec le nombre de decks pour un utilisateur"""
    conn = get_db()
    langues = conn.execute(
        'SELECT langue, COUNT(*) as count FROM decks WHERE user_id = ? GROUP BY langue ORDER BY langue', 
        (user_id,)
    ).fetchall()
    conn.close()
    return {langue['langue']: langue['count'] for langue in langues}

def get_decks_by_langue(langue, user_id):
    """Retourne tous les decks d'une langue donnée pour un utilisateur"""
    conn = get_db()
    decks = conn.execute(
        'SELECT * FROM decks WHERE langue = ? AND user_id = ? ORDER BY nom', 
        (langue, user_id)
    ).fetchall()
    conn.close()
    return decks

def create_deck(nom, langue, user_id):
    """Crée un nouveau deck pour un utilisateur"""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO decks (nom, langue, user_id) VALUES (?, ?, ?)',
        (nom, langue, user_id)
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
    return deck

def add_mots_to_deck(deck_id, mots_dict):
    """Ajoute des mots à un deck depuis un dictionnaire"""
    conn = get_db()
    
    # Vider les anciens mots du deck (pour éviter les doublons)
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

    mots = [dict(row) for row in rows]
    return mots

def get_mots_by_deck_ordered(deck_id):
    """Retourne tous les mots d'un deck dans l'ordre alphabétique (pour l'export)"""
    conn = get_db()
    rows = conn.execute(
        'SELECT mot_francais, traduction FROM mots WHERE deck_id = ? ORDER BY mot_francais',
        (deck_id,)
    ).fetchall()
    conn.close()
    
    # Retourner un dictionnaire pour l'export JSON
    return {row['mot_francais']: row['traduction'] for row in rows}

def delete_deck(deck_id):
    """Supprime un deck et tous ses mots associés"""
    conn = get_db()
    
    # Supprimer d'abord tous les mots du deck
    conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
    
    # Supprimer ensuite le deck
    conn.execute('DELETE FROM decks WHERE id = ?', (deck_id,))
    
    conn.commit()
    conn.close()

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

def get_sessions_by_deck(deck_id, days=30):
    """Retourne les sessions d'un deck sur les N derniers jours"""
    conn = get_db()
    rows = conn.execute(
        '''SELECT * FROM sessions 
        WHERE deck_id = ? 
        AND date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY date_session DESC''',
        (deck_id, days)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_sessions_by_langue(langue, days=30):
    """Retourne les sessions d'une langue sur les N derniers jours"""
    conn = get_db()
    rows = conn.execute(
        '''SELECT s.* FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.langue = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY s.date_session DESC''',
        (langue, days)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats_deck(deck_id, days=30):
    """Calcule les statistiques d'un deck"""
    conn = get_db()
    
    # Stats générales
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
    
    # 5 dernières sessions
    dernieres_sessions = conn.execute(
        '''SELECT type_session, duree_secondes, nombre_mots_vus, score, date_session
        FROM sessions
        WHERE deck_id = ?
        ORDER BY date_session DESC
        LIMIT 5''',
        (deck_id,)
    ).fetchall()
    
    # Jours d'utilisation uniques (pour le streak)
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

def get_stats_langue(langue, user_id, days=30):
    """Calcule les statistiques d'une langue pour un utilisateur"""
    conn = get_db()
    
    # Stats générales
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
        WHERE d.langue = ?
        AND d.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (langue, user_id, days)
    ).fetchone()
    
    # Jours d'utilisation uniques
    jours = conn.execute(
        '''SELECT DISTINCT DATE(s.date_session) as jour
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.langue = ?
        AND d.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (langue, user_id, days)
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
    
    # Convertir en objets date
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
    """Calcule les statistiques globales de toutes les langues pour un utilisateur"""
    conn = get_db()
    
    # Stats totales
    stats = conn.execute(
        '''SELECT 
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz,
            SUM(s.duree_secondes) as total_duree
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')''',
        (user_id, days)
    ).fetchone()
    
    # Jours d'utilisation uniques
    jours = conn.execute(
        '''SELECT DISTINCT DATE(s.date_session) as jour
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        ORDER BY jour DESC''',
        (user_id, days)
    ).fetchall()
    
    # Stats par langue
    stats_langues = conn.execute(
        '''SELECT 
            d.langue,
            COUNT(*) as total_sessions,
            SUM(s.nombre_mots_vus) as total_mots,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.score ELSE 0 END) as total_score,
            SUM(CASE WHEN s.type_session = 'quiz' THEN s.nombre_mots_vus ELSE 0 END) as total_questions_quiz
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE d.user_id = ?
        AND s.date_session >= datetime('now', '-' || ? || ' days')
        GROUP BY d.langue''',
        (user_id, days)
    ).fetchall()
    
    conn.close()
    
    result = dict(stats) if stats else {}
    result['jours_utilises'] = [row['jour'] for row in jours]
    
    # Créer un dictionnaire par langue avec leurs stats et streak
    stats_par_langue = {}
    for row in stats_langues:
        langue = row['langue']
        # Récupérer les stats complètes pour calculer le streak
        langue_stats = get_stats_langue(langue, user_id, days)
        stats_par_langue[langue] = {
            'total_sessions': row['total_sessions'],
            'total_mots': row['total_mots'],
            'total_score': row['total_score'],
            'total_questions_quiz': row['total_questions_quiz'],
            'streak': calculer_streak(langue_stats.get('jours_utilises', []))
        }
    
    result['stats_par_langue'] = stats_par_langue
    
    return result

if __name__ == '__main__':
    # Initialiser la DB si on lance ce fichier directement
    init_db()