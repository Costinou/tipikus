#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'état de la base de données
"""

import sqlite3

DATABASE = 'tipikus.db'

def check_database():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== DIAGNOSTIC DE LA BASE DE DONNÉES ===\n")
    
    # 1. Utilisateurs
    print("📊 UTILISATEURS:")
    users = cursor.execute("SELECT * FROM users ORDER BY id").fetchall()
    for user in users:
        print(f"  - ID: {user['id']}, Nom: {user['nom']}, Créé: {user['created_at']}")
    print(f"  Total: {len(users)} utilisateur(s)\n")
    
    # 2. Decks par utilisateur
    print("📚 DECKS PAR UTILISATEUR:")
    for user in users:
        decks = cursor.execute(
            "SELECT * FROM decks WHERE user_id = ? ORDER BY langue, nom",
            (user['id'],)
        ).fetchall()
        print(f"  {user['nom']} (ID: {user['id']}):")
        if decks:
            for deck in decks:
                # Compter les mots
                mot_count = cursor.execute(
                    "SELECT COUNT(*) as count FROM mots WHERE deck_id = ?",
                    (deck['id'],)
                ).fetchone()['count']
                print(f"    - [{deck['langue']}] {deck['nom']} ({mot_count} mots)")
        else:
            print(f"    Aucun deck")
    print()
    
    # 3. Sessions par utilisateur
    print("📈 SESSIONS PAR UTILISATEUR:")
    for user in users:
        session_count = cursor.execute(
            """SELECT COUNT(*) as count FROM sessions s
            JOIN decks d ON s.deck_id = d.id
            WHERE d.user_id = ?""",
            (user['id'],)
        ).fetchone()['count']
        print(f"  {user['nom']}: {session_count} session(s)")
    print()
    
    # 4. Vérifier les foreign keys
    print("🔍 VÉRIFICATION DES CONTRAINTES:")
    
    # Decks sans utilisateur
    orphan_decks = cursor.execute(
        """SELECT d.* FROM decks d
        LEFT JOIN users u ON d.user_id = u.id
        WHERE u.id IS NULL"""
    ).fetchall()
    if orphan_decks:
        print(f"  ⚠️  {len(orphan_decks)} deck(s) orphelin(s) (sans utilisateur)")
        for deck in orphan_decks:
            print(f"     - Deck ID {deck['id']}: {deck['nom']} (user_id: {deck['user_id']})")
    else:
        print("  ✅ Aucun deck orphelin")
    
    # Sessions sans deck
    orphan_sessions = cursor.execute(
        """SELECT s.* FROM sessions s
        LEFT JOIN decks d ON s.deck_id = d.id
        WHERE d.id IS NULL"""
    ).fetchall()
    if orphan_sessions:
        print(f"  ⚠️  {len(orphan_sessions)} session(s) orpheline(s)")
    else:
        print("  ✅ Aucune session orpheline")
    
    print()
    conn.close()

if __name__ == '__main__':
    try:
        check_database()
    except Exception as e:
        print(f"❌ Erreur: {e}")