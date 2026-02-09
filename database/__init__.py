"""
Tipikus Database Package
========================
Modular database package with backward compatibility

Re-exports all database functions from submodules for backward compatibility.
Import from this package works exactly like the old single database.py file.

Usage:
    from database import get_db, get_user_by_id, create_deck, etc.
"""

# Core - Database connection and initialization
from .core import (
    DATABASE,
    AVAILABLE_LEVELS,
    get_db,
    init_db
)

# Users - User management
from .users import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_name,
    get_all_users,
    create_user,
    update_user,
    delete_user,
    mark_tour_completed,
    mark_lesson_tour_completed
)

# Auth - Authentication and auth providers
from .auth import (
    add_auth_provider,
    remove_auth_provider,
    update_password,
    authenticate_local,
    authenticate_oauth,
    verify_user_password,
    update_user_password
)

# Decks - Deck and vocabulary management
from .decks import (
    get_niveaux_with_counts,
    get_decks_by_niveau,
    create_deck,
    get_deck_by_id,
    add_mots_to_deck,
    get_mots_by_deck,
    get_mots_by_deck_ordered,
    delete_deck,
    can_delete_deck
)

# Lessons - Lesson management
from .lessons import (
    get_lessons_by_niveau,
    get_lesson_by_id,
    create_lesson,
    update_lesson,
    delete_lesson,
    get_decks_by_lesson,
    associate_deck_to_lesson,
    detach_deck_from_lesson
)

# Sessions - Session tracking and statistics
from .sessions import (
    create_session,
    get_stats_deck,
    get_stats_niveau,
    get_stats_globales,
    calculer_streak,
    get_users_with_stats,
    get_recent_sessions
)

# Exercises - Exercise management
from .exercises import (
    create_exercice,
    get_exercices_by_lesson,
    get_exercice_by_id,
    delete_exercice,
    add_exercice_contenu,
    get_exercice_contenu,
    create_exercice_resultat,
    get_exercice_stats
)

# Progression - XP and level progression
from .progression import (
    calculate_niveau_total_xp,
    calculate_user_xp_for_niveau,
    calculate_niveau_progress_xp,
    get_xp_breakdown,
    get_unlocked_niveaux_xp,
    has_user_seen_all_cards,
    get_deck_total_words,
    calculate_lesson_progress,
    get_quiz_success_rate
)

# Define __all__ for explicit exports
__all__ = [
    # Core
    'DATABASE',
    'AVAILABLE_LEVELS',
    'get_db',
    'init_db',

    # Users
    'get_user_by_id',
    'get_user_by_email',
    'get_user_by_name',
    'get_all_users',
    'create_user',
    'update_user',
    'delete_user',
    'mark_tour_completed',
    'mark_lesson_tour_completed',

    # Auth
    'add_auth_provider',
    'remove_auth_provider',
    'update_password',
    'authenticate_local',
    'authenticate_oauth',
    'verify_user_password',
    'update_user_password',

    # Decks
    'get_niveaux_with_counts',
    'get_decks_by_niveau',
    'create_deck',
    'get_deck_by_id',
    'add_mots_to_deck',
    'get_mots_by_deck',
    'get_mots_by_deck_ordered',
    'delete_deck',
    'can_delete_deck',

    # Lessons
    'get_lessons_by_niveau',
    'get_lesson_by_id',
    'create_lesson',
    'update_lesson',
    'delete_lesson',
    'get_decks_by_lesson',
    'associate_deck_to_lesson',
    'detach_deck_from_lesson',

    # Sessions
    'create_session',
    'get_stats_deck',
    'get_stats_niveau',
    'get_stats_globales',
    'calculer_streak',
    'get_users_with_stats',
    'get_recent_sessions',

    # Exercises
    'create_exercice',
    'get_exercices_by_lesson',
    'get_exercice_by_id',
    'delete_exercice',
    'add_exercice_contenu',
    'get_exercice_contenu',
    'create_exercice_resultat',
    'get_exercice_stats',

    # Progression
    'calculate_niveau_total_xp',
    'calculate_user_xp_for_niveau',
    'calculate_niveau_progress_xp',
    'get_xp_breakdown',
    'get_unlocked_niveaux_xp',
    'has_user_seen_all_cards',
    'get_deck_total_words',
    'calculate_lesson_progress',
    'get_quiz_success_rate',
]
