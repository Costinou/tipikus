from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
import json
import os
import io
import csv
from io import BytesIO
from functools import wraps
from database import (
    init_db, get_niveaux_with_counts, get_decks_by_niveau, get_deck_by_id,
    create_deck, add_mots_to_deck, get_mots_by_deck, 
    get_mots_by_deck_ordered, delete_deck, can_delete_deck,
    create_session, get_stats_deck, get_stats_niveau, get_stats_globales, calculer_streak,
    get_all_users, get_user_by_id, get_user_by_name, create_user, delete_user,
    verify_user_password, update_user_password,
    get_lessons_by_niveau, get_lesson_by_id, create_lesson, update_lesson, delete_lesson,
    get_decks_by_lesson, associate_deck_to_lesson, detach_deck_from_lesson,
    calculate_lesson_progress, calculate_niveau_progress,
    NIVEAUX_DISPONIBLES
)

# Import pour la synthèse vocale
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("Warning: gTTS n'est pas installé.")

app = Flask(__name__)
app.secret_key = 'tipikus_secret_key_2024'

# Configuration des sessions
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 an
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ========== ROUTES AUTHENTIFICATION ==========

@app.route('/login', methods=['GET'])
def login():
    """Page de connexion"""
    # Si déjà connecté, rediriger vers l'accueil
    if session.get('user_id'):
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """Traiter la connexion"""
    nom = request.form.get('nom', '').strip()
    password = request.form.get('password', '').strip()
    
    if not nom or not password:
        flash('Nom et mot de passe requis')
        return redirect(url_for('login'))
    
    # Vérifier les identifiants
    user = verify_user_password(nom, password)
    
    if not user:
        flash('Nom d\'utilisateur ou mot de passe incorrect')
        return redirect(url_for('login'))
    
    # Connexion réussie
    session.clear()
    session.permanent = True
    session['user_id'] = user['id']
    session['user_name'] = user['nom']
    session.modified = True
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET'])
def change_password():
    """Page de changement de mot de passe"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = get_user_by_id(user_id)
    return render_template('change_password.html', user=user)

@app.route('/change-password', methods=['POST'])
def change_password_post():
    """Traiter le changement de mot de passe"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id:
        return redirect(url_for('login'))
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Vérifications
    if not current_password or not new_password or not confirm_password:
        flash('Tous les champs sont requis')
        return redirect(url_for('change_password'))
    
    # Vérifier le mot de passe actuel
    user = verify_user_password(user_name, current_password)
    if not user:
        flash('Mot de passe actuel incorrect')
        return redirect(url_for('change_password'))
    
    # Vérifier que les nouveaux mots de passe correspondent
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas')
        return redirect(url_for('change_password'))
    
    # Vérifier la longueur
    if len(new_password) < 4:
        flash('Le mot de passe doit contenir au moins 4 caractères')
        return redirect(url_for('change_password'))
    
    # Mettre à jour le mot de passe
    update_user_password(user_id, new_password)
    
    flash('Mot de passe changé avec succès!')
    return redirect(url_for('index'))

# ========== ROUTES ADMIN (Gestion utilisateurs) ==========

