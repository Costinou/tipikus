from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from database import (
    init_db, get_langues, get_decks_by_langue, 
    create_deck, add_mots_to_deck, get_mots_by_deck
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