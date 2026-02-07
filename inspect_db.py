#!/usr/bin/env python3
"""
Database Inspection Script
Affiche la structure et le contenu de la base de données Tipikus
"""

import sqlite3
import json

DATABASE = 'tipikus.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    print("="*60)
    print("🔍 TIPIKUS DATABASE INSPECTION")
    print("="*60)
    
    conn = get_db()
    
    # Liste des tables
    print("\n📋 TABLES:")
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    
    for table in tables:
        table_name = table['name']
        if table_name.startswith('sqlite_'):
            continue
        
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  - {table_name:<30} ({count} rows)")
    
    # Schema de users
    print("\n📊 USERS TABLE SCHEMA:")
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    
    if schema:
        print(schema['sql'])
    
    # Schema de auth_providers
    print("\n🔐 AUTH_PROVIDERS TABLE SCHEMA:")
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_providers'"
    ).fetchone()
    
    if schema:
        print(schema['sql'])
    
    # Contenu users
    print("\n👥 USERS:")
    users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    
    if users:
        for user in users:
            user_dict = dict(user)
            print(f"\n  User #{user_dict['id']}:")
            print(f"    Display Name: {user_dict['display_name']}")
            print(f"    Email: {user_dict['email']}")
            print(f"    Admin: {'Yes' if user_dict['is_admin'] else 'No'}")
            print(f"    Created: {user_dict['created_at']}")
            
            # Auth providers pour cet user
            providers = conn.execute(
                "SELECT * FROM auth_providers WHERE user_id = ?",
                (user_dict['id'],)
            ).fetchall()
            
            if providers:
                print(f"    Auth Providers:")
                for provider in providers:
                    provider_dict = dict(provider)
                    print(f"      - {provider_dict['provider_type']:<10} | {provider_dict['email']}")
                    if provider_dict.get('metadata'):
                        try:
                            metadata = json.loads(provider_dict['metadata'])
                            print(f"        Metadata: {metadata}")
                        except:
                            pass
    else:
        print("  No users found")
    
    # Stats globales
    print("\n📈 STATISTICS:")
    
    # Total decks
    try:
        decks_count = conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0]
        print(f"  Decks: {decks_count}")
    except:
        print("  Decks: N/A")
    
    # Total sessions
    try:
        sessions_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        print(f"  Sessions: {sessions_count}")
    except:
        print("  Sessions: N/A")
    
    # Total lessons
    try:
        lessons_count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        print(f"  Lessons: {lessons_count}")
    except:
        print("  Lessons: N/A")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ Inspection complete")
    print("="*60)

if __name__ == '__main__':
    main()