@app.route('/admin/users')
def admin_users():
    """Page de gestion des utilisateurs (admin uniquement)"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id or user_name != 'c':
        flash('Accès refusé')
        return redirect(url_for('index'))
    
    users = get_all_users()
    user = get_user_by_id(user_id)
    
    return render_template('admin_users.html', users=users, user=user)

@app.route('/admin/create-user', methods=['POST'])
def admin_create_user():
    """Créer un utilisateur (admin uniquement)"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Accès refusé')
        return redirect(url_for('index'))
    
    nom = request.form.get('nom', '').strip()
    password = request.form.get('password', '').strip()
    
    if not nom or not password:
        flash('Nom et mot de passe requis')
        return redirect(url_for('admin_users'))
    
    if len(nom) > 50:
        flash('Le nom est trop long (max 50 caractères)')
        return redirect(url_for('admin_users'))
    
    if len(password) < 4:
        flash('Le mot de passe doit contenir au moins 4 caractères')
        return redirect(url_for('admin_users'))
    
    user_id = create_user(nom, password)
    
    if user_id is None:
        flash('Ce nom existe déjà')
        return redirect(url_for('admin_users'))
    
    flash(f'Utilisateur "{nom}" créé avec succès')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """Supprimer un utilisateur (admin uniquement)"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Accès refusé')
        return redirect(url_for('index'))
    
    # Empêcher de supprimer l'admin
    user_to_delete = get_user_by_id(user_id)
    if user_to_delete and user_to_delete['nom'] == 'c':
        flash('Impossible de supprimer l\'administrateur')
        return redirect(url_for('admin_users'))
    
    try:
        if user_to_delete:
            nom_user = user_to_delete['nom']
            delete_user(user_id)
            flash(f'Utilisateur "{nom_user}" supprimé avec succès')
        else:
            flash('Utilisateur non trouvé')
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
def admin_reset_password(user_id):
    """Réinitialiser le mot de passe d'un utilisateur (admin uniquement)"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Accès refusé')
        return redirect(url_for('index'))
    
    new_password = request.form.get('new_password', '').strip()
    
    if not new_password:
        flash('Mot de passe requis')
        return redirect(url_for('admin_users'))
    
    if len(new_password) < 4:
        flash('Le mot de passe doit contenir au moins 4 caractères')
        return redirect(url_for('admin_users'))
    
    user_to_reset = get_user_by_id(user_id)
    if not user_to_reset:
        flash('Utilisateur non trouvé')
        return redirect(url_for('admin_users'))
    
    try:
        update_user_password(user_id, new_password)
        flash(f'Mot de passe de "{user_to_reset["nom"]}" réinitialisé avec succès')
    except Exception as e:
        flash(f'Erreur lors de la réinitialisation: {str(e)}')
    
    return redirect(url_for('admin_users'))

# ========== ROUTES UTILISATEURS (anciennes, simplifiées) ==========

@app.route('/api/select-user', methods=['POST'])
def api_select_user():
    """Rediriger vers login (ancienne route, pour compatibilité)"""
    return redirect(url_for('login'))

@app.route('/select-user')
def select_user():
    """Rediriger vers login"""
    return redirect(url_for('login'))

@app.route('/create-user', methods=['POST'])
def create_user_post():
    """Rediriger vers login"""
    return redirect(url_for('login'))

@app.route('/change-user')
def change_user():
    """Déconnexion"""
    return redirect(url_for('logout'))

@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    """Rediriger vers admin"""
    return redirect(url_for('admin_users'))

# ========== ROUTES PRINCIPALES ==========

@app.route('/')
def index():
    """Page d'accueil - Sélection du niveau"""
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('login'))
    
    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Récupérer les niveaux avec compteur de decks
    niveaux_counts = get_niveaux_with_counts(user_id)
    
    # Calculer la progression pour chaque niveau
    niveaux_progress = {}
    for niveau in NIVEAUX_DISPONIBLES:
        niveaux_progress[niveau] = calculate_niveau_progress(user_id, niveau)
    
    return render_template('index.html', 
                         niveaux_disponibles=NIVEAUX_DISPONIBLES,
                         niveaux_counts=niveaux_counts,
                         niveaux_progress=niveaux_progress,
                         user=user)

@app.route('/niveau/<niveau>')
def niveau(niveau):
    """Page d'un niveau - Liste des lessons et decks"""
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    if niveau not in NIVEAUX_DISPONIBLES:
        flash(f'Niveau "{niveau}" non supporté')
        return redirect(url_for('index'))
    
    # Récupérer les lessons du niveau
    lessons = get_lessons_by_niveau(niveau)
    
    # Calculer la progression pour chaque lesson
    lessons_progress = {}
    for lesson in lessons:
        lessons_progress[lesson['id']] = calculate_lesson_progress(user_id, lesson['id'])
    
    # Récupérer les decks HORS lessons (communs + perso)
    all_decks = get_decks_by_niveau(niveau, user_id, include_in_lessons=False)
    
    # Séparer decks communs et perso
    decks_communs = [d for d in all_decks if d['is_commun']]
    decks_perso = [d for d in all_decks if not d['is_commun']]
    
    user = get_user_by_id(user_id)
    
    return render_template('niveau.html', 
                         niveau=niveau,
                         lessons=lessons,
                         lessons_progress=lessons_progress,
                         decks_communs=decks_communs,
                         decks_perso=decks_perso,
                         user=user)

# ========== ROUTES POUR LES LESSONS ==========

