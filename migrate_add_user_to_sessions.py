#!/usr/bin/env python3
"""
Script de migration pour ajouter user_id à la table sessions
À exécuter UNE SEULE FOIS
"""

import sqlite3

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Ajout de user_id à la table sessions ===\n")
    
    # 1. Vérifier si la colonne user_id existe déjà
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' in columns:
        print("[✓] La colonne user_id existe déjà dans sessions\n")
        conn.close()
        return
    
    print("[1/3] Ajout de la colonne user_id à la table sessions...")
    
    # Ajouter la colonne (nullable pour l'instant)
    cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
    print("  ✓ Colonne user_id ajoutée\n")
    
    print("[2/3] Mise à jour des sessions existantes...")
    
    # Associer chaque session existante à l'utilisateur propriétaire du deck
    cursor.execute('''
        UPDATE sessions 
        SET user_id = (
            SELECT user_id 
            FROM decks 
            WHERE decks.id = sessions.deck_id
        )
    ''')
    
    nb_updated = cursor.rowcount
    print(f"  ✓ {nb_updated} session(s) mise(s) à jour\n")
    
    print("[3/3] Vérification...")
    
    # Vérifier qu'il n'y a pas de sessions orphelines
    cursor.execute('''
        SELECT COUNT(*) 
        FROM sessions 
        WHERE user_id IS NULL
    ''')
    nb_orphan = cursor.fetchone()[0]
    
    if nb_orphan > 0:
        print(f"  ⚠️  {nb_orphan} session(s) sans user_id (decks supprimés)")
    else:
        print("  ✓ Toutes les sessions ont un user_id")
    
    # Afficher l'état final
    print("\nÉtat final:")
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]
    print(f"  → Total sessions: {total_sessions}")
    
    cursor.execute('''
        SELECT u.nom, COUNT(s.id) as nb_sessions
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        GROUP BY u.nom
        ORDER BY nb_sessions DESC
    ''')
    stats_users = cursor.fetchall()
    
    print("\n  Répartition par utilisateur:")
    for nom, nb in stats_users:
        print(f"    - {nom}: {nb} session(s)")
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nProchaines étapes:")
    print("  1. Redémarrer l'application")
    print("  2. Les statistiques seront maintenant correctes par utilisateur")
    print("\n💡 Note: Les nouvelles sessions seront automatiquement")
    print("   liées à l'utilisateur connecté")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()