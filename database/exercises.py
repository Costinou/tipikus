"""
Tipikus Database - Exercises Module
====================================
Exercise management and results tracking functions
"""

import json
from typing import Dict, List, Optional
from .core import get_db


def create_exercice(lesson_id, type_exercice, titre, description='', ordre=0, config=None):
    """Creates a new exercise"""
    conn = get_db()

    config_json = json.dumps(config) if config else None

    cursor = conn.execute(
        '''INSERT INTO exercices (lesson_id, type_exercice, titre, description, ordre, config)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (lesson_id, type_exercice, titre, description, ordre, config_json)
    )
    exercice_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return exercice_id


def get_exercices_by_lesson(lesson_id):
    """Returns all exercises for a lesson"""
    conn = get_db()
    exercices = conn.execute(
        'SELECT * FROM exercices WHERE lesson_id = ? ORDER BY ordre',
        (lesson_id,)
    ).fetchall()
    conn.close()

    result = []
    for ex in exercices:
        ex_dict = dict(ex)
        if ex_dict.get('config'):
            try:
                ex_dict['config'] = json.loads(ex_dict['config'])
            except:
                ex_dict['config'] = {}
        else:
            ex_dict['config'] = {}
        result.append(ex_dict)

    return result


def get_exercice_by_id(exercice_id):
    """Returns an exercise by ID"""
    conn = get_db()
    exercice = conn.execute(
        'SELECT * FROM exercices WHERE id = ?',
        (exercice_id,)
    ).fetchone()
    conn.close()

    if not exercice:
        return None

    ex_dict = dict(exercice)
    if ex_dict.get('config'):
        try:
            ex_dict['config'] = json.loads(ex_dict['config'])
        except:
            ex_dict['config'] = {}
    else:
        ex_dict['config'] = {}

    return ex_dict


def delete_exercice(exercice_id):
    """Deletes an exercise (CASCADE will handle content and results)"""
    conn = get_db()
    conn.execute('DELETE FROM exercices WHERE id = ?', (exercice_id,))
    conn.commit()
    conn.close()


def add_exercice_contenu(exercice_id, contenu_list):
    """Adds content to an exercise"""
    conn = get_db()

    for i, contenu in enumerate(contenu_list):
        contenu_json = json.dumps(contenu, ensure_ascii=False)
        conn.execute(
            'INSERT INTO exercices_contenu (exercice_id, contenu, ordre) VALUES (?, ?, ?)',
            (exercice_id, contenu_json, i)
        )

    conn.commit()
    conn.close()


def get_exercice_contenu(exercice_id):
    """Returns all content for an exercise"""
    conn = get_db()
    contenus = conn.execute(
        'SELECT * FROM exercices_contenu WHERE exercice_id = ? ORDER BY ordre',
        (exercice_id,)
    ).fetchall()
    conn.close()

    result = []
    for c in contenus:
        c_dict = dict(c)
        try:
            c_dict['contenu'] = json.loads(c_dict['contenu'])
        except:
            c_dict['contenu'] = {}
        result.append(c_dict)

    return result


def create_exercice_resultat(exercice_id, user_id, score, total_questions, temps_secondes, complete):
    """Records an exercise result"""
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO exercices_resultats
        (exercice_id, user_id, score, total_questions, temps_secondes, complete)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (exercice_id, user_id, score, total_questions, temps_secondes, complete)
    )
    resultat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return resultat_id


def get_exercice_stats(exercice_id, user_id):
    """Returns exercise statistics for a user"""
    conn = get_db()

    meilleur = conn.execute(
        '''SELECT * FROM exercices_resultats
        WHERE exercice_id = ? AND user_id = ?
        ORDER BY score DESC, date_completion DESC
        LIMIT 1''',
        (exercice_id, user_id)
    ).fetchone()

    nb_tentatives = conn.execute(
        'SELECT COUNT(*) as count FROM exercices_resultats WHERE exercice_id = ? AND user_id = ?',
        (exercice_id, user_id)
    ).fetchone()

    conn.close()

    meilleur_dict = dict(meilleur) if meilleur else None

    return {
        'meilleur_score': meilleur_dict['score'] if meilleur_dict else 0,
        'meilleur_total': meilleur_dict['total_questions'] if meilleur_dict else 0,
        'meilleur_pourcentage': round((meilleur_dict['score'] / meilleur_dict['total_questions']) * 100) if meilleur_dict and meilleur_dict['total_questions'] > 0 else 0,
        'nb_tentatives': nb_tentatives['count'],
        'complete': meilleur_dict['complete'] if meilleur_dict else False
    }
