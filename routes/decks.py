"""
Tipikus Routes - Decks Blueprint
=================================
Deck management routes (CRUD, export, flashcards, quiz)
"""

import json
import csv
import io
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from database import (
    get_user_by_id,
    get_deck_by_id,
    create_deck,
    delete_deck,
    add_mots_to_deck,
    get_mots_by_deck,
    get_mots_by_deck_ordered,
    AVAILABLE_LEVELS
)

decks_bp = Blueprint('decks', __name__)


@decks_bp.route('/nouveau-deck')
@decks_bp.route('/nouveau-deck/<niveau>')
def nouveau_deck(niveau=None):
    """Display deck creation form"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    user = get_user_by_id(user_id)

    return render_template('nouveau_deck.html',
                         niveaux=AVAILABLE_LEVELS,
                         niveau_preselect=niveau,
                         user=user)


@decks_bp.route('/creer-deck', methods=['POST'])
def creer_deck():
    """Process creating a new deck"""
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    niveau = request.form.get('niveau', '').strip()
    nom_deck = request.form.get('nom_deck', '').strip()
    is_commun = request.form.get('is_commun') == 'on'
    import_method = request.form.get('import_method', 'file')

    if niveau not in AVAILABLE_LEVELS:
        flash('Please select a valid level')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS)

    if not nom_deck:
        flash('Deck name is required')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

    # Handle manual word creation
    if import_method == 'manual':
        mots_dict = {}

        # Collect all word pairs from form
        for key in request.form:
            if key.startswith('word_french_'):
                index = key.replace('word_french_', '')
                french = request.form.get(f'word_french_{index}', '').strip()
                hungarian = request.form.get(f'word_hungarian_{index}', '').strip()

                if french and hungarian:
                    mots_dict[french] = hungarian

        if not mots_dict:
            flash('Please add at least one word pair')
            return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

        try:
            # Create deck
            deck_id = create_deck(nom_deck, niveau, user_id, is_commun)
            add_mots_to_deck(deck_id, mots_dict)

            type_deck = "common" if is_commun else "personal"
            flash(f'{type_deck.capitalize()} deck "{nom_deck}" created with {len(mots_dict)} words!')
            return redirect(url_for('main.niveau', niveau=niveau))
        except Exception as e:
            flash(f'Error creating deck: {str(e)}')
            return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

    # Handle file import (existing logic)
    fichier = request.files.get('fichier')

    if not fichier or fichier.filename == '':
        flash('Please select a file')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

    # Determine file type
    filename = fichier.filename.lower()
    is_json = filename.endswith('.json')
    is_csv = filename.endswith('.csv')

    if not (is_json or is_csv):
        flash('Unsupported file format. Use .json or .csv')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

    try:
        contenu = fichier.read().decode('utf-8-sig')
        mots_dict = {}

        if is_json:
            mots_dict = json.loads(contenu)
            if not isinstance(mots_dict, dict):
                flash('JSON file must be an object (dictionary)')
                return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

        elif is_csv:
            lignes = contenu.strip().split('\n')

            if len(lignes) < 2:
                flash('CSV file must contain at least 2 lines')
                return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

            premiere_ligne = lignes[0]
            separateur = ';' if ';' in premiere_ligne else ','

            reader = csv.reader(lignes, delimiter=separateur)
            lignes_parsed = list(reader)

            start_index = 0
            if lignes_parsed[0][0].lower() in ['francais', 'français', 'french', 'fr']:
                start_index = 1

            for ligne in lignes_parsed[start_index:]:
                if len(ligne) >= 2:
                    mot_fr = ligne[0].strip()
                    traduction = ligne[1].strip()
                    if mot_fr and traduction:
                        mots_dict[mot_fr] = traduction

        if not mots_dict:
            flash('File is empty or contains no valid words')
            return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)

        # Create deck
        deck_id = create_deck(nom_deck, niveau, user_id, is_commun)
        add_mots_to_deck(deck_id, mots_dict)

        type_deck = "common" if is_commun else "personal"
        flash(f'{type_deck.capitalize()} deck "{nom_deck}" created with {len(mots_dict)} words!')
        return redirect(url_for('main.niveau', niveau=niveau))

    except json.JSONDecodeError:
        flash('Error: Invalid JSON file')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)
    except Exception as e:
        flash(f'Error creating deck: {str(e)}')
        return render_template('nouveau_deck.html', niveaux=AVAILABLE_LEVELS, niveau_preselect=niveau)


@decks_bp.route('/supprimer-deck/<int:deck_id>', methods=['POST'])
def supprimer_deck(deck_id):
    """Delete a deck"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')

    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck not found')
            return redirect(url_for('main.index'))

        # Check permissions
        if deck['is_commun']:
            # Common deck: only admin can delete
            if not session.get('is_admin'):
                flash('Only administrators can delete common decks')
                return redirect(url_for('main.niveau', niveau=deck['niveau']))
        else:
            # Personal deck: only owner can delete
            if deck['user_id'] != user_id:
                flash('You cannot delete this deck')
                return redirect(url_for('main.niveau', niveau=deck['niveau']))

        niveau = deck['niveau']
        nom_deck = deck['nom']

        delete_deck(deck_id)

        flash(f'Deck "{nom_deck}" deleted successfully')
        return redirect(url_for('main.niveau', niveau=niveau))

    except Exception as e:
        flash(f'Error during deletion: {str(e)}')
        return redirect(url_for('main.index'))


