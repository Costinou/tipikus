from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
import json
import os
import io
import csv
from io import BytesIO
from functools import wraps
from database import (
    init_db, get_langues, get_decks_by_langue, get_deck_by_id,
    create_deck, add_mots_to_deck, get_mots_by_deck, 
    get_mots_by_deck_ordered, delete_deck,
    create_session, get_stats_deck, get_stats_langue, get_stats_globales, calculer_streak,
    get_all_users, get_user_by_id, create_user, delete_user
)

# Import pour la synthèse vocale
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("Warning: gTTS n'est pas installé. La prononciation audio ne sera pas disponible.")
    print("Installez-le avec: pip install gtts")

app = Flask(__name__)
app.secret_key = 'tipikus_secret_key_2024'  # Pour les messages flash et sessions

# Configuration des sessions - sessions permanentes pour 1 an
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 an en secondes
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Langues supportées (constante)
LANGUES_SUPPORTEES = ['Magyarul', 'Polonais', 'Espagnol']

# Routes pour la sélection d'utilisateur

@app.route('/api/select-user', methods=['POST'])
def api_select_user():
    """API pour sélectionner un utilisateur"""
    user_id = request.form.get('user_id')
    user_name = request.form.get('user_name')
    
    print(f"[DEBUG] Sélection utilisateur - user_id: {user_id}, user_name: {user_name}")
    
    if not user_id:
        flash('Erreur: utilisateur non sélectionné')
        return redirect(url_for('select_user'))
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        flash('Erreur: ID utilisateur invalide')
        return redirect(url_for('select_user'))
    
    # Vérifier que l'utilisateur existe
    user = get_user_by_id(user_id)
    if not user:
        flash('Erreur: utilisateur introuvable')
        return redirect(url_for('select_user'))
    
    print(f"[DEBUG] Utilisateur trouvé: {user}")
    
    # Nettoyer la session d'abord
    session.clear()
    
    # Stocker dans la session Flask (permanente)
    session.permanent = True
    session['user_id'] = user_id
    session['user_name'] = user_name
    session.modified = True  # Forcer Flask à sauvegarder la session
    
    print(f"[DEBUG] Session après stockage: {dict(session)}")
    
    # Rediriger vers l'accueil
    return redirect(url_for('index'))

@app.route('/select-user')
def select_user():
    """Page de sélection d'utilisateur"""
    users = get_all_users()
    error = request.args.get('error')
    return render_template('select_user.html', users=users, error=error)

@app.route('/create-user', methods=['POST'])
def create_user_post():
    """Créer un nouvel utilisateur"""
    nom = request.form.get('nom', '').strip()
    
    if not nom:
        return redirect(url_for('select_user', error='Le nom est obligatoire'))
    
    if len(nom) > 50:
        return redirect(url_for('select_user', error='Le nom est trop long (max 50 caractères)'))
    
    user_id = create_user(nom)
    
    if user_id is None:
        return redirect(url_for('select_user', error='Ce nom existe déjà'))
    
    # Stocker dans la session (permanente)
    session.permanent = True
    session['user_id'] = user_id
    session['user_name'] = nom
    
    # Rediriger vers l'accueil
    return redirect(url_for('index'))

@app.route('/change-user')
def change_user():
    """Changer d'utilisateur"""
    session.clear()
    return redirect(url_for('select_user'))

@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    """Supprimer un utilisateur"""
    try:
        # Vérifier que l'utilisateur existe
        user = get_user_by_id(user_id)
        if not user:
            flash('Utilisateur non trouvé')
            return redirect(url_for('select_user'))
        
        nom_user = user['nom']
        
        # Supprimer l'utilisateur et toutes ses données
        delete_user(user_id)
        
        # Si c'était l'utilisateur connecté, nettoyer la session
        if session.get('user_id') == user_id:
            session.clear()
        
        flash(f'Utilisateur "{nom_user}" supprimé avec succès')
        return redirect(url_for('select_user'))
        
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}')
        return redirect(url_for('select_user'))

