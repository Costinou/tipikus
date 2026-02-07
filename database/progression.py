"""
Tipikus Database - Progression Module
======================================
XP calculation, level progression, and unlocking functions
"""

from typing import Dict, List
from .core import get_db, AVAILABLE_LEVELS
from .users import get_user_by_id
from .lessons import get_decks_by_lesson


def calculate_niveau_total_xp(niveau):
    """
    Calcule l'XP total possible pour un niveau

    XP Total = Flashcards (10/mot) + Quiz (20/mot) + Exercices (25/question)
    """
    conn = get_db()

    total_xp = 0

    # 1. XP des decks (flashcards + quiz)
    decks = conn.execute(
        '''SELECT d.id, COUNT(m.id) as nb_mots
        FROM decks d
        LEFT JOIN mots m ON d.id = m.deck_id
        WHERE d.niveau = ?
        GROUP BY d.id''',
        (niveau,)
    ).fetchall()

    for deck in decks:
        nb_mots = deck['nb_mots'] or 0
        # Flashcards : 10 XP par mot
        total_xp += nb_mots * 10
        # Quiz : 20 XP par mot
        total_xp += nb_mots * 20

    # 2. XP des exercices
    exercices = conn.execute(
        '''SELECT e.id, COUNT(ec.id) as nb_questions
        FROM exercices e
        LEFT JOIN exercices_contenu ec ON e.id = ec.exercice_id
        JOIN lessons l ON e.lesson_id = l.id
        WHERE l.niveau = ?
        GROUP BY e.id''',
        (niveau,)
    ).fetchall()

    for exercice in exercices:
        nb_questions = exercice['nb_questions'] or 0
        # Exercices : 25 XP par question
        total_xp += nb_questions * 25

    conn.close()

    return total_xp


def calculate_user_xp_for_niveau(user_id, niveau):
    """
    Calcule l'XP gagné par un utilisateur pour un niveau

    Système de points:
    - Flashcards: 10 XP par carte vue
    - Quiz: 20 XP par bonne réponse, 5 XP par mauvaise
    - Exercices: 25 XP par bonne réponse, 8 XP par mauvaise (meilleur essai)

    Bonus:
    - Quiz ≥80%: +10 XP
    - Quiz 100%: +20 XP supplémentaire
    - Exercice ≥80%: +25 XP
    - Exercice 100%: +50 XP supplémentaire
    - Premier exercice complet par leçon: +100 XP
    """
    conn = get_db()

    xp_flashcards = 0
    xp_quiz = 0
    xp_exercices = 0
    bonus_quiz = 0
    bonus_exercices = 0

    # 1. XP FLASHCARDS
    flashcard_sessions = conn.execute(
        '''SELECT s.deck_id, MAX(s.nombre_mots_vus) as max_vus
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        AND d.niveau = ?
        AND s.type_session = 'flashcard'
        GROUP BY s.deck_id''',
        (user_id, niveau)
    ).fetchall()

    for session in flashcard_sessions:
        cartes_vues = session['max_vus'] or 0
        xp_flashcards += cartes_vues * 10

    # 2. XP QUIZ
    quiz_sessions = conn.execute(
        '''SELECT s.score, s.nombre_mots_vus
        FROM sessions s
        JOIN decks d ON s.deck_id = d.id
        WHERE s.user_id = ?
        AND d.niveau = ?
        AND s.type_session = 'quiz'
        AND s.nombre_mots_vus > 0''',
        (user_id, niveau)
    ).fetchall()

    for session in quiz_sessions:
        score = session['score'] or 0
        total_questions = session['nombre_mots_vus'] or 0

        if total_questions == 0:
            continue

        # Bonnes réponses : 20 XP
        xp_quiz += score * 20
        # Mauvaises réponses : 5 XP (tentative)
        xp_quiz += (total_questions - score) * 5

        # Bonus >= 80%
        if score / total_questions >= 0.8:
            bonus_quiz += 10

        # Bonus 100%
        if score == total_questions:
            bonus_quiz += 20

    # 3. XP EXERCICES
    exercice_results = conn.execute(
        '''SELECT er.exercice_id,
               MAX(er.score) as best_score,
               (SELECT ec.total_questions
                FROM exercices_resultats ec
                WHERE ec.exercice_id = er.exercice_id
                AND ec.user_id = er.user_id
                ORDER BY ec.score DESC
                LIMIT 1) as total_questions,
               MAX(CASE WHEN er.complete = 1 THEN 1 ELSE 0 END) as completed
        FROM exercices_resultats er
        JOIN exercices e ON er.exercice_id = e.id
        JOIN lessons l ON e.lesson_id = l.id
        WHERE er.user_id = ?
        AND l.niveau = ?
        GROUP BY er.exercice_id''',
        (user_id, niveau)
    ).fetchall()

    exercices_completed = set()

    for result in exercice_results:
        exercice_id = result['exercice_id']
        best_score = result['best_score'] or 0
        total_questions = result['total_questions'] or 0
        completed = result['completed']

        if total_questions == 0:
            continue

        # Bonnes réponses : 25 XP
        xp_exercices += best_score * 25
        # Mauvaises réponses : 8 XP (sur meilleur essai)
        xp_exercices += (total_questions - best_score) * 8

        # Bonus >= 80%
        if best_score / total_questions >= 0.8:
            bonus_exercices += 25

        # Bonus 100%
        if best_score == total_questions:
            bonus_exercices += 50

        # Marquer comme complété
        if completed:
            exercices_completed.add(exercice_id)

    # Bonus premier exercice complet par leçon
    if exercices_completed:
        lessons_completed = conn.execute(
            '''SELECT DISTINCT l.id
            FROM lessons l
            JOIN exercices e ON l.id = e.lesson_id
            WHERE l.niveau = ?
            AND e.id IN ({})'''.format(','.join('?' * len(exercices_completed))),
            (niveau, *exercices_completed)
        ).fetchall()

        # 100 XP par leçon avec au moins un exercice complet
        bonus_exercices += len(lessons_completed) * 100

    conn.close()

    xp_total = xp_flashcards + xp_quiz + xp_exercices + bonus_quiz + bonus_exercices

    return {
        'xp_flashcards': xp_flashcards,
        'xp_quiz': xp_quiz,
        'xp_exercices': xp_exercices,
        'bonus_quiz': bonus_quiz,
        'bonus_exercices': bonus_exercices,
        'xp_total': xp_total
    }