@decks_bp.route('/exporter-deck/<int:deck_id>')
def exporter_deck(deck_id):
    """Export a deck in JSON or CSV format"""
    format_export = request.args.get('format', 'json').lower()

    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck not found')
            return redirect(url_for('main.index'))

        mots_dict = get_mots_by_deck_ordered(deck_id)

        if not mots_dict:
            flash('This deck contains no words')
            return redirect(url_for('main.niveau', niveau=deck['niveau']))

        base_filename = deck['nom'].replace(' ', '_')

        if format_export == 'csv':
            buffer = BytesIO()
            buffer.write('\ufeff'.encode('utf-8'))

            wrapper = io.TextIOWrapper(buffer, encoding='utf-8', newline='', write_through=True)
            writer = csv.writer(wrapper, delimiter=';')

            writer.writerow(['French', 'Hungarian'])

            for mot_fr, traduction in mots_dict.items():
                writer.writerow([mot_fr, traduction])

            wrapper.detach()
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"{base_filename}.csv"
            )
        else:
            json_content = json.dumps(mots_dict, ensure_ascii=False, indent=2)
            buffer = BytesIO()
            buffer.write(json_content.encode('utf-8'))
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype='application/json',
                as_attachment=True,
                download_name=f"{base_filename}.json"
            )

    except Exception as e:
        flash(f'Error during export: {str(e)}')
        return redirect(url_for('main.index'))


@decks_bp.route('/voir-deck/<int:deck_id>')
def voir_deck(deck_id):
    """Display deck content"""
    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck not found')
            return redirect(url_for('main.index'))

        mots = get_mots_by_deck(deck_id)
        mots_sorted = sorted(mots, key=lambda x: x['mot_francais'].lower())

        return render_template('voir_deck.html', deck=deck, mots=mots_sorted)

    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))


@decks_bp.route('/apprendre/<int:deck_id>')
def apprendre(deck_id):
    """Learning page for a deck"""
    mots = get_mots_by_deck(deck_id)

    if not mots:
        flash('This deck contains no words')
        return redirect(url_for('main.index'))

    # Track last studied deck for review suggestion
    session['last_studied_deck_id'] = deck_id
    session.modified = True

    return render_template('apprendre.html', mots=mots, deck_id=deck_id)


@decks_bp.route('/quiz/<int:deck_id>')
def quiz(deck_id):
    """Multiple choice quiz page for a deck"""
    mots = get_mots_by_deck(deck_id)

    if not mots:
        flash('This deck contains no words')
        return redirect(url_for('main.index'))

    if len(mots) < 3:
        flash('Deck must contain at least 3 words for a quiz')
        return redirect(url_for('main.index'))

    return render_template('quiz.html', mots=mots, deck_id=deck_id)
