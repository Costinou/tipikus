"""
Tipikus Database - Core Module
================================
Database connection and initialization
"""

import sqlite3

# Database file path
DATABASE = 'tipikus.db'

# Available levels for language learning
AVAILABLE_LEVELS = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']


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
