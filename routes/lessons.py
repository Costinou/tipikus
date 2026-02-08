"""
Tipikus Routes - Lessons Blueprint
===================================
Lesson management routes (CRUD, deck association)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import (
    get_user_by_id,
    get_lesson_by_id,
    get_lessons_by_niveau,
    create_lesson,
    update_lesson,
    delete_lesson,
    get_decks_by_lesson,
    get_exercices_by_lesson,
    get_decks_by_niveau,
    get_deck_by_id,
    associate_deck_to_lesson,
    detach_deck_from_lesson,
    AVAILABLE_LEVELS
)

lessons_bp = Blueprint('lessons', __name__)


@lessons_bp.route('/lesson/<int:lesson_id>')
def view_lesson(lesson_id):
    """Display a lesson with its markdown content, decks and exercises"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    # Get decks for this lesson
    decks = get_decks_by_lesson(lesson_id)

    # Get exercises for this lesson
    exercices = get_exercices_by_lesson(lesson_id)

    user = get_user_by_id(user_id)

    # Check if user should see the lesson tour
    show_lesson_tour = session.get('lesson_tour_completed') is None

    return render_template('lesson.html',
                         lesson=lesson,
                         decks=decks,
                         exercices=exercices,
                         user=user,
                         show_lesson_tour=show_lesson_tour)


