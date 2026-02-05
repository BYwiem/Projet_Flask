# utils/decorators.py
from functools import wraps
from flask import redirect, url_for, flash, abort, request, jsonify
from flask_login import current_user
from models import UserRole


def login_required_with_role(*roles):
    """
    Decorator to require login and specific role(s).
    Usage: @login_required_with_role(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.is_active:
                flash('Votre compte est désactivé.', 'danger')
                return redirect(url_for('auth.login'))
            
            if roles and current_user.role not in roles:
                flash('Vous n\'avez pas les permissions nécessaires.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def super_admin_required(f):
    """Decorator for routes that require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if current_user.role != UserRole.SUPER_ADMIN:
            flash('Accès réservé au super administrateur.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator for routes that require admin staff or super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF]:
            flash('Accès réservé au personnel administratif.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def professor_required(f):
    """Decorator for routes that require professor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if current_user.role != UserRole.PROFESSOR:
            flash('Accès réservé aux professeurs.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator for routes that require student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if current_user.role != UserRole.STUDENT:
            flash('Accès réservé aux étudiants.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def can_create_users(f):
    """Decorator for routes that require user creation permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.can_create_users():
            flash('Vous n\'avez pas les permissions pour créer des utilisateurs.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Decorator for API routes requiring authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'message': 'Veuillez vous connecter.'
            }), 401
        
        if not current_user.is_active:
            return jsonify({
                'success': False,
                'error': 'Account disabled',
                'message': 'Votre compte est désactivé.'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def api_role_required(*roles):
    """Decorator for API routes requiring specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'message': 'Veuillez vous connecter.'
                }), 401
            
            if current_user.role not in roles:
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'Vous n\'avez pas les permissions nécessaires.'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_first_login(f):
    """Decorator to check if user needs to change password on first login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_first_login:
            if request.endpoint != 'auth.change_password':
                flash('Veuillez changer votre mot de passe initial.', 'warning')
                return redirect(url_for('auth.change_password'))
        return f(*args, **kwargs)
    return decorated_function
