#!/usr/bin/env python3
"""
Script pour gérer les administrateurs Tipikus
==============================================

Usage:
    python3 make_admin.py list              - Liste tous les utilisateurs
    python3 make_admin.py add <user_id>     - Rendre un utilisateur admin
    python3 make_admin.py remove <user_id>  - Retirer les droits admin
    python3 make_admin.py email <email>     - Rendre admin par email

Exemples:
    python3 make_admin.py list
    python3 make_admin.py add 2
    python3 make_admin.py email john@example.com
"""

from database import get_db, get_all_users, get_user_by_email
import sys


def list_users():
    """Affiche tous les utilisateurs avec leur statut admin"""
    users = get_all_users()
    
    print()
    print("=" * 80)
    print("👥 LISTE DES UTILISATEURS")
    print("=" * 80)
    print()
    print(f"{'ID':>4} {'Display Name':<25} {'Email':<35} {'Status':<10}")
    print("-" * 80)
    
    for user in users:
        admin_badge = "👑 ADMIN" if user.get('is_admin') else ""
        email = user.get('email', 'N/A')
        
        print(f"{user['id']:>4} {user['display_name']:<25} {email:<35} {admin_badge:<10}")
    
    print("-" * 80)
    print(f"Total: {len(users)} user(s)")
    
    # Compter les admins
    admin_count = sum(1 for u in users if u.get('is_admin'))
    print(f"Admins: {admin_count}")
    print("=" * 80)
    print()


def make_admin_by_id(user_id):
    """Rend un utilisateur admin par ID"""
    conn = get_db()
    
    # Vérifier que l'utilisateur existe
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        print(f"❌ User ID {user_id} not found")
        conn.close()
        return False
    
    user_dict = dict(user)
    display_name = user_dict.get('display_name', 'Unknown')
    email = user_dict.get('email', 'N/A')
    
    # Vérifier s'il est déjà admin
    if user_dict.get('is_admin'):
        print(f"ℹ️  {display_name} ({email}) is already admin")
        conn.close()
        return True
    
    # Promouvoir en admin
    conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    print()
    print("✅ SUCCESS")
    print(f"   {display_name} ({email}) is now admin!")
    print()
    
    return True


def make_admin_by_email(email):
    """Rend un utilisateur admin par email"""
    user = get_user_by_email(email)
    
    if not user:
        print(f"❌ User with email '{email}' not found")
        return False
    
    return make_admin_by_id(user['id'])


def remove_admin_by_id(user_id):
    """Retire les privilèges admin d'un utilisateur"""
    conn = get_db()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        print(f"❌ User ID {user_id} not found")
        conn.close()
        return False
    
    user_dict = dict(user)
    display_name = user_dict.get('display_name', 'Unknown')
    email = user_dict.get('email', 'N/A')
    
    if not user_dict.get('is_admin'):
        print(f"ℹ️  {display_name} ({email}) is not admin")
        conn.close()
        return True
    
    # Vérifier qu'il reste au moins un admin
    admin_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = 1').fetchone()['count']
    
    if admin_count <= 1:
        print("❌ Cannot remove last admin")
        print("   At least one admin must remain")
        conn.close()
        return False
    
    # Retirer les privilèges
    conn.execute('UPDATE users SET is_admin = 0 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    print()
    print("✅ SUCCESS")
    print(f"   {display_name} ({email}) is no longer admin")
    print()
    
    return True


def show_help():
    """Affiche l'aide"""
    print()
    print("=" * 80)
    print("🔐 TIPIKUS ADMIN MANAGER")
    print("=" * 80)
    print()
    print("Usage:")
    print("  python3 make_admin.py list                    - List all users")
    print("  python3 make_admin.py add <user_id>           - Make user admin by ID")
    print("  python3 make_admin.py remove <user_id>        - Remove admin by ID")
    print("  python3 make_admin.py email <email>           - Make user admin by email")
    print()
    print("Examples:")
    print("  python3 make_admin.py list")
    print("  python3 make_admin.py add 2")
    print("  python3 make_admin.py email john@example.com")
    print("  python3 make_admin.py remove 3")
    print()
    print("=" * 80)
    print()


def main():
    """Fonction principale"""
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    action = sys.argv[1].lower()
    
    if action in ['help', '-h', '--help']:
        show_help()
    
    elif action == 'list':
        list_users()
    
    elif action == 'add':
        if len(sys.argv) < 3:
            print("❌ User ID required")
            print("Usage: python3 make_admin.py add <user_id>")
            print()
            print("Tip: Use 'python3 make_admin.py list' to see all user IDs")
            return
        
        try:
            user_id = int(sys.argv[2])
            make_admin_by_id(user_id)
        except ValueError:
            print("❌ Invalid user ID (must be a number)")
    
    elif action == 'email':
        if len(sys.argv) < 3:
            print("❌ Email required")
            print("Usage: python3 make_admin.py email <email>")
            return
        
        email = sys.argv[2]
        make_admin_by_email(email)
    
    elif action == 'remove':
        if len(sys.argv) < 3:
            print("❌ User ID required")
            print("Usage: python3 make_admin.py remove <user_id>")
            return
        
        try:
            user_id = int(sys.argv[2])
            remove_admin_by_id(user_id)
        except ValueError:
            print("❌ Invalid user ID (must be a number)")
    
    else:
        print(f"❌ Unknown action: {action}")
        print()
        show_help()


if __name__ == "__main__":
    main()