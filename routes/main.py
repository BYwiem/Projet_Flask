# routes/main.py
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, User, UserRole, Classe, Module, StudentProfile, ProfessorProfile, StudentAbsence, Major
from utils.decorators import check_first_login

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def landing():
    """Public landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')


@main_bp.route('/dashboard')
@login_required
@check_first_login
def dashboard():
    """Role-based dashboard"""
    if current_user.role == UserRole.SUPER_ADMIN:
        return redirect(url_for('admin.super_admin_dashboard'))
    elif current_user.role == UserRole.ADMIN_STAFF:
        return redirect(url_for('admin.staff_dashboard'))
    elif current_user.role == UserRole.PROFESSOR:
        return redirect(url_for('professor.dashboard'))
    elif current_user.role == UserRole.STUDENT:
        return redirect(url_for('student.dashboard'))
    else:
        flash('Rôle inconnu.', 'danger')
        return redirect(url_for('main.landing'))


@main_bp.route('/profile')
@login_required
@check_first_login
def profile():
    """View user profile"""
    profile = current_user.profile
    return render_template('profile.html', user=current_user, profile=profile)


@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@check_first_login
def edit_profile():
    """Edit user profile"""
    from forms import UpdateProfileForm
    from flask import request
    from werkzeug.utils import secure_filename
    import os
    
    form = UpdateProfileForm()
    profile = current_user.profile
    
    if form.validate_on_submit():
        if profile:
            profile.first_name = form.first_name.data
            profile.last_name = form.last_name.data
            profile.phone = form.phone.data
            
            # Handle date_of_birth if the profile has this attribute
            if hasattr(profile, 'date_of_birth') and form.date_of_birth.data:
                profile.date_of_birth = form.date_of_birth.data
            
            # Handle address if the profile has this attribute
            if hasattr(profile, 'address') and form.address.data:
                profile.address = form.address.data
            
            # Handle photo upload
            if form.photo.data:
                filename = secure_filename(form.photo.data.filename)
                # Add user ID to filename to avoid conflicts
                filename = f"user_{current_user.id}_{filename}"
                upload_path = os.path.join(
                    current_app.config['UPLOADED_PHOTOS_DEST'], 
                    filename
                )
                form.photo.data.save(upload_path)
                profile.photo = filename
            
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            return redirect(url_for('main.profile'))
    
    elif request.method == 'GET' and profile:
        form.first_name.data = profile.first_name
        form.last_name.data = profile.last_name
        form.phone.data = getattr(profile, 'phone', None)
        form.date_of_birth.data = getattr(profile, 'date_of_birth', None)
        form.address.data = getattr(profile, 'address', None)
    
    return render_template('edit_profile.html', form=form, user=current_user, profile=profile)


@main_bp.route('/notifications')
@login_required
@check_first_login
def notifications():
    """View user notifications"""
    from models import NotificationLog
    
    notifications = NotificationLog.query.filter_by(
        recipient_id=current_user.id
    ).order_by(NotificationLog.sent_at.desc()).limit(50).all()
    
    return render_template('notifications.html', notifications=notifications)


@main_bp.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def mark_notification_read(id):
    """Mark notification as read"""
    from models import NotificationLog
    from datetime import datetime
    
    notification = NotificationLog.query.get_or_404(id)
    
    if notification.recipient_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.notifications'))
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return redirect(url_for('main.notifications'))


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')
