#!/usr/bin/env python3
"""
Script de migration pour ajouter l'authentification
À exécuter UNE SEULE FOIS
"""

import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'tipikus.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("=== Migration: Système d'authentification ===\n")
    
    # 1. Vérifier si la colonne password_hash existe déjà
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'password_hash' not in columns:
        print("[1/3] Ajout de la colonne password_hash...")
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        print("  ✓ Colonne password_hash ajoutée\n")
    else:
        print("[1/3] Colonne password_hash existe déjà ✓\n")
    
    # 2. Vérifier si l'utilisateur admin 'c' existe
    print("[2/3] Vérification de l'utilisateur admin 'c'...")
    cursor.execute("SELECT id, password_hash FROM users WHERE nom = 'c'")
    admin = cursor.fetchone()
    
    if admin:
        admin_id, current_hash = admin
        if not current_hash:
            # L'admin existe mais n'a pas de mot de passe
            default_password = 'admin123'
            password_hash = generate_password_hash(default_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, admin_id))
            print(f"  ✓ Mot de passe défini pour 'c': {default_password}")
            print("  ⚠️  CHANGEZ CE MOT DE PASSE dès la première connexion!\n")
        else:
            print("  ✓ L'admin 'c' a déjà un mot de passe\n")
    else:
        # Créer l'utilisateur admin
        default_password = 'admin123'
        password_hash = generate_password_hash(default_password)
        cursor.execute("INSERT INTO users (nom, password_hash) VALUES ('c', ?)", (password_hash,))
        print("  ✓ Utilisateur admin 'c' créé")
        print(f"  → Mot de passe par défaut: {default_password}")
        print("  ⚠️  CHANGEZ CE MOT DE PASSE dès la première connexion!\n")
    
    # 3. Mettre à jour les utilisateurs existants sans mot de passe
    print("[3/3] Mise à jour des utilisateurs existants...")
    cursor.execute("SELECT id, nom FROM users WHERE password_hash IS NULL OR password_hash = ''")
    users_sans_mdp = cursor.fetchall()
    
    if users_sans_mdp:
        print(f"  → {len(users_sans_mdp)} utilisateur(s) sans mot de passe trouvé(s)")
        for user_id, nom in users_sans_mdp:
            if nom != 'c':  # On a déjà géré 'c'
                # Générer un mot de passe temporaire : nom123
                temp_password = f"{nom}123"
                password_hash = generate_password_hash(temp_password)
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
                print(f"    • {nom}: mot de passe = {temp_password}")
        print("  ✓ Mots de passe temporaires définis\n")
    else:
        print("  ✓ Tous les utilisateurs ont un mot de passe\n")
    
    # Afficher l'état final
    print("État final:")
    cursor.execute("SELECT COUNT(*) FROM users")
    nb_users = cursor.fetchone()[0]
    print(f"  → Utilisateurs: {nb_users}")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE password_hash IS NOT NULL AND password_hash != ''")
    nb_with_password = cursor.fetchone()[0]
    print(f"  → Avec mot de passe: {nb_with_password}")
    
    # Commit et fermer
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("\n🔑 INFORMATIONS DE CONNEXION:")
    print("─" * 50)
    print("Administrateur:")
    print("  • Nom: c")
    print("  • Mot de passe: admin123")
    print("  ⚠️  CHANGEZ-LE IMMÉDIATEMENT!")
    print("─" * 50)
    
    if users_sans_mdp and len([u for u in users_sans_mdp if u[1] != 'c']) > 0:
        print("\nAutres utilisateurs:")
        for user_id, nom in users_sans_mdp:
            if nom != 'c':
                print(f"  • {nom}: {nom}123")
        print("\n💡 Les utilisateurs peuvent changer leur mot de passe")
        print("   dans leur profil après connexion.")
    
    print("\nProchaines étapes:")
    print("  1. Redémarrez l'application")
    print("  2. Connectez-vous avec 'c' / 'admin123'")
    print("  3. Changez le mot de passe admin")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()