@app.route('/lesson/<int:lesson_id>')
def view_lesson(lesson_id):
    """Afficher une lesson avec son contenu markdown et ses decks"""
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson non trouvée')
        return redirect(url_for('index'))
    
    # Récupérer les decks de cette lesson
    decks = get_decks_by_lesson(lesson_id)
    
    user = get_user_by_id(user_id)
    
    return render_template('lesson.html', lesson=lesson, decks=decks, user=user)

@app.route('/create-lesson', methods=['GET'])
def create_lesson_form():
    """Formulaire de création de lesson (admin uniquement)"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    # Vérifier que c'est l'admin
    if user_name != 'c':
        flash('Seul l\'utilisateur "c" peut créer des lessons')
        return redirect(url_for('index'))
    
    user = get_user_by_id(user_id)
    return render_template('create_lesson.html', niveaux=NIVEAUX_DISPONIBLES, user=user)

@app.route('/create-lesson', methods=['POST'])
def create_lesson_post():
    """Traiter la création d'une lesson"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id or user_name != 'c':
        flash('Seul l\'utilisateur "c" peut créer des lessons')
        return redirect(url_for('index'))
    
    niveau = request.form.get('niveau', '').strip()
    numero = request.form.get('numero', '').strip()
    titre = request.form.get('titre', '').strip()
    fichier_md = request.files.get('fichier_md')
    
    # Validations
    if niveau not in NIVEAUX_DISPONIBLES:
        flash('Niveau invalide')
        return redirect(url_for('create_lesson_form'))
    
    try:
        numero = int(numero)
        if numero < 1:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Le numéro doit être un entier positif')
        return redirect(url_for('create_lesson_form'))
    
    if not titre:
        flash('Le titre est obligatoire')
        return redirect(url_for('create_lesson_form'))
    
    if not fichier_md or not fichier_md.filename.endswith('.md'):
        flash('Veuillez sélectionner un fichier .md')
        return redirect(url_for('create_lesson_form'))
    
    try:
        # Lire le contenu du fichier markdown
        content_markdown = fichier_md.read().decode('utf-8')
        
        # Créer la lesson
        lesson_id = create_lesson(niveau, numero, titre, content_markdown)
        
        if lesson_id is None:
            flash(f'Une lesson {numero} existe déjà pour le niveau {niveau}')
            return redirect(url_for('create_lesson_form'))
        
        flash(f'Lesson "{titre}" créée avec succès!')
        return redirect(url_for('view_lesson', lesson_id=lesson_id))
        
    except Exception as e:
        flash(f'Erreur lors de la création: {str(e)}')
        return redirect(url_for('create_lesson_form'))

@app.route('/delete-lesson/<int:lesson_id>', methods=['POST'])
def delete_lesson_route(lesson_id):
    """Supprimer une lesson (admin uniquement)"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Seul l\'utilisateur "c" peut supprimer des lessons')
        return redirect(url_for('index'))
    
    try:
        lesson = get_lesson_by_id(lesson_id)
        if not lesson:
            flash('Lesson non trouvée')
            return redirect(url_for('index'))
        
        niveau = lesson['niveau']
        titre = lesson['titre']
        
        delete_lesson(lesson_id)
        
        flash(f'Lesson "{titre}" supprimée avec succès')
        return redirect(url_for('niveau', niveau=niveau))
        
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}')
        return redirect(url_for('index'))

@app.route('/edit-lesson/<int:lesson_id>', methods=['GET'])
def edit_lesson_form(lesson_id):
    """Formulaire de modification d'une lesson (admin uniquement)"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id or user_name != 'c':
        flash('Seul l\'utilisateur "c" peut modifier des lessons')
        return redirect(url_for('index'))
    
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson non trouvée')
        return redirect(url_for('index'))
    
    user = get_user_by_id(user_id)
    return render_template('edit_lesson.html', lesson=lesson, user=user)

