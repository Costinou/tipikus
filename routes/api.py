"""
Tipikus Routes - API Blueprint
===============================
API endpoints for AJAX requests
"""

from io import BytesIO
from flask import Blueprint, request, jsonify, session, send_file
from database import (
    get_mots_by_deck,
    create_session
)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Check if gTTS is available
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


@api_bp.route('/mots/<int:deck_id>')
def api_mots(deck_id):
    """API to retrieve words from a deck"""
    mots = get_mots_by_deck(deck_id)
    return jsonify([{
        'id': mot['id'],
        'mot_francais': mot['mot_francais'],
        'traduction': mot['traduction']
    } for mot in mots])


@api_bp.route('/tts')
def text_to_speech():
    """API to generate Hungarian TTS audio"""
    if not GTTS_AVAILABLE:
        return jsonify({'error': 'gTTS not available'}), 503

    texte = request.args.get('text', '')
    if not texte:
        return jsonify({'error': 'Missing text parameter'}), 400

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


@api_bp.route('/session', methods=['POST'])
def enregistrer_session():
    """API to record a learning session"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()

        deck_id = data.get('deck_id')
        type_session = data.get('type_session')
        nombre_mots_vus = data.get('nombre_mots_vus', 0)
        score = data.get('score', 0)
        duree_secondes = data.get('duree_secondes', 0)
        complete = data.get('complete', False)

        if not deck_id or not type_session:
            return jsonify({'error': 'Missing parameters'}), 400

        # Pass user_id to create_session function
        session_id = create_session(
            deck_id, user_id, type_session, nombre_mots_vus,
            score, duree_secondes, complete
        )

        return jsonify({'success': True, 'session_id': session_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/xp-gain', methods=['POST'])
def get_xp_gain():
    """API to calculate XP gains from an activity"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()

        activity_type = data.get('type')  # 'flashcard', 'quiz', 'exercice'
        deck_id = data.get('deck_id')
        exercice_id = data.get('exercice_id')
        score = data.get('score', 0)
        total = data.get('total', 0)

        xp_gain = 0
        bonus = 0
        details = []

        if activity_type == 'flashcard':
            # 10 XP per card seen
            xp_gain = total * 10
            details.append(f"+{xp_gain} XP - {total} card(s) seen")

            # Track last studied deck for review suggestion
            if deck_id:
                session['last_studied_deck_id'] = deck_id
                session.modified = True

        elif activity_type == 'quiz':
            # 20 XP per correct answer, 5 XP per incorrect
            correct = score
            incorrect = total - score

            xp_gain = (correct * 20) + (incorrect * 5)
            details.append(f"+{correct * 20} XP - {correct} correct answer(s)")
            if incorrect > 0:
                details.append(f"+{incorrect * 5} XP - {incorrect} attempt(s)")

            # Bonus
            if total > 0:
                success_rate = score / total
                if success_rate >= 0.8:
                    bonus += 10
                    details.append(f"+10 XP - Bonus 80%+")
                if success_rate == 1.0:
                    bonus += 20
                    details.append(f"+20 XP - Perfect score!")

        elif activity_type == 'exercice':
            # 25 XP per correct answer, 8 XP per incorrect
            correct = score
            incorrect = total - score

            xp_gain = (correct * 25) + (incorrect * 8)
            details.append(f"+{correct * 25} XP - {correct} correct answer(s)")
            if incorrect > 0:
                details.append(f"+{incorrect * 8} XP - {incorrect} attempt(s)")

            # Bonus
            if total > 0:
                success_rate = score / total
                if success_rate >= 0.8:
                    bonus += 25
                    details.append(f"+25 XP - Bonus 80%+")
                if success_rate == 1.0:
                    bonus += 50
                    details.append(f"+50 XP - Perfect score!")

        total_xp = xp_gain + bonus

        return jsonify({
            'success': True,
            'xp_gain': total_xp,
            'details': details
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tour-completed', methods=['POST'])
def tour_completed():
    """Mark the onboarding tour as completed"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Store in session that user has completed the tour
        session['tour_completed'] = True
        session.modified = True

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/lesson-tour-completed', methods=['POST'])
def lesson_tour_completed():
    """Mark the lesson tour as completed"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Store in session that user has completed the lesson tour
        session['lesson_tour_completed'] = True
        session.modified = True

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dismiss-last-deck', methods=['POST'])
def dismiss_last_deck():
    """Clear the last studied deck suggestion"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Clear the last studied deck from session
        session.pop('last_studied_deck_id', None)
        session.modified = True

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
