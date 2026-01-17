#!/usr/bin/env python3
"""
Script de migration pour ajouter user_id aux sessions
À exécuter UNE SEULE FOIS
"""

import sqlite3

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Ajout user_id aux sessions ===\n")
    
    # 1. Vérifier si la colonne user_id existe déjà dans sessions
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print("[1/4] Ajout de la colonne user_id à la table sessions...")
        
        # Ajouter la colonne
        cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
        print("  ✓ Colonne user_id ajoutée\n")
        
        # 2. Mettre à jour les sessions existantes avec le user_id du deck
        print("[2/4] Attribution des sessions aux utilisateurs...")
        cursor.execute('''
            UPDATE sessions
            SET user_id = (
                SELECT d.user_id 
                FROM decks d 
                WHERE d.id = sessions.deck_id
            )
        ''')
        nb_updated = cursor.rowcount
        print(f"  ✓ {nb_updated} session(s) mise(s) à jour\n")
        
        # 3. Vérifier l'état
        print("[3/4] Vérification des données...")
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id IS NULL")
        orphan_sessions = cursor.fetchone()[0]
        
        if orphan_sessions > 0:
            print(f"  ⚠️  {orphan_sessions} session(s) sans user_id (decks supprimés?)")
            # Supprimer les sessions orphelines
            cursor.execute("DELETE FROM sessions WHERE user_id IS NULL")
            print(f"  ✓ Sessions orphelines supprimées\n")
        else:
            print("  ✓ Aucune session orpheline\n")
        
        # 4. Afficher l'état final
        print("[4/4] État final:")
        cursor.execute('''
            SELECT u.nom, COUNT(s.id) as nb_sessions
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id
            GROUP BY u.id
            ORDER BY u.nom
        ''')
        stats = cursor.fetchall()
        
        for nom, nb_sessions in stats:
            print(f"  → {nom}: {nb_sessions} session(s)")
        
    else:
        print("[1/4] Colonne user_id existe déjà ✓\n")
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nProchaines étapes:")
    print("  1. Redémarrer l'application: ./tipikus.sh restart")
    print("  2. Les statistiques seront maintenant personnalisées par utilisateur")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()