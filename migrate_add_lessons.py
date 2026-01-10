#!/usr/bin/env python3
"""
Script de migration pour ajouter le système de lessons
À exécuter UNE SEULE FOIS
"""

import sqlite3
import os

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Système de lessons ===\n")
    
    # 1. Créer la table lessons
    print("[1/3] Création de la table lessons...")
    cursor.execute('''
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
    print("  ✓ Table lessons créée\n")
    
    # 2. Vérifier si la colonne lesson_id existe déjà dans decks
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'lesson_id' not in columns:
        print("[2/3] Ajout de la colonne lesson_id à la table decks...")
        cursor.execute("ALTER TABLE decks ADD COLUMN lesson_id INTEGER DEFAULT NULL")
        print("  ✓ Colonne lesson_id ajoutée\n")
    else:
        print("[2/3] Colonne lesson_id existe déjà ✓\n")
    
    # 3. Créer le dossier pour les images si nécessaire
    print("[3/3] Création du dossier pour les images...")
    images_dir = os.path.join('static', 'lessons', 'images')
    os.makedirs(images_dir, exist_ok=True)
    print(f"  ✓ Dossier créé : {images_dir}\n")
    
    # Afficher l'état final
    print("État final:")
    cursor.execute("SELECT COUNT(*) FROM lessons")
    nb_lessons = cursor.fetchone()[0]
    print(f"  → Lessons existantes: {nb_lessons}")
    
    cursor.execute("SELECT COUNT(*) FROM decks WHERE lesson_id IS NOT NULL")
    nb_decks_in_lessons = cursor.fetchone()[0]
    print(f"  → Decks dans des lessons: {nb_decks_in_lessons}")
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nProchaines étapes:")
    print("  1. Redémarrer l'application")
    print("  2. Connectez-vous avec l'utilisateur 'c'")
    print("  3. Créez votre première lesson avec un fichier .md")
    print(f"  4. Placez vos images dans: {images_dir}")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()