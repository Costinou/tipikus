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
    
    # Table des decks
    conn.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            langue TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    conn.commit()
    conn.close()
    print("Base de données initialisée avec succès!")

def get_langues():
    """Retourne la liste des langues disponibles"""
    conn = get_db()
    langues = conn.execute('SELECT DISTINCT langue FROM decks ORDER BY langue').fetchall()
    conn.close()
    return [langue['langue'] for langue in langues]

def get_decks_by_langue(langue):
    """Retourne tous les decks d'une langue donnée"""
    conn = get_db()
    decks = conn.execute(
        'SELECT * FROM decks WHERE langue = ? ORDER BY nom', 
        (langue,)
    ).fetchall()
    conn.close()
    return decks

def create_deck(nom, langue):
    """Crée un nouveau deck"""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO decks (nom, langue) VALUES (?, ?)',
        (nom, langue)
    )
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deck_id

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

if __name__ == '__main__':
    # Initialiser la DB si on lance ce fichier directement
    init_db()