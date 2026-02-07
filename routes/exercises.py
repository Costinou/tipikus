"""
Tipikus Routes - Exercises Blueprint
=====================================
Exercise management routes (CRUD, fill_blank)
"""

import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import (
    get_user_by_id,
    get_lesson_by_id,
    get_exercice_by_id,
    get_exercices_by_lesson,
    create_exercice,
    delete_exercice,
    add_exercice_contenu,
    get_exercice_contenu,
    create_exercice_resultat,
    get_exercice_stats
)

exercises_bp = Blueprint('exercises', __name__)


@exercises_bp.route('/create-exercice/<int:lesson_id>', methods=['GET'])
def create_exercice_form(lesson_id):
    """Exercise creation form (admin only)"""
    user_id = session.get('user_id')

    if not user_id or not session.get('is_admin'):
        flash('Only administrators can create exercises')
        return redirect(url_for('main.index'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    user = get_user_by_id(user_id)
    return render_template('create_exercice.html', lesson=lesson, user=user)


@exercises_bp.route('/create-exercice/<int:lesson_id>', methods=['POST'])
def create_exercice_post(lesson_id):
    """Process creating a fill_blank exercise"""
    if not session.get('is_admin'):
        flash('Only administrators can create exercises')
        return redirect(url_for('main.index'))

    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('main.index'))

    titre = request.form.get('titre', '').strip()
    description = request.form.get('description', '').strip()
    fichier_json = request.files.get('fichier_json')

    if not titre:
        flash('Title is required')
        return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))

    if not fichier_json or not fichier_json.filename.endswith('.json'):
        flash('Please select a .json file')
        return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))

    try:
        contenu_json = json.loads(fichier_json.read().decode('utf-8'))

        # Validate structure
        if not isinstance(contenu_json, list):
            flash('JSON file must contain a list of sentences')
            return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))

        for item in contenu_json:
            if not all(k in item for k in ['phrase', 'reponses_valides']):
                flash('Each sentence must have "phrase" and "reponses_valides"')
                return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))

        # Get order (number of existing exercises + 1)
        exercices_existants = get_exercices_by_lesson(lesson_id)
        ordre = len(exercices_existants)

        # Create exercise
        config = {
            'show_hints': True,
            'case_sensitive': False
        }

        exercice_id = create_exercice(
            lesson_id=lesson_id,
            type_exercice='fill_blank',
            titre=titre,
            description=description,
            ordre=ordre,
            config=config
        )

        # Add content
        add_exercice_contenu(exercice_id, contenu_json)

        flash(f'Exercise "{titre}" created with {len(contenu_json)} sentence(s)!')
        return redirect(url_for('lessons.view_lesson', lesson_id=lesson_id))

    except json.JSONDecodeError:
        flash('Error: Invalid JSON file')
        return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))
    except Exception as e:
        flash(f'Error during creation: {str(e)}')
        return redirect(url_for('exercises.create_exercice_form', lesson_id=lesson_id))


@exercises_bp.route('/exercice/<int:exercice_id>')
def exercice_fill_blank(exercice_id):
    """Fill_blank exercise page"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    exercice = get_exercice_by_id(exercice_id)
    if not exercice:
        flash('Exercise not found')
        return redirect(url_for('main.index'))

    if exercice['type_exercice'] != 'fill_blank':
        flash('Unsupported exercise type')
        return redirect(url_for('main.index'))

    # Get content
    contenu = get_exercice_contenu(exercice_id)

    # Get lesson
    lesson = get_lesson_by_id(exercice['lesson_id'])

    # Get stats
    stats = get_exercice_stats(exercice_id, user_id)

    user = get_user_by_id(user_id)

    return render_template('exercice_fill_blank.html',
                         exercice=exercice,
                         contenu=contenu,
                         lesson=lesson,
                         stats=stats,
                         user=user)


@exercises_bp.route('/api/exercice/submit', methods=['POST'])
def submit_exercice():
    """API to submit exercise result"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()

        exercice_id = data.get('exercice_id')
        score = data.get('score', 0)
        total_questions = data.get('total_questions', 0)
        temps_secondes = data.get('temps_secondes', 0)
        complete = data.get('complete', False)

        if not exercice_id:
            return jsonify({'error': 'Missing parameters'}), 400

        resultat_id = create_exercice_resultat(
            exercice_id, user_id, score, total_questions, temps_secondes, complete
        )

        return jsonify({'success': True, 'resultat_id': resultat_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@exercises_bp.route('/delete-exercice/<int:exercice_id>', methods=['POST'])
def delete_exercice_route(exercice_id):
    """Delete an exercise (admin only)"""
    if not session.get('is_admin'):
        flash('Only administrators can delete exercises')
        return redirect(url_for('main.index'))

    try:
        exercice = get_exercice_by_id(exercice_id)
        if not exercice:
            flash('Exercise not found')
            return redirect(url_for('main.index'))

        lesson_id = exercice['lesson_id']
        titre = exercice['titre']

        delete_exercice(exercice_id)

        flash(f'Exercise "{titre}" deleted successfully')
        return redirect(url_for('lessons.view_lesson', lesson_id=lesson_id))

    except Exception as e:
        flash(f'Error during deletion: {str(e)}')
        return redirect(url_for('main.index'))
