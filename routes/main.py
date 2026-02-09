"""
Tipikus Routes - Main Blueprint
================================
Main application routes (index, niveau)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import (
    get_user_by_id,
    get_niveaux_with_counts,
    get_decks_by_niveau,
    get_deck_by_id,
    get_lessons_by_niveau,
    calculate_niveau_progress_xp,
    calculate_user_xp_for_niveau,
    calculate_niveau_total_xp,
    get_unlocked_niveaux_xp,
    calculate_lesson_progress,
    get_xp_breakdown,
    AVAILABLE_LEVELS
)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - Level selection"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # Get levels with deck counter
    niveaux_counts = get_niveaux_with_counts(user_id)

    # Calculate XP-based progress for each level
    niveaux_progress = {}
    niveaux_xp = {}

    for niveau in AVAILABLE_LEVELS:
        # Progression XP
        niveaux_progress[niveau] = calculate_niveau_progress_xp(user_id, niveau)

        # Détails XP
        xp_data = calculate_user_xp_for_niveau(user_id, niveau)
        xp_total = calculate_niveau_total_xp(niveau)

        niveaux_xp[niveau] = {
            'xp_gagne': xp_data['xp_total'],
            'xp_total': xp_total
        }

    # Get unlocked levels (XP-based)
    unlocked_niveaux = get_unlocked_niveaux_xp(user_id)

    # Check if user should see the onboarding tour (from database)
    show_tour = not user.get('tour_completed', False)

    # Get last studied deck for review suggestion
    last_deck = None
    last_deck_id = session.get('last_studied_deck_id')
    if last_deck_id:
        last_deck = get_deck_by_id(last_deck_id)

    return render_template('index.html',
                         AVAILABLE_LEVELS=AVAILABLE_LEVELS,
                         niveaux_counts=niveaux_counts,
                         niveaux_progress=niveaux_progress,
                         niveaux_xp=niveaux_xp,
                         unlocked_niveaux=unlocked_niveaux,
                         user=user,
                         show_tour=show_tour,
                         last_studied_deck=last_deck)


@main_bp.route('/niveau/<niveau>')
def niveau(niveau):
    """Level page - List of lessons and decks"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    if niveau not in AVAILABLE_LEVELS:
        flash(f'Level "{niveau}" not supported')
        return redirect(url_for('main.index'))

    # Check if level is unlocked (XP-based) - STRICT CHECK
    unlocked_niveaux = get_unlocked_niveaux_xp(user_id)
    if niveau not in unlocked_niveaux:
        # Get previous level info for error message
        prev_index = AVAILABLE_LEVELS.index(niveau) - 1
        prev_niveau = AVAILABLE_LEVELS[prev_index] if prev_index >= 0 else 'A1'
        if prev_niveau == 'Custom' and prev_index > 0:
            prev_niveau = AVAILABLE_LEVELS[prev_index - 1]

        prev_progress = calculate_niveau_progress_xp(user_id, prev_niveau)

        flash(f'🔒 Level {niveau} is locked. Complete level {prev_niveau} to 80% to unlock it. (Current: {prev_progress:.1f}%)')
        return redirect(url_for('main.index'))

    # Get lessons for this level
    lessons = get_lessons_by_niveau(niveau)

    # Calculate progress for each lesson (keep old system for lessons)
    lessons_progress = {}
    for lesson in lessons:
        lessons_progress[lesson['id']] = calculate_lesson_progress(user_id, lesson['id'])

    # Get decks OUTSIDE lessons
    all_decks = get_decks_by_niveau(niveau, user_id, include_in_lessons=False)

    user = get_user_by_id(user_id)
    is_admin = user.get('is_admin')

    # Separate decks
    decks_communs = [d for d in all_decks if d['is_commun']]

    if is_admin:
        decks_perso_admin = [d for d in all_decks if not d['is_commun'] and d['user_id'] == user_id]
        decks_perso_autres = [d for d in all_decks if not d['is_commun'] and d['user_id'] != user_id]
    else:
        decks_perso_admin = []
        decks_perso_autres = []
        decks_perso = [d for d in all_decks if not d['is_commun']]

    # Get XP breakdown for this level
    xp_breakdown = get_xp_breakdown(user_id, niveau)

    return render_template('niveau.html',
                         niveau=niveau,
                         lessons=lessons,
                         lessons_progress=lessons_progress,
                         decks_communs=decks_communs,
                         decks_perso=decks_perso if not is_admin else decks_perso_admin,
                         decks_perso_autres=decks_perso_autres if is_admin else [],
                         user=user,
                         is_admin=is_admin,
                         xp_breakdown=xp_breakdown)
