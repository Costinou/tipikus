#!/usr/bin/env python3
"""
Migration Script: Single Auth → Multi-Provider Auth
====================================================

This script migrates the Tipikus database from the old authentication model
(nom + password_hash) to the new multi-provider model (users + auth_providers).

Usage:
    python migrate_to_multi_provider.py [--dry-run]
    
Options:
    --dry-run    Show what would be done without actually modifying the database
"""

import sqlite3
import sys
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DATABASE = 'tipikus.db'
BACKUP_SUFFIX = datetime.now().strftime('%Y%m%d_%H%M%S')


def create_backup():
    """Create a backup of the current database"""
    if not os.path.exists(DATABASE):
        print(f"⚠️  No existing database found at {DATABASE}")
        return None
    
    backup_name = f"{DATABASE}.backup_{BACKUP_SUFFIX}"
    
    print(f"📦 Creating backup: {backup_name}")
    
    # SQLite backup method
    source = sqlite3.connect(DATABASE)
    dest = sqlite3.connect(backup_name)
    
    source.backup(dest)
    
    source.close()
    dest.close()
    
    print(f"✅ Backup created successfully")
    return backup_name


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def check_old_schema_exists():
    """Check if old schema exists"""
    conn = get_db()
    
    # Check if users table has 'nom' column (old schema)
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    has_old_schema = 'nom' in columns
    
    conn.close()
    return has_old_schema


