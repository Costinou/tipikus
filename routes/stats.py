"""
Tipikus Routes - Stats Blueprint
=================================
Statistics display routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import (
    get_user_by_id,
    get_deck_by_id,
    get_decks_by_niveau,
    get_stats_deck,
    get_stats_niveau,
    get_stats_globales,
    calculer_streak,
    AVAILABLE_LEVELS
)

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


@stats_bp.route('/deck/<int:deck_id>')
def stats_deck(deck_id):
    """Display deck statistics for logged in user"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck not found')
            return redirect(url_for('main.index'))

        # Pass user_id to stats function
        stats = get_stats_deck(deck_id, user_id, days=30)

        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak

        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None

        return render_template('stats_deck.html', deck=deck, stats=stats)

    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))


@stats_bp.route('/niveau/<niveau>')
def stats_niveau_route(niveau):
    """Display level statistics for logged in user"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        if niveau not in AVAILABLE_LEVELS:
            flash('Level not found')
            return redirect(url_for('main.index'))

        # Pass user_id to stats function
        stats = get_stats_niveau(niveau, user_id, days=30)
        decks = get_decks_by_niveau(niveau, user_id)

        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak

        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None

        user = get_user_by_id(user_id)

        return render_template('stats_niveau.html', niveau=niveau, stats=stats, decks=decks, user=user)

    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))


@stats_bp.route('/')
def stats_globales():
    """Display global statistics for logged in user"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        # Pass user_id to stats function
        stats = get_stats_globales(user_id, days=30)

        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak

        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None

        total_duree = stats.get('total_duree', 0) or 0
        stats['total_heures'] = total_duree // 3600
        stats['total_minutes'] = (total_duree % 3600) // 60

        stats_par_niveau = stats.get('stats_par_niveau', {})

        user = get_user_by_id(user_id)

        return render_template('stats_globales.html',
                             stats_totales=stats,
                             stats_par_niveau=stats_par_niveau,
                             user=user)

    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))