def calculate_niveau_progress_xp(user_id, niveau):
    """
    Calcule la progression d'un niveau basée sur l'XP (0-100%)
    """
    xp_total_possible = calculate_niveau_total_xp(niveau)

    if xp_total_possible == 0:
        return 100.0  # Niveau vide = 100%

    xp_data = calculate_user_xp_for_niveau(user_id, niveau)
    xp_gagne = xp_data['xp_total']

    progression = (xp_gagne / xp_total_possible) * 100
    return min(progression, 100.0)


def get_xp_breakdown(user_id, niveau):
    """
    Retourne un résumé détaillé de l'XP pour un niveau
    """
    conn = get_db()

    xp_total_possible = calculate_niveau_total_xp(niveau)
    xp_gagne = calculate_user_xp_for_niveau(user_id, niveau)

    # Calculer XP max par catégorie
    # Flashcards
    total_mots = conn.execute(
        '''SELECT COUNT(m.id) as total
        FROM mots m
        JOIN decks d ON m.deck_id = d.id
        WHERE d.niveau = ?''',
        (niveau,)
    ).fetchone()['total'] or 0

    xp_flashcards_max = total_mots * 10

    # Quiz
    xp_quiz_max = total_mots * 20

    # Exercices
    total_questions = conn.execute(
        '''SELECT COUNT(ec.id) as total
        FROM exercices_contenu ec
        JOIN exercices e ON ec.exercice_id = e.id
        JOIN lessons l ON e.lesson_id = l.id
        WHERE l.niveau = ?''',
        (niveau,)
    ).fetchone()['total'] or 0

    xp_exercices_max = total_questions * 25

    conn.close()

    # Calculer pourcentages
    progression = (xp_gagne['xp_total'] / xp_total_possible * 100) if xp_total_possible > 0 else 100.0

    flashcards_pct = (xp_gagne['xp_flashcards'] / xp_flashcards_max * 100) if xp_flashcards_max > 0 else 0
    quiz_pct = ((xp_gagne['xp_quiz'] + xp_gagne['bonus_quiz']) / (xp_quiz_max + 100) * 100) if xp_quiz_max > 0 else 0
    exercices_pct = ((xp_gagne['xp_exercices'] + xp_gagne['bonus_exercices']) / (xp_exercices_max + 500) * 100) if xp_exercices_max > 0 else 0

    return {
        'xp_total_possible': xp_total_possible,
        'xp_gagne': xp_gagne,
        'progression': min(progression, 100.0),
        'details': {
            'flashcards': {
                'actuel': xp_gagne['xp_flashcards'],
                'max': xp_flashcards_max,
                'pourcentage': min(flashcards_pct, 100.0)
            },
            'quiz': {
                'actuel': xp_gagne['xp_quiz'] + xp_gagne['bonus_quiz'],
                'max': xp_quiz_max,
                'pourcentage': min(quiz_pct, 100.0)
            },
            'exercices': {
                'actuel': xp_gagne['xp_exercices'] + xp_gagne['bonus_exercices'],
                'max': xp_exercices_max,
                'pourcentage': min(exercices_pct, 100.0)
            }
        }
    }


