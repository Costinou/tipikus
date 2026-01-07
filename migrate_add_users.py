#!/usr/bin/env python3
"""
Script de migration pour ajouter le système d'utilisateurs
À exécuter UNE SEULE FOIS pour migrer les données existantes
"""

import sqlite3

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Ajout du système d'utilisateurs ===\n")
    
    # 1. Créer la table users si elle n'existe pas
    print("[1/4] Création de la table users...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Vérifier si la colonne user_id existe déjà dans decks
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print("[2/4] Ajout de la colonne user_id à la table decks...")
        
        # Créer un utilisateur par défaut si aucun n'existe
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            print("  → Création d'un utilisateur par défaut 'Utilisateur'")
            cursor.execute("INSERT INTO users (nom) VALUES ('Utilisateur')")
            default_user_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM users LIMIT 1")
            default_user_id = cursor.fetchone()[0]
        
        # Ajouter la colonne user_id
        cursor.execute(f"ALTER TABLE decks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
        
        # Mettre à jour tous les decks existants avec l'utilisateur par défaut
        cursor.execute(f"UPDATE decks SET user_id = {default_user_id} WHERE user_id IS NULL")
        
        print(f"  → Tous les decks existants ont été attribués à l'utilisateur ID {default_user_id}")
    else:
        print("[2/4] La colonne user_id existe déjà ✓")
    
    # 3. Créer la table sessions si elle n'existe pas (déjà dans init_db normalement)
    print("[3/4] Vérification de la table sessions...")
    cursor.execute('''
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
    
    # 4. Commit et fermer
    print("[4/4] Sauvegarde des modifications...")
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nVous pouvez maintenant:")
    print("  1. Redémarrer l'application: ./tipikus.sh restart")
    print("  2. Accéder à l'application")
    print("  3. Sélectionner ou créer un utilisateur")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        print("\nSi l'erreur persiste, contactez le support.")