def create_new_schema(conn):
    """Create the new multi-provider schema"""
    print("\n📋 Creating new schema...")
    
    # Create new users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            email TEXT UNIQUE,
            avatar_url TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    print("  ✓ Created users_new table")
    
    # Create auth_providers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auth_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_type TEXT NOT NULL,
            provider_user_id TEXT,
            email TEXT,
            password_hash TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (provider_type, provider_user_id),
            UNIQUE (provider_type, email)
        )
    ''')
    print("  ✓ Created auth_providers table")
    
    # Create indexes
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_user ON auth_providers(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_type ON auth_providers(provider_type)')
    print("  ✓ Created indexes")
    
    conn.commit()


def migrate_old_data(conn, dry_run=False):
    """Migrate data from old schema to new schema"""
    print("\n🔄 Migrating existing data...")
    
    # Check if old users table exists
    old_users = conn.execute('SELECT * FROM users').fetchall()
    
    if not old_users:
        print("  ℹ️  No users to migrate")
        return
    
    print(f"  Found {len(old_users)} users to migrate")
    
    migrated_count = 0
    
    for old_user in old_users:
        # Convert Row to dict for easier access
        old_user_dict = dict(old_user)
        
        user_id = old_user_dict['id']
        nom = old_user_dict['nom']
        password_hash = old_user_dict.get('password_hash')
        created_at = old_user_dict.get('created_at')
        
        # Determine if admin (old logic: nom == 'c')
        is_admin = 1 if nom == 'c' else 0
        
        # Generate email for local provider
        email = f"{nom}@tipikus.local"
        
        if dry_run:
            print(f"  [DRY RUN] Would migrate user: {nom} (admin: {bool(is_admin)})")
            continue
        
        # Insert into users_new
        cursor = conn.execute(
            '''INSERT INTO users_new (display_name, email, is_admin, created_at)
            VALUES (?, ?, ?, ?)''',
            (nom, email, is_admin, created_at)
        )
        new_user_id = cursor.lastrowid
        
        # Insert into auth_providers (local)
        if password_hash:
            conn.execute(
                '''INSERT INTO auth_providers 
                (user_id, provider_type, email, password_hash, created_at, last_used)
                VALUES (?, 'local', ?, ?, ?, ?)''',
                (new_user_id, email, password_hash, created_at, created_at)
            )
        
        # Update foreign keys in other tables
        tables_to_update = [
            'decks',
            'sessions',
            'exercices_resultats'
        ]
        
        for table in tables_to_update:
            try:
                conn.execute(
                    f'UPDATE {table} SET user_id = ? WHERE user_id = ?',
                    (new_user_id, user_id)
                )
            except sqlite3.OperationalError:
                # Table might not exist or have user_id column
                pass
        
        migrated_count += 1
        print(f"  ✓ Migrated: {nom} → user_id={new_user_id}")
    
    if not dry_run:
        conn.commit()
        print(f"\n✅ Migrated {migrated_count} users successfully")


def finalize_migration(conn, dry_run=False):
    """Replace old users table with new one"""
    if dry_run:
        print("\n[DRY RUN] Would finalize migration:")
        print("  - DROP TABLE users")
        print("  - ALTER TABLE users_new RENAME TO users")
        return
    
    print("\n🔨 Finalizing migration...")
    
    # Drop old users table
    conn.execute('DROP TABLE IF EXISTS users')
    print("  ✓ Dropped old users table")
    
    # Rename users_new to users
    conn.execute('ALTER TABLE users_new RENAME TO users')
    print("  ✓ Renamed users_new to users")
    
    conn.commit()
    print("✅ Migration finalized")


def create_fresh_schema():
    """Create fresh schema for new installations"""
    print("\n🆕 Creating fresh multi-provider schema...")
    
    conn = get_db()
    
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            email TEXT UNIQUE,
            avatar_url TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Auth providers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auth_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_type TEXT NOT NULL,
            provider_user_id TEXT,
            email TEXT,
            password_hash TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (provider_type, provider_user_id),
            UNIQUE (provider_type, email)
        )
    ''')
    
    # Indexes
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_user ON auth_providers(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_providers_type ON auth_providers(provider_type)')
    
    # Create default admin user
    cursor = conn.execute(
        '''INSERT INTO users (display_name, email, is_admin, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
        ('Admin', 'admin@tipikus.local', 1)
    )
    admin_id = cursor.lastrowid
    
    # Create local auth for admin (password: admin123)
    password_hash = generate_password_hash('admin123')
    conn.execute(
        '''INSERT INTO auth_providers 
        (user_id, provider_type, email, password_hash, created_at, last_used)
        VALUES (?, 'local', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)''',
        (admin_id, 'admin@tipikus.local', password_hash)
    )
    
    conn.commit()
    conn.close()
    
    print("✅ Fresh schema created")
    print("🔑 Default admin credentials:")
    print("   Email: admin@tipikus.local")
    print("   Password: admin123")
    print("   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")


def verify_migration(conn):
    """Verify the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    # Check users table
    users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    print(f"  ✓ Users table: {users_count} users")
    
    # Check auth_providers table
    providers_count = conn.execute('SELECT COUNT(*) FROM auth_providers').fetchone()[0]
    print(f"  ✓ Auth providers table: {providers_count} providers")
    
    # Check admin exists
    admin = conn.execute('SELECT * FROM users WHERE is_admin = 1').fetchone()
    if admin:
        admin_dict = dict(admin)
        print(f"  ✓ Admin user found: {admin_dict['display_name']}")
    else:
        print("  ⚠️  No admin user found!")
    
    # Check for orphaned auth providers
    orphans = conn.execute('''
        SELECT COUNT(*) FROM auth_providers ap
        LEFT JOIN users u ON ap.user_id = u.id
        WHERE u.id IS NULL
    ''').fetchone()[0]
    
    if orphans > 0:
        print(f"  ⚠️  Found {orphans} orphaned auth providers!")
    else:
        print("  ✓ No orphaned auth providers")
    
    print("\n✅ Verification complete")


def main():
    """Main migration function"""
    dry_run = '--dry-run' in sys.argv
    
    print("="*60)
    print("🚀 TIPIKUS MULTI-PROVIDER AUTH MIGRATION")
    print("="*60)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    
    # Check if database exists
    if not os.path.exists(DATABASE):
        print(f"\n📝 No existing database found. Creating fresh schema...")
        create_fresh_schema()
        return
    
    # Create backup
    if not dry_run:
        backup_file = create_backup()
        if backup_file:
            print(f"💾 Restore command: cp {backup_file} {DATABASE}")
    
    # Check if old schema exists
    if not check_old_schema_exists():
        print("\n⚠️  No old schema found. Database already migrated or empty.")
        return
    
    # Connect to database
    conn = get_db()
    
    try:
        # Create new schema
        create_new_schema(conn)
        
        # Migrate data
        migrate_old_data(conn, dry_run)
        
        # Finalize
        finalize_migration(conn, dry_run)
        
        # Verify
        if not dry_run:
            verify_migration(conn)
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        
        if dry_run:
            print("\n💡 Run without --dry-run to apply changes")
        else:
            print(f"\n💾 Backup saved to: {DATABASE}.backup_{BACKUP_SUFFIX}")
            print("🔄 Restart your application to use the new schema")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        if not dry_run:
            conn.rollback()
            print("\n🔙 Changes rolled back")
        
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == '__main__':
    main()