@app.route('/')
def index():
    """Page d'accueil - Sélection de la langue"""
    # Récupérer l'user_id depuis la session
    user_id = session.get('user_id')
    
    print(f"[DEBUG] Index - user_id dans session: {user_id}")
    print(f"[DEBUG] Index - session complète: {dict(session)}")
    
    if not user_id:
        print("[DEBUG] Pas d'utilisateur, redirection vers select_user")
        return redirect(url_for('select_user'))
    
    # Vérifier que l'utilisateur existe
    user = get_user_by_id(user_id)
    if not user:
        print("[DEBUG] Utilisateur introuvable, nettoyage session")
        session.clear()
        return redirect(url_for('select_user'))
    
    print(f"[DEBUG] Utilisateur trouvé: {user}")
    
    # Récupérer les langues qui ont déjà des decks
    langues_existantes = get_langues(user_id)
    return render_template('index.html', 
                         langues_supportees=LANGUES_SUPPORTEES,
                         langues_existantes=langues_existantes,
                         user=user)

@app.route('/langue/<langue>')
def langue(langue):
    """Page d'une langue - Liste des decks existants"""
    user_id = session.get('user_id')
    
    print(f"[DEBUG] Page langue - user_id: {user_id}, langue: {langue}")
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    if langue not in LANGUES_SUPPORTEES:
        flash(f'Langue "{langue}" non supportée')
        return redirect(url_for('index'))
    
    decks = get_decks_by_langue(langue, user_id)
    print(f"[DEBUG] Decks trouvés pour user {user_id}: {len(decks)}")
    
    user = get_user_by_id(user_id)
    return render_template('langue.html', langue=langue, decks=decks, user=user)

@app.route('/nouveau-deck')
@app.route('/nouveau-deck/<langue>')
def nouveau_deck(langue=None):
    """Afficher le formulaire de création de deck"""
    user_id = session.get('user_id')
    
    print(f"[DEBUG] Page nouveau-deck - user_id: {user_id}")
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    return render_template('nouveau_deck.html', 
                         langues=LANGUES_SUPPORTEES, 
                         langue_preselect=langue)

