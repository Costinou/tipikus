"""
Tipikus Routes - Admin Blueprint
=================================
User management routes (admin only)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import (
    get_user_by_id,
    get_all_users,
    create_user,
    delete_user,
    update_user_password,
    get_users_with_stats,
    get_recent_sessions
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
def admin_users():
    """User management page (admin only)"""
    user_id = session.get('user_id')

    if not user_id or not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('main.index'))

    # Get all users
    users = get_all_users()

    # Get statistics per user
    users_stats = get_users_with_stats()

    # Get last 10 sessions
    recent_sessions = get_recent_sessions(limit=10)

    user = get_user_by_id(user_id)

    return render_template('admin_users.html',
                         users=users,
                         users_stats=users_stats,
                         recent_sessions=recent_sessions,
                         user=user)


@admin_bp.route('/create-user', methods=['POST'])
def admin_create_user():
    """Create a user (admin only)"""
    if not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('main.index'))

    nom = request.form.get('nom', '').strip()
    password = request.form.get('password', '').strip()

    if not nom or not password:
        flash('Username and password required')
        return redirect(url_for('admin.admin_users'))

    if len(nom) > 50:
        flash('Username is too long (max 50 characters)')
        return redirect(url_for('admin.admin_users'))

    if len(password) < 4:
        flash('Password must be at least 4 characters')
        return redirect(url_for('admin.admin_users'))

    user_id = create_user(nom, password)

    if user_id is None:
        flash('This username already exists')
        return redirect(url_for('admin.admin_users'))

    flash(f'User "{nom}" created successfully')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """Delete a user (admin only)"""
    if not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('main.index'))

    # Prevent deleting admin users
    user_to_delete = get_user_by_id(user_id)
    if user_to_delete and user_to_delete.get('is_admin'):
        flash('Cannot delete administrator')
        return redirect(url_for('admin.admin_users'))

    try:
        if user_to_delete:
            nom_user = user_to_delete['nom']
            delete_user(user_id)
            flash(f'User "{nom_user}" deleted successfully')
        else:
            flash('User not found')
    except Exception as e:
        flash(f'Error during deletion: {str(e)}')

    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/reset-password/<int:user_id>', methods=['POST'])
def admin_reset_password(user_id):
    """Reset user password (admin only)"""
    if not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('main.index'))

    new_password = request.form.get('new_password', '').strip()

    if not new_password:
        flash('Password required')
        return redirect(url_for('admin.admin_users'))

    if len(new_password) < 4:
        flash('Password must be at least 4 characters')
        return redirect(url_for('admin.admin_users'))

    user_to_reset = get_user_by_id(user_id)
    if not user_to_reset:
        flash('User not found')
        return redirect(url_for('admin.admin_users'))

    try:
        update_user_password(user_id, new_password)
        flash(f'Password for "{user_to_reset["nom"]}" reset successfully')
    except Exception as e:
        flash(f'Error during reset: {str(e)}')

    return redirect(url_for('admin.admin_users'))