@lessons_bp.route('/create-lesson', methods=['GET'])
def create_lesson_form():
    """Lesson creation form (admin only)"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    # Check that it's admin
    if not session.get('is_admin'):
        flash('Only administrators can create lessons')
        return redirect(url_for('main.index'))

    user = get_user_by_id(user_id)
    return render_template('create_lesson.html', niveaux=AVAILABLE_LEVELS, user=user)


@lessons_bp.route('/create-lesson', methods=['POST'])
def create_lesson_post():
    """Process lesson creation"""
    user_id = session.get('user_id')

    if not user_id or not session.get('is_admin'):
        flash('Only administrators can create lessons')
        return redirect(url_for('main.index'))

    niveau = request.form.get('niveau', '').strip()
    numero = request.form.get('numero', '').strip()
    titre = request.form.get('titre', '').strip()
    fichier_md = request.files.get('fichier_md')

    # Validations
    if niveau not in AVAILABLE_LEVELS:
        flash('Invalid level')
        return redirect(url_for('lessons.create_lesson_form'))

    try:
        numero = int(numero)
        if numero < 1:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Number must be a positive integer')
        return redirect(url_for('lessons.create_lesson_form'))

    if not titre:
        flash('Title is required')
        return redirect(url_for('lessons.create_lesson_form'))

    if not fichier_md or not fichier_md.filename.endswith('.md'):
        flash('Please select a .md file')
        return redirect(url_for('lessons.create_lesson_form'))

    try:
        # Read markdown file content
        content_markdown = fichier_md.read().decode('utf-8')

        # Create lesson
        lesson_id = create_lesson(niveau, numero, titre, content_markdown)

        if lesson_id is None:
            flash(f'A lesson {numero} already exists for level {niveau}')
            return redirect(url_for('lessons.create_lesson_form'))

        flash(f'Lesson "{titre}" created successfully!')
        return redirect(url_for('lessons.view_lesson', lesson_id=lesson_id))

    except Exception as e:
        flash(f'Error during creation: {str(e)}')
        return redirect(url_for('lessons.create_lesson_form'))


@lessons_bp.route('/delete-lesson/<int:lesson_id>', methods=['POST'])
def delete_lesson_route(lesson_id):
    """Delete a lesson (admin only)"""
    if not session.get('is_admin'):
        flash('Only administrators can delete lessons')
        return redirect(url_for('main.index'))

    try:
        lesson = get_lesson_by_id(lesson_id)
        if not lesson:
            flash('Lesson not found')
            return redirect(url_for('main.index'))

        niveau = lesson['niveau']
        titre = lesson['titre']

        delete_lesson(lesson_id)

        flash(f'Lesson "{titre}" deleted successfully')
        return redirect(url_for('main.niveau', niveau=niveau))

    except Exception as e:
        flash(f'Error during deletion: {str(e)}')
        return redirect(url_for('main.index'))


@lessons_bp.route('/edit-lesson/<int:lesson_id>', methods=['GET'])
def edit_lesson_form(lesson_id):
    """Lesson editing form (admin only)"""
    user_id = session.get('user_id')

    if not user_id or not session.get('is_admin'):
        flash('Only administrators can edit lessons')
        return redirect(url_for('main.index'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    user = get_user_by_id(user_id)
    return render_template('edit_lesson.html', lesson=lesson, user=user)


@lessons_bp.route('/edit-lesson/<int:lesson_id>', methods=['POST'])
def edit_lesson_post(lesson_id):
    """Process lesson modification"""
    if not session.get('is_admin'):
        flash('Only administrators can edit lessons')
        return redirect(url_for('main.index'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    titre = request.form.get('titre', '').strip()
    fichier_md = request.files.get('fichier_md')

    # Validations
    if not titre:
        flash('Title is required')
        return redirect(url_for('lessons.edit_lesson_form', lesson_id=lesson_id))

    try:
        # If new file uploaded, read it
        if fichier_md and fichier_md.filename and fichier_md.filename.endswith('.md'):
            content_markdown = fichier_md.read().decode('utf-8')
        else:
            # Otherwise, keep old content
            content_markdown = lesson['content_markdown']

        # Update lesson
        update_lesson(lesson_id, titre, content_markdown)

        flash(f'Lesson "{titre}" modified successfully!')
        return redirect(url_for('lessons.view_lesson', lesson_id=lesson_id))

    except Exception as e:
        flash(f'Error during modification: {str(e)}')
        return redirect(url_for('lessons.edit_lesson_form', lesson_id=lesson_id))


@lessons_bp.route('/manage-lesson-decks/<int:lesson_id>')
def manage_lesson_decks(lesson_id):
    """Interface to manage lesson decks (admin only)"""
    user_id = session.get('user_id')

    if not user_id or not session.get('is_admin'):
        flash('Only administrators can manage lessons')
        return redirect(url_for('main.index'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    # Decks already in lesson
    decks_in_lesson = get_decks_by_lesson(lesson_id)

    # Available decks (common, same level, not yet in a lesson)
    all_decks = get_decks_by_niveau(lesson['niveau'], user_id, include_in_lessons=True)
    available_decks = [d for d in all_decks if d['is_commun'] and d['lesson_id'] is None]

    user = get_user_by_id(user_id)

    return render_template('manage_lesson_decks.html',
                         lesson=lesson,
                         decks_in_lesson=decks_in_lesson,
                         available_decks=available_decks,
                         user=user)


@lessons_bp.route('/associate-deck-to-lesson', methods=['POST'])
def associate_deck_route():
    """Associate a deck with a lesson"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    deck_id = request.form.get('deck_id')
    lesson_id = request.form.get('lesson_id')

    try:
        associate_deck_to_lesson(int(deck_id), int(lesson_id))
        return redirect(url_for('lessons.manage_lesson_decks', lesson_id=lesson_id))
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('lessons.manage_lesson_decks', lesson_id=lesson_id))


@lessons_bp.route('/detach-deck-from-lesson/<int:deck_id>', methods=['POST'])
def detach_deck_route(deck_id):
    """Detach a deck from its lesson"""
    if not session.get('is_admin'):
        flash('Unauthorized')
        return redirect(url_for('main.index'))

    try:
        deck = get_deck_by_id(deck_id)
        lesson_id = deck['lesson_id'] if deck else None

        detach_deck_from_lesson(deck_id)

        if lesson_id:
            return redirect(url_for('lessons.manage_lesson_decks', lesson_id=lesson_id))
        else:
            return redirect(url_for('main.index'))
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))