@app.route('/creer-deck', methods=['POST'])
def creer_deck():
    """Traiter la création d'un nouveau deck"""
    import sys
    
    print("="*60, flush=True)
    print("[DEBUG] !!!!! ENTRÉE DANS creer_deck !!!!!", flush=True)
    print("="*60, flush=True)
    sys.stdout.flush()
    
    user_id = session.get('user_id')
    
    print(f"[DEBUG] Création deck - user_id dans session: {user_id}", flush=True)
    print(f"[DEBUG] Création deck - session complète: {dict(session)}", flush=True)
    sys.stdout.flush()
    
    if not user_id:
        print("[DEBUG] Pas d'utilisateur, redirection", flush=True)
        return redirect(url_for('select_user'))
    
    langue = request.form.get('langue', '').strip()
    nom_deck = request.form.get('nom_deck', '').strip()
    fichier = request.files.get('fichier')
    
    print(f"[DEBUG] Langue: {langue}, Nom: {nom_deck}, User: {user_id}", flush=True)
    sys.stdout.flush()
    
    if langue not in LANGUES_SUPPORTEES:
        flash('Veuillez sélectionner une langue valide')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES)
    
    if not nom_deck:
        flash('Le nom du deck est obligatoire')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    
    if not fichier or fichier.filename == '':
        flash('Veuillez sélectionner un fichier')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    
    # Déterminer le type de fichier
    filename = fichier.filename.lower()
    is_json = filename.endswith('.json')
    is_csv = filename.endswith('.csv')
    
    if not (is_json or is_csv):
        flash('Format de fichier non supporté. Utilisez .json ou .csv')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    
    try:
        # Lire le contenu du fichier
        contenu = fichier.read().decode('utf-8-sig')  # utf-8-sig pour gérer le BOM
        
        mots_dict = {}
        
        if is_json:
            # Parser le JSON
            mots_dict = json.loads(contenu)
            
            if not isinstance(mots_dict, dict):
                flash('Le fichier JSON doit être un objet (dictionnaire)')
                return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
        
        elif is_csv:
            # Parser le CSV
            lignes = contenu.strip().split('\n')
            
            if len(lignes) < 2:
                flash('Le fichier CSV doit contenir au moins 2 lignes (en-tête + données)')
                return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
            
            # Détecter le séparateur (point-virgule ou virgule)
            premiere_ligne = lignes[0]
            separateur = ';' if ';' in premiere_ligne else ','
            
            # Parser les lignes
            reader = csv.reader(lignes, delimiter=separateur)
            lignes_parsed = list(reader)
            
            # Ignorer la première ligne si elle ressemble à un en-tête
            start_index = 0
            if lignes_parsed[0][0].lower() in ['francais', 'français', 'french', 'fr']:
                start_index = 1
            
            # Extraire les paires mot/traduction
            for ligne in lignes_parsed[start_index:]:
                if len(ligne) >= 2:
                    mot_fr = ligne[0].strip()
                    traduction = ligne[1].strip()
                    if mot_fr and traduction:
                        mots_dict[mot_fr] = traduction
        
        if not mots_dict:
            flash('Le fichier est vide ou ne contient pas de mots valides')
            return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
        
        # Créer le deck et ajouter les mots
        print(f"[DEBUG] Appel create_deck avec nom={nom_deck}, langue={langue}, user_id={user_id}", flush=True)
        sys.stdout.flush()
        deck_id = create_deck(nom_deck, langue, user_id)
        print(f"[DEBUG] Deck créé avec ID: {deck_id}", flush=True)
        sys.stdout.flush()
        add_mots_to_deck(deck_id, mots_dict)
        
        flash(f'Deck "{nom_deck}" créé avec {len(mots_dict)} mots!')
        return redirect(url_for('langue', langue=langue))
        
    except json.JSONDecodeError:
        flash('Erreur: Fichier JSON invalide')
        return render_template('nouveau_deck.html', langues=LANGUES_SUPPORTEES, langue_preselect=langue)
    except UnicodeDecodeError:
        flash('Erreur: Problème d\'encodage du fichier. Assurez-vous qu\'il est en UTF-8')
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
    """Exporter un deck au format JSON ou CSV"""
    format_export = request.args.get('format', 'json').lower()
    
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
        
        # Nom de base du fichier
        base_filename = deck['nom'].replace(' ', '_')
        
        if format_export == 'csv':
            # Créer le CSV
            buffer = BytesIO()
            # Écrire en UTF-8 avec BOM pour Excel
            buffer.write('\ufeff'.encode('utf-8'))
            
            # Créer le writer CSV
            wrapper = io.TextIOWrapper(buffer, encoding='utf-8', newline='', write_through=True)
            writer = csv.writer(wrapper, delimiter=';')
            
            # Écrire l'en-tête
            writer.writerow(['Français', deck['langue']])
            
            # Écrire les données
            for mot_fr, traduction in mots_dict.items():
                writer.writerow([mot_fr, traduction])
            
            # Détacher le wrapper pour récupérer le buffer
            wrapper.detach()
            buffer.seek(0)
            
            return send_file(
                buffer,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"{base_filename}.csv"
            )
        else:
            # Export JSON (par défaut)
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
        flash(f'Erreur lors de l\'export: {str(e)}')
        return redirect(url_for('index'))

@app.route('/voir-deck/<int:deck_id>')
def voir_deck(deck_id):
    """Afficher le contenu d'un deck sous forme de tableau"""
    try:
        # Récupérer les infos du deck
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        # Récupérer les mots (dans l'ordre alphabétique)
        mots = get_mots_by_deck(deck_id)
        # Trier par mot français
        mots_sorted = sorted(mots, key=lambda x: x['mot_francais'].lower())
        
        return render_template('voir_deck.html', deck=deck, mots=mots_sorted)
        
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.route('/apprendre/<int:deck_id>')
def apprendre(deck_id):
    """Page d'apprentissage pour un deck"""
    mots = get_mots_by_deck(deck_id)
    
    if not mots:
        flash('Ce deck ne contient aucun mot')
        return redirect(url_for('index'))
    
    return render_template('apprendre.html', mots=mots, deck_id=deck_id)

