"""
Migration Script: Add tour completion columns to users table
============================================================
This script adds two new columns to the users table:
- tour_completed: tracks if user has completed the onboarding tour
- lesson_tour_completed: tracks if user has completed the lesson tour

Usage:
    python3 migrate_tour_columns.py

Optional: Mark existing users as already completed (they won't see tours again):
    python3 migrate_tour_columns.py --mark-existing-completed
"""

import sqlite3
import sys
import os

# Database path - update if needed for remote server
DATABASE_PATH = 'tipikus.db'

def run_migration(mark_existing_completed=False):
    """Run the migration to add tour completion columns"""

    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Error: Database file '{DATABASE_PATH}' not found!")
        print(f"   Current directory: {os.getcwd()}")
        return False

    print(f"📊 Running migration on: {DATABASE_PATH}")
    print()

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Add tour_completed column
        try:
            conn.execute('ALTER TABLE users ADD COLUMN tour_completed BOOLEAN DEFAULT 0')
            print('✓ Added tour_completed column')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print('✓ tour_completed column already exists')
            else:
                raise

        # Add lesson_tour_completed column
        try:
            conn.execute('ALTER TABLE users ADD COLUMN lesson_tour_completed BOOLEAN DEFAULT 0')
            print('✓ Added lesson_tour_completed column')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print('✓ lesson_tour_completed column already exists')
            else:
                raise

        conn.commit()
        print()

        # Optional: Mark existing users as completed
        if mark_existing_completed:
            cursor = conn.execute('UPDATE users SET tour_completed = 1, lesson_tour_completed = 1')
            count = cursor.rowcount
            conn.commit()
            print(f'✓ Marked {count} existing user(s) as having completed both tours')
            print()

        # Verify the migration
        cursor = conn.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]

        if 'tour_completed' in columns and 'lesson_tour_completed' in columns:
            print('✅ Migration successful!')
            print()
            print('Column list:', ', '.join(columns))

            # Show user count
            cursor = conn.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            print(f'Total users in database: {user_count}')

            return True
        else:
            print('❌ Migration verification failed!')
            return False

    except Exception as e:
        print(f'❌ Error during migration: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Tipikus Database Migration - Tour Completion Columns")
    print("=" * 60)
    print()

    # Check for --mark-existing-completed flag
    mark_existing = '--mark-existing-completed' in sys.argv

    if mark_existing:
        print("⚠️  Option: Existing users will be marked as having completed tours")
        print("   (They won't see the tours again)")
        print()

    # Run migration
    success = run_migration(mark_existing_completed=mark_existing)

    print()
    if success:
        print("🎉 Migration completed successfully!")
        if not mark_existing:
            print()
            print("💡 Note: Existing users will see the tour once more.")
            print("   To skip this, run: python3 migrate_tour_columns.py --mark-existing-completed")
    else:
        print("❌ Migration failed!")
        sys.exit(1)

    print()
    print("=" * 60)
