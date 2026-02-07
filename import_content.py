#!/usr/bin/env python3
"""
Automated Content Import Script for Tipikus
============================================
This script imports lessons, exercises, and decks into the Tipikus database
based on a structured folder organization.

Directory Structure Expected:
- Lessons/          : Markdown lesson files (A1_Chapter1_Title.md)
- Lessons_decks/    : JSON vocabulary decks for lessons (A1_01_DeckName.json)
- Lessons_exercices/: JSON exercise files (A1_02_ExerciseName.json)
- Free_decks/       : JSON decks not associated with lessons (A1_DeckName.json)

Usage:
    # Auto-detect admin user
    python import_content.py --content-dir /path/to/content

    # Specify admin user by ID
    python import_content.py --content-dir /path/to/content --admin-user-id 1

    # Preview changes without importing (dry-run)
    python import_content.py --content-dir /path/to/content --dry-run

    # Use custom database file
    python import_content.py --content-dir /path/to/content --db /path/to/custom.db
"""

import sqlite3
import json
import os
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Database connection
DATABASE = 'tipikus.db'

# Available levels
AVAILABLE_LEVELS = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']


class TipikusImporter:
    """Main importer class for Tipikus content"""
    
    def __init__(self, content_dir: str, admin_user_id: Optional[int] = None, dry_run: bool = False):
        self.content_dir = Path(content_dir)
        self.admin_user_id = admin_user_id
        self.dry_run = dry_run
        self.conn = None
        
        # Directories
        self.lessons_dir = self.content_dir / 'Lessons'
        self.decks_dir = self.content_dir / 'Lessons_decks'
        self.exercises_dir = self.content_dir / 'Lessons_exercices'
        self.free_decks_dir = self.content_dir / 'Free_decks'
        
        # Mapping: lesson_key -> lesson_id
        self.lesson_map: Dict[str, int] = {}
        # Mapping: deck_filename -> deck_id
        self.deck_map: Dict[str, int] = {}
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(DATABASE)
        self.conn.row_factory = sqlite3.Row
        print(f"✓ Connected to database: {DATABASE}")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")
    
    def get_admin_user_id(self) -> int:
        """Get or verify admin user ID"""
        if self.admin_user_id:
            # Verify the provided user ID is an admin
            cursor = self.conn.execute(
                'SELECT id, display_name, is_admin FROM users WHERE id = ?',
                (self.admin_user_id,)
            )
            user = cursor.fetchone()

            if not user:
                raise ValueError(f"User ID {self.admin_user_id} not found in database!")

            if not user['is_admin']:
                raise ValueError(f"User ID {self.admin_user_id} ({user['display_name']}) is not an admin!")

            print(f"✓ Using admin user '{user['display_name']}' (ID: {self.admin_user_id})")
        else:
            # Auto-find first admin user
            cursor = self.conn.execute(
                'SELECT id, display_name FROM users WHERE is_admin = 1 LIMIT 1'
            )
            user = cursor.fetchone()

            if not user:
                raise ValueError("No admin users found in database! Please create an admin user first.")

            self.admin_user_id = user['id']
            print(f"✓ Auto-detected admin user '{user['display_name']}' (ID: {self.admin_user_id})")

        return self.admin_user_id
    
    def parse_filename(self, filename: str) -> Optional[Tuple[str, int, str]]:
        """
        Parse filename to extract level, chapter number, and title.
        
        Expected formats:
        - A1_Chapter1_Title.md -> ('A1', 1, 'Title')
        - A1_01_DeckName.json -> ('A1', 1, 'DeckName')
        - A1_02_Exercise_1.json -> ('A1', 2, 'Exercise_1')
        
        Returns: (level, chapter_number, title) or None if parsing fails
        """
        # Pattern: LEVEL_ChapterN_Title or LEVEL_NN_Title
        pattern = r'^([A-Z]\d\+?)_(Chapter)?(\d+)_(.+)\.(md|json)$'
        match = re.match(pattern, filename)
        
        if match:
            level = match.group(1)
            chapter_num = int(match.group(3))
            title = match.group(4).replace('_', ' ')
            return (level, chapter_num, title)
        
        return None
    
    def import_lessons(self) -> Dict[str, int]:
        """
        Import all lessons from Lessons/ directory.
        Returns mapping of lesson_key -> lesson_id
        """
        print("\n" + "="*60)
        print("📖 IMPORTING LESSONS")
        print("="*60)
        
        if not self.lessons_dir.exists():
            print(f"⚠️  Lessons directory not found: {self.lessons_dir}")
            return {}
        
        lesson_files = sorted(self.lessons_dir.glob('*.md'))
        
        if not lesson_files:
            print("⚠️  No lesson files found")
            return {}
        
        for lesson_file in lesson_files:
            parsed = self.parse_filename(lesson_file.name)
            
            if not parsed:
                print(f"⚠️  Could not parse filename: {lesson_file.name}")
                continue
            
            niveau, numero, titre = parsed
            
            # Read markdown content
            with open(lesson_file, 'r', encoding='utf-8') as f:
                content_markdown = f.read()
            
            # Create lesson key for mapping
            lesson_key = f"{niveau}_{numero:02d}"
            
            print(f"\n[{lesson_key}] {titre}")
            print(f"  Level: {niveau}, Number: {numero}")
            print(f"  Content: {len(content_markdown)} characters")
            
            if self.dry_run:
                print("  [DRY RUN] Would create lesson")
                self.lesson_map[lesson_key] = -1  # Fake ID for dry run
                continue
            
            # Check if lesson already exists
            cursor = self.conn.execute(
                'SELECT id FROM lessons WHERE niveau = ? AND numero = ?',
                (niveau, numero)
            )
            existing = cursor.fetchone()
            
            if existing:
                lesson_id = existing['id']
                print(f"  ⚠️  Lesson already exists (ID: {lesson_id}), updating...")
                self.conn.execute(
                    'UPDATE lessons SET titre = ?, content_markdown = ? WHERE id = ?',
                    (titre, content_markdown, lesson_id)
                )
            else:
                cursor = self.conn.execute(
                    'INSERT INTO lessons (niveau, numero, titre, content_markdown) VALUES (?, ?, ?, ?)',
                    (niveau, numero, titre, content_markdown)
                )
                lesson_id = cursor.lastrowid
                print(f"  ✓ Created lesson ID: {lesson_id}")
            
            self.lesson_map[lesson_key] = lesson_id
        
        if not self.dry_run:
            self.conn.commit()
        
        print(f"\n✓ Imported {len(self.lesson_map)} lessons")
        return self.lesson_map
    
    def import_deck(self, deck_file: Path, lesson_id: Optional[int] = None, 
                    is_common: bool = True) -> Optional[int]:
        """
        Import a single deck from JSON file.
        
        Args:
            deck_file: Path to JSON file
            lesson_id: Optional lesson ID to associate with
            is_common: Whether deck is common (visible to all users)
        
        Returns: deck_id or None if failed
        """
        parsed = self.parse_filename(deck_file.name)
        
        if not parsed:
            print(f"⚠️  Could not parse filename: {deck_file.name}")
            return None
        
        niveau, chapter_num, nom_deck = parsed
        
        # Read JSON content
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                mots_dict = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {deck_file.name}: {e}")
            return None
        
        if not isinstance(mots_dict, dict):
            print(f"❌ JSON must be a dictionary in {deck_file.name}")
            return None
        
        print(f"  📦 {nom_deck}")
        print(f"    Level: {niveau}, Words: {len(mots_dict)}")
        
        if lesson_id:
            print(f"    Associated with lesson ID: {lesson_id}")
        
        if self.dry_run:
            print("    [DRY RUN] Would create deck")
            return -1
        
        # Check if deck already exists
        cursor = self.conn.execute(
            'SELECT id FROM decks WHERE nom = ? AND niveau = ? AND user_id = ?',
            (nom_deck, niveau, self.admin_user_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            deck_id = existing['id']
            print(f"    ⚠️  Deck already exists (ID: {deck_id}), updating...")
            
            # Update lesson association if provided
            if lesson_id:
                self.conn.execute(
                    'UPDATE decks SET lesson_id = ? WHERE id = ?',
                    (lesson_id, deck_id)
                )
            
            # Update words
            self.conn.execute('DELETE FROM mots WHERE deck_id = ?', (deck_id,))
        else:
            cursor = self.conn.execute(
                'INSERT INTO decks (nom, niveau, user_id, is_commun, lesson_id) VALUES (?, ?, ?, ?, ?)',
                (nom_deck, niveau, self.admin_user_id, 1 if is_common else 0, lesson_id)
            )
            deck_id = cursor.lastrowid
            print(f"    ✓ Created deck ID: {deck_id}")
        
        # Add words
        for mot_francais, traduction in mots_dict.items():
            self.conn.execute(
                'INSERT INTO mots (deck_id, mot_francais, traduction) VALUES (?, ?, ?)',
                (deck_id, mot_francais, traduction)
            )
        
        print(f"    ✓ Added {len(mots_dict)} words")
        
        return deck_id
    
    def import_lesson_decks(self):
        """Import all decks from Lessons_decks/ and associate with lessons"""
        print("\n" + "="*60)
        print("📚 IMPORTING LESSON DECKS")
        print("="*60)
        
        if not self.decks_dir.exists():
            print(f"⚠️  Decks directory not found: {self.decks_dir}")
            return
        
        deck_files = sorted(self.decks_dir.glob('*.json'))
        
        if not deck_files:
            print("⚠️  No deck files found")
            return
        
        for deck_file in deck_files:
            parsed = self.parse_filename(deck_file.name)
            
            if not parsed:
                print(f"⚠️  Could not parse filename: {deck_file.name}")
                continue
            
            niveau, chapter_num, _ = parsed
            lesson_key = f"{niveau}_{chapter_num:02d}"
            
            # Find associated lesson
            lesson_id = self.lesson_map.get(lesson_key)
            
            if not lesson_id:
                print(f"⚠️  No lesson found for {lesson_key}, importing as free deck")
                lesson_id = None
            
            # Import deck
            deck_id = self.import_deck(deck_file, lesson_id=lesson_id, is_common=True)
            
            if deck_id:
                self.deck_map[deck_file.name] = deck_id
        
        if not self.dry_run:
            self.conn.commit()
        
        print(f"\n✓ Imported {len(self.deck_map)} lesson decks")
    
    def import_free_decks(self):
        """Import decks from Free_decks/ (not associated with lessons)"""
        print("\n" + "="*60)
        print("🆓 IMPORTING FREE DECKS")
        print("="*60)
        
        if not self.free_decks_dir.exists():
            print(f"⚠️  Free decks directory not found: {self.free_decks_dir}")
            return
        
        deck_files = sorted(self.free_decks_dir.glob('*.json'))
        
        if not deck_files:
            print("⚠️  No free deck files found")
            return
        
        for deck_file in deck_files:
            deck_id = self.import_deck(deck_file, lesson_id=None, is_common=True)
            
            if deck_id:
                self.deck_map[deck_file.name] = deck_id
        
        if not self.dry_run:
            self.conn.commit()
        
        print(f"\n✓ Imported free decks")
    
    def import_exercises(self):
        """Import exercises from Lessons_exercices/ and associate with lessons"""
        print("\n" + "="*60)
        print("✍️  IMPORTING EXERCISES")
        print("="*60)
        
        if not self.exercises_dir.exists():
            print(f"⚠️  Exercises directory not found: {self.exercises_dir}")
            return
        
        exercise_files = sorted(self.exercises_dir.glob('*.json'))
        
        if not exercise_files:
            print("⚠️  No exercise files found")
            return
        
        for exercise_file in exercise_files:
            parsed = self.parse_filename(exercise_file.name)
            
            if not parsed:
                print(f"⚠️  Could not parse filename: {exercise_file.name}")
                continue
            
            niveau, chapter_num, titre = parsed
            lesson_key = f"{niveau}_{chapter_num:02d}"
            
            # Find associated lesson
            lesson_id = self.lesson_map.get(lesson_key)
            
            if not lesson_id:
                print(f"⚠️  No lesson found for {lesson_key}, skipping exercise: {exercise_file.name}")
                continue
            
            # Read JSON content
            try:
                with open(exercise_file, 'r', encoding='utf-8') as f:
                    contenu_json = json.load(f)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in {exercise_file.name}: {e}")
                continue
            
            if not isinstance(contenu_json, list):
                print(f"❌ JSON must be a list in {exercise_file.name}")
                continue
            
            # Validate structure
            valid = True
            for item in contenu_json:
                if not all(k in item for k in ['phrase', 'reponses_valides']):
                    print(f"❌ Invalid structure in {exercise_file.name}")
                    valid = False
                    break
            
            if not valid:
                continue
            
            print(f"\n  ✍️  {titre}")
            print(f"    Level: {niveau}, Lesson: {lesson_key}")
            print(f"    Questions: {len(contenu_json)}")
            
            if self.dry_run:
                print("    [DRY RUN] Would create exercise")
                continue
            
            # Get current order (number of existing exercises for this lesson)
            cursor = self.conn.execute(
                'SELECT COUNT(*) as count FROM exercices WHERE lesson_id = ?',
                (lesson_id,)
            )
            ordre = cursor.fetchone()['count']
            
            # Check if exercise already exists
            cursor = self.conn.execute(
                'SELECT id FROM exercices WHERE lesson_id = ? AND titre = ?',
                (lesson_id, titre)
            )
            existing = cursor.fetchone()
            
            if existing:
                exercice_id = existing['id']
                print(f"    ⚠️  Exercise already exists (ID: {exercice_id}), updating...")
                
                # Delete old content
                self.conn.execute('DELETE FROM exercices_contenu WHERE exercice_id = ?', (exercice_id,))
            else:
                # Create exercise
                config = json.dumps({'show_hints': True, 'case_sensitive': False})
                cursor = self.conn.execute(
                    '''INSERT INTO exercices (lesson_id, type_exercice, titre, description, ordre, config)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (lesson_id, 'fill_blank', titre, '', ordre, config)
                )
                exercice_id = cursor.lastrowid
                print(f"    ✓ Created exercise ID: {exercice_id}")
            
            # Add content
            for i, contenu in enumerate(contenu_json):
                contenu_str = json.dumps(contenu, ensure_ascii=False)
                self.conn.execute(
                    'INSERT INTO exercices_contenu (exercice_id, contenu, ordre) VALUES (?, ?, ?)',
                    (exercice_id, contenu_str, i)
                )
            
            print(f"    ✓ Added {len(contenu_json)} questions")
        
        if not self.dry_run:
            self.conn.commit()
        
        print(f"\n✓ Imported exercises")
    
    def run(self):
        """Run the complete import process"""
        try:
            print("\n" + "="*60)
            print("🚀 TIPIKUS CONTENT IMPORTER")
            print("="*60)
            print(f"Content directory: {self.content_dir}")
            print(f"Dry run: {self.dry_run}")
            print("="*60)
            
            # Connect to database
            self.connect()
            
            # Get admin user ID
            self.get_admin_user_id()
            
            # Import in order
            self.import_lessons()
            self.import_lesson_decks()
            self.import_free_decks()
            self.import_exercises()
            
            # Summary
            print("\n" + "="*60)
            print("✅ IMPORT COMPLETE")
            print("="*60)
            print(f"Lessons imported: {len(self.lesson_map)}")
            print(f"Decks imported: {len(self.deck_map)}")
            
            if self.dry_run:
                print("\n⚠️  DRY RUN MODE - No changes were made to the database")
            else:
                print("\n✓ All changes committed to database")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import lessons, decks, and exercises into Tipikus database'
    )
    parser.add_argument(
        '--content-dir',
        type=str,
        required=True,
        help='Path to content directory containing Lessons/, Lessons_decks/, etc.'
    )
    parser.add_argument(
        '--admin-user-id',
        type=int,
        default=None,
        help='Admin user ID (default: auto-detect first admin user)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying database'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='tipikus.db',
        help='Path to database file (default: tipikus.db)'
    )
    
    args = parser.parse_args()
    
    # Update global DATABASE variable
    global DATABASE
    DATABASE = args.db
    
    # Validate content directory
    content_dir = Path(args.content_dir)
    if not content_dir.exists():
        print(f"❌ Content directory not found: {content_dir}")
        sys.exit(1)
    
    # Run importer
    importer = TipikusImporter(
        content_dir=str(content_dir),
        admin_user_id=args.admin_user_id,
        dry_run=args.dry_run
    )
    importer.run()


if __name__ == '__main__':
    main()