@app.route('/edit-lesson/<int:lesson_id>', methods=['POST'])
def edit_lesson_post(lesson_id):
    """Traiter la modification d'une lesson"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Seul l\'utilisateur "c" peut modifier des lessons')
        return redirect(url_for('index'))
    
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson non trouvée')
        return redirect(url_for('index'))
    
    titre = request.form.get('titre', '').strip()
    fichier_md = request.files.get('fichier_md')
    
    # Validations
    if not titre:
        flash('Le titre est obligatoire')
        return redirect(url_for('edit_lesson_form', lesson_id=lesson_id))
    
    try:
        # Si un nouveau fichier est uploadé, le lire
        if fichier_md and fichier_md.filename and fichier_md.filename.endswith('.md'):
            content_markdown = fichier_md.read().decode('utf-8')
        else:
            # Sinon, garder l'ancien contenu
            content_markdown = lesson['content_markdown']
        
        # Mettre à jour la lesson
        update_lesson(lesson_id, titre, content_markdown)
        
        flash(f'Lesson "{titre}" modifiée avec succès!')
        return redirect(url_for('view_lesson', lesson_id=lesson_id))
        
    except Exception as e:
        flash(f'Erreur lors de la modification: {str(e)}')
        return redirect(url_for('edit_lesson_form', lesson_id=lesson_id))

@app.route('/manage-lesson-decks/<int:lesson_id>')
def manage_lesson_decks(lesson_id):
    """Interface pour gérer les decks d'une lesson (admin uniquement)"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id or user_name != 'c':
        flash('Seul l\'utilisateur "c" peut gérer les lessons')
        return redirect(url_for('index'))
    
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        flash('Lesson non trouvée')
        return redirect(url_for('index'))
    
    # Decks déjà dans la lesson
    decks_in_lesson = get_decks_by_lesson(lesson_id)
    
    # Decks disponibles (communs, même niveau, pas encore dans une lesson)
    all_decks = get_decks_by_niveau(lesson['niveau'], user_id, include_in_lessons=True)
    available_decks = [d for d in all_decks if d['is_commun'] and d['lesson_id'] is None]
    
    user = get_user_by_id(user_id)
    
    return render_template('manage_lesson_decks.html', 
                         lesson=lesson, 
                         decks_in_lesson=decks_in_lesson,
                         available_decks=available_decks,
                         user=user)

@app.route('/associate-deck-to-lesson', methods=['POST'])
def associate_deck_route():
    """Associer un deck à une lesson"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        return jsonify({'error': 'Non autorisé'}), 403
    
    deck_id = request.form.get('deck_id')
    lesson_id = request.form.get('lesson_id')
    
    try:
        associate_deck_to_lesson(int(deck_id), int(lesson_id))
        return redirect(url_for('manage_lesson_decks', lesson_id=lesson_id))
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('manage_lesson_decks', lesson_id=lesson_id))

@app.route('/detach-deck-from-lesson/<int:deck_id>', methods=['POST'])
def detach_deck_route(deck_id):
    """Détacher un deck de sa lesson"""
    user_name = session.get('user_name')
    
    if user_name != 'c':
        flash('Non autorisé')
        return redirect(url_for('index'))
    
    try:
        deck = get_deck_by_id(deck_id)
        lesson_id = deck['lesson_id'] if deck else None
        
        detach_deck_from_lesson(deck_id)
        
        if lesson_id:
            return redirect(url_for('manage_lesson_decks', lesson_id=lesson_id))
        else:
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

# ========== ROUTES PRINCIPALES ==========

@app.route('/nouveau-deck')
@app.route('/nouveau-deck/<niveau>')
def nouveau_deck(niveau=None):
    """Afficher le formulaire de création de deck"""
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    user = get_user_by_id(user_id)
    
    return render_template('nouveau_deck.html', 
                         niveaux=NIVEAUX_DISPONIBLES, 
                         niveau_preselect=niveau,
                         user=user)

@app.route('/creer-deck', methods=['POST'])
def creer_deck():
    """Traiter la création d'un nouveau deck"""
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    niveau = request.form.get('niveau', '').strip()
    nom_deck = request.form.get('nom_deck', '').strip()
    is_commun = request.form.get('is_commun') == 'on'
    fichier = request.files.get('fichier')
    
    if niveau not in NIVEAUX_DISPONIBLES:
        flash('Veuillez sélectionner un niveau valide')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES)
    
    if not nom_deck:
        flash('Le nom du deck est obligatoire')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
    
    if not fichier or fichier.filename == '':
        flash('Veuillez sélectionner un fichier')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
    
    # Déterminer le type de fichier
    filename = fichier.filename.lower()
    is_json = filename.endswith('.json')
    is_csv = filename.endswith('.csv')
    
    if not (is_json or is_csv):
        flash('Format de fichier non supporté. Utilisez .json ou .csv')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
    
    try:
        contenu = fichier.read().decode('utf-8-sig')
        mots_dict = {}
        
        if is_json:
            mots_dict = json.loads(contenu)
            if not isinstance(mots_dict, dict):
                flash('Le fichier JSON doit être un objet (dictionnaire)')
                return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
        
        elif is_csv:
            lignes = contenu.strip().split('\n')
            
            if len(lignes) < 2:
                flash('Le fichier CSV doit contenir au moins 2 lignes')
                return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
            
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
            flash('Le fichier est vide ou ne contient pas de mots valides')
            return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
        
        # Créer le deck
        deck_id = create_deck(nom_deck, niveau, user_id, is_commun)
        add_mots_to_deck(deck_id, mots_dict)
        
        type_deck = "commun" if is_commun else "personnel"
        flash(f'Deck {type_deck} "{nom_deck}" créé avec {len(mots_dict)} mots!')
        return redirect(url_for('niveau', niveau=niveau))
        
    except json.JSONDecodeError:
        flash('Erreur: Fichier JSON invalide')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)
    except Exception as e:
        flash(f'Erreur lors de la création du deck: {str(e)}')
        return render_template('nouveau_deck.html', niveaux=NIVEAUX_DISPONIBLES, niveau_preselect=niveau)