def get_unlocked_niveaux_xp(user_id):
    """
    Retourne les niveaux déverrouillés basés sur le système XP

    Un niveau est déverrouillé si :
    - C'est A1 (toujours déverrouillé - premier niveau)
    - C'est Custom (toujours déverrouillé - niveau libre)
    - OU le niveau précédent >= 80% (XP) - REQUIS pour accès
    - OU l'utilisateur est admin
    """
    # Vérifier si admin
    user = get_user_by_id(user_id)
    if user and user.get('is_admin') == True:
        return AVAILABLE_LEVELS.copy()

    unlocked = []

    for i, niveau in enumerate(AVAILABLE_LEVELS):
        # A1 : toujours déverrouillé (premier niveau)
        if niveau == 'A1':
            unlocked.append(niveau)
            continue

        # Custom : toujours déverrouillé (niveau libre)
        if niveau == 'Custom':
            unlocked.append(niveau)
            continue

        # Autres niveaux : vérifier progression du précédent
        prev_niveau = AVAILABLE_LEVELS[i - 1]

        # Skip if previous level is Custom
        if prev_niveau == 'Custom' and i >= 2:
            prev_niveau = AVAILABLE_LEVELS[i - 2]

        prev_progress = calculate_niveau_progress_xp(user_id, prev_niveau)

        # STRICT: >= 80% requis
        if prev_progress >= 80.0:
            unlocked.append(niveau)

    return unlocked


def has_user_seen_all_cards(user_id, deck_id):
    """Checks if a user has seen all cards in a deck at least once"""
    total_words = get_deck_total_words(deck_id)
    if total_words == 0:
        return True  # No words = considered "seen"

    conn = get_db()
    # Check if there's at least one complete flashcard session with all cards
    complete_sessions = conn.execute(
        '''SELECT COUNT(*) FROM sessions
        WHERE deck_id = ?
        AND type_session = 'flashcard'
        AND complete = 1
        AND nombre_mots_vus >= ?''',
        (deck_id, total_words)
    ).fetchone()[0]
    conn.close()

    return complete_sessions > 0


def get_deck_total_words(deck_id):
    """Returns the total number of words in a deck"""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM mots WHERE deck_id = ?', (deck_id,)).fetchone()[0]
    conn.close()
    return count


def calculate_lesson_progress(user_id, lesson_id):
    """Calculates lesson progress (0-100%)

    50% = All cards seen in all decks
    50% = Success rate >80% in all deck quizzes
    """
    decks = get_decks_by_lesson(lesson_id)

    if not decks:
        return 100.0  # Lesson without decks = 100%

    # 1. Check if all cards have been seen (50%)
    all_cards_seen = all(has_user_seen_all_cards(user_id, deck['id']) for deck in decks)
    cards_progress = 50.0 if all_cards_seen else 0.0

    # 2. Calculate average quiz success rate (50%)
    quiz_rates = [get_quiz_success_rate(user_id, deck['id']) for deck in decks]
    avg_quiz_rate = sum(quiz_rates) / len(quiz_rates) if quiz_rates else 0.0

    # If average rate is >80%, get 50%
    quiz_progress = 50.0 if avg_quiz_rate >= 80.0 else 0.0

    return cards_progress + quiz_progress


def get_quiz_success_rate(user_id, deck_id):
    """Returns the average quiz success rate for a deck (%)"""
    conn = get_db()
    stats = conn.execute(
        '''SELECT
            SUM(score) as total_score,
            SUM(nombre_mots_vus) as total_questions
        FROM sessions
        WHERE deck_id = ? AND user_id = ? AND type_session = 'quiz' ''',
        (deck_id, user_id)
    ).fetchone()
    conn.close()

    if not stats or not stats['total_questions'] or stats['total_questions'] == 0:
        return 0.0

    return (stats['total_score'] / stats['total_questions']) * 100
