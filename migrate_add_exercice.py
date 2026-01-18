#!/usr/bin/env python3
"""
Script de migration pour ajouter le système d'exercices
À exécuter UNE SEULE FOIS
"""

import sqlite3

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Système d'exercices ===\n")
    
    # 1. Créer la table exercices
    print("[1/4] Création de la table exercices...")
    cursor.execute('''
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
    print("  ✓ Table exercices créée\n")
    
    # 2. Créer la table exercices_contenu
    print("[2/4] Création de la table exercices_contenu...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercices_contenu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            contenu TEXT NOT NULL,
            ordre INTEGER DEFAULT 0,
            FOREIGN KEY (exercice_id) REFERENCES exercices (id) ON DELETE CASCADE
        )
    ''')
    print("  ✓ Table exercices_contenu créée\n")
    
    # 3. Créer la table exercices_resultats
    print("[3/4] Création de la table exercices_resultats...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercices_resultats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            temps_secondes INTEGER DEFAULT 0,
            complete BOOLEAN DEFAULT 0,
            date_completion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exercice_id) REFERENCES exercices (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    print("  ✓ Table exercices_resultats créée\n")
    
    # 4. Afficher l'état final
    print("[4/4] État final:")
    cursor.execute("SELECT COUNT(*) FROM exercices")
    nb_exercices = cursor.fetchone()[0]
    print(f"  → Exercices: {nb_exercices}")
    
    cursor.execute("SELECT COUNT(*) FROM exercices_contenu")
    nb_contenu = cursor.fetchone()[0]
    print(f"  → Contenus: {nb_contenu}")
    
    cursor.execute("SELECT COUNT(*) FROM exercices_resultats")
    nb_resultats = cursor.fetchone()[0]
    print(f"  → Résultats: {nb_resultats}")
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nProchaines étapes:")
    print("  1. Redémarrer l'application: ./tipikus.sh restart")
    print("  2. Créer votre premier exercice 'fill_blank'")
    print("  3. L'associer à une lesson")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()