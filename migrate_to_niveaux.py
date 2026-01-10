#!/usr/bin/env python3
"""
Script de migration pour passer au système de niveaux hongrois
À exécuter UNE SEULE FOIS
"""

import sqlite3

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Système de niveaux hongrois ===\n")
    
    # 1. Supprimer tous les decks non-hongrois
    print("[1/6] Suppression des decks polonais et espagnol...")
    cursor.execute("SELECT id, langue FROM decks WHERE langue != 'Magyarul'")
    decks_a_supprimer = cursor.fetchall()
    
    for deck_id, langue in decks_a_supprimer:
        # Supprimer les mots
        cursor.execute("DELETE FROM mots WHERE deck_id = ?", (deck_id,))
        # Supprimer les sessions
        cursor.execute("DELETE FROM sessions WHERE deck_id = ?", (deck_id,))
        print(f"  → Deck {deck_id} ({langue}) supprimé")
    
    cursor.execute("DELETE FROM decks WHERE langue != 'Magyarul'")
    print(f"  ✓ {len(decks_a_supprimer)} deck(s) supprimé(s)\n")
    
    # 2. Créer la nouvelle table decks avec le bon schéma
    print("[2/6] Recréation de la table decks...")
    
    # Créer une table temporaire avec le nouveau schéma
    cursor.execute('''
        CREATE TABLE decks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            niveau TEXT NOT NULL DEFAULT 'A1',
            is_commun BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    print("  ✓ Nouvelle table créée\n")
    
    # 3. Copier les données de l'ancienne table vers la nouvelle
    print("[3/6] Copie des données...")
    cursor.execute('''
        INSERT INTO decks_new (id, user_id, nom, niveau, is_commun, created_at)
        SELECT id, user_id, nom, 'A1', 0, created_at
        FROM decks
        WHERE langue = 'Magyarul'
    ''')
    nb_copies = cursor.rowcount
    print(f"  ✓ {nb_copies} deck(s) hongrois copié(s) (niveau A1 par défaut)\n")
    
    # 4. Supprimer l'ancienne table
    print("[4/6] Suppression de l'ancienne table...")
    cursor.execute("DROP TABLE decks")
    print("  ✓ Ancienne table supprimée\n")
    
    # 5. Renommer la nouvelle table
    print("[5/6] Renommage de la nouvelle table...")
    cursor.execute("ALTER TABLE decks_new RENAME TO decks")
    print("  ✓ Table renommée\n")
    
    # 6. Afficher l'état final
    print("[6/6] État final de la base de données:")
    cursor.execute("SELECT COUNT(*) FROM decks")
    total_decks = cursor.fetchone()[0]
    print(f"  → Total decks (hongrois): {total_decks}")
    
    cursor.execute("SELECT COUNT(*) FROM decks WHERE is_commun = 1")
    decks_communs = cursor.fetchone()[0]
    print(f"  → Decks communs: {decks_communs}")
    
    cursor.execute("SELECT COUNT(*) FROM decks WHERE is_commun = 0")
    decks_perso = cursor.fetchone()[0]
    print(f"  → Decks personnels: {decks_perso}")
    
    # Afficher les niveaux
    cursor.execute("SELECT niveau, COUNT(*) FROM decks GROUP BY niveau")
    niveaux = cursor.fetchall()
    print(f"\n  Par niveau:")
    for niveau, count in niveaux:
        print(f"    - {niveau}: {count} deck(s)")
    
    print()
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\nProchaines étapes:")
    print("  1. Redémarrer l'application: ./tipikus.sh restart")
    print("  2. L'interface affichera maintenant les niveaux (A1, A1+, etc.)")
    print("  3. Vous pouvez créer des decks communs (visibles par tous)")
    print("\n💡 Astuce: Tous vos decks sont en 'A1' par défaut.")
    print("   Vous pouvez les réorganiser en créant de nouveaux decks avec le bon niveau.")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        print("\nSi l'erreur persiste, restaurez votre sauvegarde:")
        print("  cp tipikus.db.backup tipikus.db")