@app.route('/supprimer-deck/<int:deck_id>', methods=['POST'])
def supprimer_deck(deck_id):
    """Supprimer un deck"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_id:
        return redirect(url_for('select_user'))
    
    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        # Vérifier les permissions
        if deck['is_commun']:
            # Deck commun : seul 'c' peut supprimer
            if user_name != 'c':
                flash('Seul l\'utilisateur "c" peut supprimer les decks communs')
                return redirect(url_for('niveau', niveau=deck['niveau']))
        else:
            # Deck perso : seul le propriétaire peut supprimer
            if deck['user_id'] != user_id:
                flash('Vous ne pouvez pas supprimer ce deck')
                return redirect(url_for('niveau', niveau=deck['niveau']))
        
        niveau = deck['niveau']
        nom_deck = deck['nom']
        
        delete_deck(deck_id)
        
        flash(f'Deck "{nom_deck}" supprimé avec succès')
        return redirect(url_for('niveau', niveau=niveau))
        
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}')
        return redirect(url_for('index'))

@app.route('/exporter-deck/<int:deck_id>')
def exporter_deck(deck_id):
    """Exporter un deck au format JSON ou CSV"""
    format_export = request.args.get('format', 'json').lower()
    
    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        mots_dict = get_mots_by_deck_ordered(deck_id)
        
        if not mots_dict:
            flash('Ce deck ne contient aucun mot')
            return redirect(url_for('niveau', niveau=deck['niveau']))
        
        base_filename = deck['nom'].replace(' ', '_')
        
        if format_export == 'csv':
            buffer = BytesIO()
            buffer.write('\ufeff'.encode('utf-8'))
            
            wrapper = io.TextIOWrapper(buffer, encoding='utf-8', newline='', write_through=True)
            writer = csv.writer(wrapper, delimiter=';')
            
            writer.writerow(['Français', 'Hongrois'])
            
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
        flash(f'Erreur lors de l\'export: {str(e)}')
        return redirect(url_for('index'))

@app.route('/voir-deck/<int:deck_id>')
def voir_deck(deck_id):
    """Afficher le contenu d'un deck"""
    try:
        deck = get_deck_by_id(deck_id)
        if not deck:
            flash('Deck non trouvé')
            return redirect(url_for('index'))
        
        mots = get_mots_by_deck(deck_id)
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
    """API pour récupérer les mots d'un deck"""
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
        tts = gTTS(text=texte, lang='hu', slow=False)
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
        
        streak = calculer_streak(stats.get('jours_utilises', []))
        stats['streak'] = streak
        
        total_quiz = stats.get('total_questions_quiz', 0) or 0
        if total_quiz > 0:
            stats['taux_reussite'] = round((stats['total_score'] / total_quiz) * 100, 1)
        else:
            stats['taux_reussite'] = None
        
        return render_template('stats_deck.html', deck=deck, stats=stats)
        
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.route('/stats/niveau/<niveau>')
def stats_niveau_route(niveau):
    """Afficher les statistiques d'un niveau"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('select_user'))
    
    try:
        if niveau not in NIVEAUX_DISPONIBLES:
            flash('Niveau non trouvé')
            return redirect(url_for('index'))
        
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
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    
    print("="*60)
    print("🚀 DÉMARRAGE DE L'APPLICATION TIPIKUS")
    print("="*60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )