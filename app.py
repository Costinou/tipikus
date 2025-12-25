from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import json
import os
from io import BytesIO
from database import (
    init_db, get_langues, get_decks_by_langue, get_deck_by_id,
    create_deck, add_mots_to_deck, get_mots_by_deck, 
    get_mots_by_deck_ordered, delete_deck
)

app = Flask(__name__)
app.secret_key = 'tipikus_secret_key_2024'  # Pour les messages flash

# Langues supportées (constante)
LANGUES_SUPPORTEES = ['Magyarul', 'Polonais', 'Espagnol']

@app.route('/')
def index():
    """Page d'accueil - Sélection de la langue"""
    # Récupérer les langues qui ont déjà des decks
    langues_existantes = get_langues()
    return render_template('index.html', 
                         langues_supportees=LANGUES_SUPPORTEES,
                         langues_existantes=langues_existantes)

@app.route('/langue/<langue>')
def langue(langue):
    """Page d'une langue - Liste des decks existants"""
    if langue not in LANGUES_SUPPORTEES:
        flash(f'Langue "{langue}" non supportée')
        return redirect(url_for('index'))
    
    decks = get_decks_by_langue(langue)
    return render_template('langue.html', langue=langue, decks=decks)

@app.route('/nouveau-deck')
@app.route('/nouveau-deck/<langue>')
def nouveau_deck(langue=None):
    """Afficher le formulaire de création de deck"""
    return render_template('nouveau_deck.html', 
                         langues=LANGUES_SUPPORTEES, 
                         langue_preselect=langue)

@app.route('/creer-deck', methods=['POST'])
def creer_deck():
    """Traiter la création d'un nouveau deck"""
    langue = request.form.get('langue', '').strip()
    nom_deck = request.form.get('nom_deck', '').strip()
    fichier_json = request.files.get('fichier_json')
    
    if langue not in LANGUES_SUPPORTEES:
        flash('Veuillez sélectionner une langue valide')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES)
    
    if not nom_deck:
        flash('Le nom du deck est obligatoire')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    
    if not fichier_json or fichier_json.filename == '':
        flash('Veuillez sélectionner un fichier JSON')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    
    try:
        # Lire et parser le JSON
        contenu = fichier_json.read().decode('utf-8')
        mots_dict = json.loads(contenu)
        
        if not isinstance(mots_dict, dict):
            flash('Le fichier JSON doit être un objet (dictionnaire)')
            return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
        
        if not mots_dict:
            flash('Le fichier JSON est vide')
            return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
        
        # Créer le deck et ajouter les mots
        deck_id = create_deck(nom_deck, langue)
        add_mots_to_deck(deck_id, mots_dict)
        
        flash(f'Deck "{nom_deck}" créé avec {len(mots_dict)} mots!')
        return redirect(url_for('langue', langue=langue))
        
    except json.JSONDecodeError:
        flash('Erreur: Fichier JSON invalide')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    except Exception as e:
        flash(f'Erreur lors de la création du deck: {str(e)}')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)

@app.route('/supprimer-deck/<int:deck_id>', methods=['POST'])
def supprimer_deck(deck_id):
    """Supprimer un deck"""
    try:
        # Récupérer les infos du deck avant suppression
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        langue = deck['langue']
        nom_deck = deck['nom']
        
        # Supprimer le deck
        delete_deck(deck_id)
        
        flash(f'Deck "{nom_deck}" supprimé avec succès')
        return redirect(url_for('langue', langue=langue))
        
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}')
        return redirect(url_for('index'))

@app.route('/exporter-deck/<int:deck_id>')
def exporter_deck(deck_id):
    """Exporter un deck au format JSON"""
    try:
        # Récupérer les infos du deck
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        # Récupérer les mots (triés alphabétiquement)
        mots_dict = get_mots_by_deck_ordered(deck_id)
        
        if not mots_dict:
            flash('Ce deck ne contient aucun mot')
            return redirect(url_for('langue', langue=deck['langue']))
        
        # Créer le JSON
        json_content = json.dumps(mots_dict, ensure_ascii=False, indent=2)
        
        # Créer un fichier en mémoire
        buffer = BytesIO()
        buffer.write(json_content.encode('utf-8'))
        buffer.seek(0)
        
        # Nom du fichier à télécharger
        filename = f"{deck['nom'].replace(' ', '_')}.json"
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erreur lors de l\'export: {str(e)}')
        return redirect(url_for('index'))

@app.route('/apprendre/<int:deck_id>')
def apprendre(deck_id):
    """Page d'apprentissage pour un deck"""
    mots = get_mots_by_deck(deck_id)
    
    if not mots:
        flash('Ce deck ne contient aucun mot')
        return redirect(url_for('index'))
    
    return render_template('apprendre.html', mots=mots, deck_id=deck_id)

@app.route('/api/mots/<int:deck_id>')
def api_mots(deck_id):
    """API pour récupérer les mots d'un deck (pour l'AJAX)"""
    mots = get_mots_by_deck(deck_id)
    return jsonify([{
        'id': mot['id'],
        'mot_francais': mot['mot_francais'],
        'traduction': mot['traduction']
    } for mot in mots])

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialiser la base de données au démarrage
    init_db()
    
    # Lancer l'application
    app.run(
        host='0.0.0.0',  # Accessible depuis le réseau local
        port=5000,
        debug=True
    )