@app.route('/quiz/<int:deck_id>')
def quiz(deck_id):
    """Page de quiz QCM pour un deck"""
    mots = get_mots_by_deck(deck_id)
    
    if not mots:
        flash('Ce deck ne contient aucun mot')
        return redirect(url_for('index'))
    
    if len(mots) < 3:
        flash('Le deck doit contenir au moins 3 mots pour faire un quiz')
        return redirect(url_for('index'))
    
    return render_template('quiz.html', mots=mots, deck_id=deck_id)

@app.route('/api/mots/<int:deck_id>')
def api_mots(deck_id):
    """API pour récupérer les mots d'un deck (pour l'AJAX)"""
    mots = get_mots_by_deck(deck_id)
    return jsonify([{
        'id': mot['id'],
        'mot_francais': mot['mot_francais'],
        'traduction': mot['traduction']
    } for mot in mots])

@app.route('/api/tts')
def text_to_speech():
    """API pour générer l'audio TTS en hongrois"""
    if not GTTS_AVAILABLE:
        return jsonify({'error': 'gTTS non disponible'}), 503
    
    texte = request.args.get('text', '')
    if not texte:
        return jsonify({'error': 'Paramètre text manquant'}), 400
    
    try:
        # Générer l'audio en hongrois
        tts = gTTS(text=texte, lang='hu', slow=False)
        
        # Sauvegarder dans un buffer en mémoire
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return send_file(
            audio_buffer,
            mimetype='audio/mpeg',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session', methods=['POST'])
def enregistrer_session():
    """API pour enregistrer une session d'apprentissage"""
    try:
        data = request.get_json()
        
        deck_id = data.get('deck_id')
        type_session = data.get('type_session')
        nombre_mots_vus = data.get('nombre_mots_vus', 0)
        score = data.get('score', 0)
        duree_secondes = data.get('duree_secondes', 0)
        complete = data.get('complete', False)
        
        if not deck_id or not type_session:
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        session_id = create_session(
            deck_id, type_session, nombre_mots_vus, 
            score, duree_secondes, complete
        )
        
        return jsonify({'success': True, 'session_id': session_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats/deck/<int:deck_id>')
def stats_deck(deck_id):
    """Afficher les statistiques d'un deck"""
    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        stats = get_stats_deck(deck_id, days=30)
        
        # Calculer le streak
        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak
        
        # Calculer le taux de réussite au quiz
        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None
        
        return render_template('stats_deck.html', deck=deck, stats=stats)
        
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.route('/stats/langue/<langue>')
def stats_langue(langue):
    """Afficher les statistiques d'une langue"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('select_user'))
    
    try:
        if langue not in LANGUES_SUPPORTEES:
            flash('Langue non trouvée')
            return redirect(url_for('index'))
        
        stats = get_stats_langue(langue, user_id, days=30)
        decks = get_decks_by_langue(langue, user_id)
        
        # Calculer le streak
        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak
        
        # Calculer le taux de réussite au quiz
        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None
        
        user = get_user_by_id(user_id)
        
        return render_template('stats_langue.html', langue=langue, stats=stats, decks=decks, user=user)
        
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.route('/stats')
def stats_globales():
    """Afficher les statistiques globales"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('select_user'))
    
    try:
        stats = get_stats_globales(user_id, days=30)
        
        # Calculer le streak global
        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak
        
        # Calculer le taux de réussite global
        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None
        
        # Formater la durée totale
        total_duree = stats.get('total_duree', 0) or 0
        stats['total_heures'] = total_duree // 3600
        stats['total_minutes'] = (total_duree % 3600) // 60
        
        # Préparer les stats par langue
        stats_par_langue = stats.get('stats_par_langue', {})
        
        user = get_user_by_id(user_id)
        
        return render_template('stats_globales.html', 
                             stats_totales=stats, 
                             stats_par_langue=stats_par_langue,
                             user=user)
        
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialiser la base de données au démarrage
    init_db()
    
    print("="*60)
    print("🚀 DÉMARRAGE DE L'APPLICATION TIPIKUS")
    print("="*60)
    print(f"Mode debug: True")
    print(f"Host: 0.0.0.0")
    print(f"Port: 5000")
    print("="*60)
    
    # Lancer l'application
    app.run(
        host='0.0.0.0',  # Accessible depuis le réseau local
        port=5000,
        debug=True,
        use_reloader=True  # Force le rechargement automatique du code
    )