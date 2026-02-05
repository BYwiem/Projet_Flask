# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from models import db, User, UserRole
from forms import LoginForm, ChangePasswordForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user is None:
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html', form=form)
        
        if not user.check_password(form.password.data):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html', form=form)
        
        if not user.is_active:
            flash('Votre compte est désactivé. Contactez l\'administration.', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log in the user
        login_user(user, remember=form.remember_me.data)
        
        # Check if first login
        if user.is_first_login:
            flash('Bienvenue! Veuillez changer votre mot de passe initial.', 'info')
            return redirect(url_for('auth.change_password'))
        
        flash(f'Bienvenue, {user.full_name}!', 'success')
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.landing'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Mot de passe actuel incorrect.', 'danger')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        current_user.is_first_login = False
        current_user.initial_password = None  # Clear initial password once changed
        db.session.commit()
        
        flash('Mot de passe changé avec succès!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            # TODO: Generate reset token and send email
            # from utils.email_service import EmailService
            # token = generate_reset_token(user)
            # EmailService.send_password_reset_email(user, token)
            pass
        
        # Always show success to prevent email enumeration
        flash('Si cet email existe, un lien de réinitialisation a été envoyé.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # TODO: Verify token and get user
    # user = verify_reset_token(token)
    # if not user:
    #     flash('Lien invalide ou expiré.', 'danger')
    #     return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # user.set_password(form.password.data)
        # db.session.commit()
        flash('Mot de passe réinitialisé avec succès!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)
