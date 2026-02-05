# routes/api.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import (db, User, UserRole, StudentProfile, ProfessorProfile, 
                   Module, Classe, Major, StudentAbsence, ProfessorAbsence,
                   TeachingAssignment)
from utils.decorators import api_login_required, api_role_required
from utils.exceptions import (ValidationError, NotFoundError, AuthorizationError, 
                              DuplicateError, ThresholdExceededError)
from utils.email_service import EmailService
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# ==================== HELPER FUNCTIONS ====================
def success_response(data=None, message=None, status_code=200):
    """Standard success response"""
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    return jsonify(response), status_code


def error_response(message, error_type='Error', status_code=400, **kwargs):
    """Standard error response"""
    response = {
        'success': False,
        'error': error_type,
        'message': message
    }
    response.update(kwargs)
    return jsonify(response), status_code


# ==================== USER ENDPOINTS ====================
@api_bp.route('/users', methods=['GET'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def get_users():
    """Get all users with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if search:
        query = query.filter(User.email.ilike(f'%{search}%'))
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=min(per_page, 100)
    )
    
    users = [{
        'id': u.id,
        'email': u.email,
        'role': u.role,
        'is_active': u.is_active,
        'full_name': u.full_name,
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'last_login': u.last_login.isoformat() if u.last_login else None
    } for u in pagination.items]
    
    return success_response({
        'users': users,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@api_bp.route('/users', methods=['POST'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def create_user():
    """Create a new user with profile"""
    data = request.get_json()
    
    if not data:
        return error_response('Données requises', 'ValidationError')
    
    role = data.get('role')
    email = data.get('email', '').lower()
    
    if not email or not role:
        return error_response('Email et rôle requis', 'ValidationError')
    
    if role not in UserRole.all():
        return error_response('Rôle invalide', 'ValidationError')
    
    # Only super admin can create admin staff
    if role == UserRole.ADMIN_STAFF and current_user.role != UserRole.SUPER_ADMIN:
        return error_response('Seul un super admin peut créer du personnel administratif', 'AuthorizationError', 403)
    
    # Check duplicate email
    if User.query.filter_by(email=email).first():
        return error_response('Cet email est déjà utilisé', 'DuplicateError', 409)
    
    try:
        # Generate password
        initial_password = User.generate_initial_password()
        
        # Create user
        user = User(
            email=email,
            role=role,
            created_by_id=current_user.id
        )
        user.set_password(initial_password)
        db.session.add(user)
        db.session.flush()
        
        # Create profile based on role
        profile_data = data.get('profile', {})
        
        if role == UserRole.STUDENT:
            if not profile_data.get('student_id'):
                db.session.rollback()
                return error_response('student_id requis pour les étudiants', 'ValidationError')
            
            if StudentProfile.query.filter_by(student_id=profile_data['student_id']).first():
                db.session.rollback()
                return error_response('Ce numéro étudiant existe déjà', 'DuplicateError', 409)
            
            profile = StudentProfile(
                user_id=user.id,
                student_id=profile_data['student_id'],
                first_name=profile_data.get('first_name', ''),
                last_name=profile_data.get('last_name', ''),
                date_of_birth=datetime.strptime(profile_data['date_of_birth'], '%Y-%m-%d').date() if profile_data.get('date_of_birth') else None,
                place_of_birth=profile_data.get('place_of_birth'),
                phone=profile_data.get('phone'),
                major_id=profile_data.get('major_id'),
                class_id=profile_data.get('class_id'),
                current_semester=profile_data.get('current_semester', 1)
            )
            db.session.add(profile)
            
        elif role == UserRole.PROFESSOR:
            if not profile_data.get('employee_id'):
                db.session.rollback()
                return error_response('employee_id requis pour les professeurs', 'ValidationError')
            
            if ProfessorProfile.query.filter_by(employee_id=profile_data['employee_id']).first():
                db.session.rollback()
                return error_response('Ce matricule existe déjà', 'DuplicateError', 409)
            
            profile = ProfessorProfile(
                user_id=user.id,
                employee_id=profile_data['employee_id'],
                first_name=profile_data.get('first_name', ''),
                last_name=profile_data.get('last_name', ''),
                phone=profile_data.get('phone'),
                office=profile_data.get('office'),
                department=profile_data.get('department'),
                specialization=profile_data.get('specialization')
            )
            db.session.add(profile)
            
        elif role in [UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN]:
            if not profile_data.get('employee_id'):
                db.session.rollback()
                return error_response('employee_id requis', 'ValidationError')
            
            from models import StaffProfile
            if StaffProfile.query.filter_by(employee_id=profile_data['employee_id']).first():
                db.session.rollback()
                return error_response('Ce matricule existe déjà', 'DuplicateError', 409)
            
            profile = StaffProfile(
                user_id=user.id,
                employee_id=profile_data['employee_id'],
                first_name=profile_data.get('first_name', ''),
                last_name=profile_data.get('last_name', ''),
                phone=profile_data.get('phone'),
                office=profile_data.get('office'),
                department=profile_data.get('department'),
                position=profile_data.get('position')
            )
            db.session.add(profile)
        
        db.session.commit()
        
        # Send welcome email
        try:
            EmailService.send_welcome_email(user, initial_password)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")
        
        return success_response({
            'user_id': user.id,
            'email': user.email,
            'initial_password': initial_password
        }, 'Utilisateur créé avec succès', 201)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {e}")
        return error_response(str(e), 'DatabaseError', 500)


@api_bp.route('/users/<int:user_id>', methods=['GET'])
@api_login_required
def get_user(user_id):
    """Get user details"""
    # Users can view their own profile, admins can view any
    if current_user.id != user_id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF]:
        return error_response('Accès non autorisé', 'AuthorizationError', 403)
    
    user = User.query.get(user_id)
    if not user:
        return error_response('Utilisateur non trouvé', 'NotFoundError', 404)
    
    profile_data = {}
    if user.profile:
        profile_data = {
            'first_name': user.profile.first_name,
            'last_name': user.profile.last_name,
            'phone': getattr(user.profile, 'phone', None),
            'photo': getattr(user.profile, 'photo', None)
        }
    
    return success_response({
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'is_first_login': user.is_first_login,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'profile': profile_data
    })


@api_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def toggle_user_status(user_id):
    """Toggle user active status"""
    user = User.query.get(user_id)
    if not user:
        return error_response('Utilisateur non trouvé', 'NotFoundError', 404)
    
    if user.id == current_user.id:
        return error_response('Vous ne pouvez pas modifier votre propre statut', 'ValidationError')
    
    if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        return error_response('Permission refusée', 'AuthorizationError', 403)
    
    user.is_active = not user.is_active
    db.session.commit()
    
    return success_response({
        'is_active': user.is_active
    }, f"Utilisateur {'activé' if user.is_active else 'désactivé'}")


# ==================== STUDENT ENDPOINTS ====================
@api_bp.route('/students', methods=['GET'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.PROFESSOR)
def get_students():
    """Get students with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    class_id = request.args.get('class_id', type=int)
    major_id = request.args.get('major_id', type=int)
    search = request.args.get('search', '')
    
    query = StudentProfile.query
    
    # Professors can only see their students
    if current_user.role == UserRole.PROFESSOR:
        professor = current_user.professor_profile
        if professor:
            class_ids = [a.class_id for a in professor.teaching_assignments if a.class_id]
            query = query.filter(StudentProfile.class_id.in_(class_ids))
    
    if class_id:
        query = query.filter_by(class_id=class_id)
    
    if major_id:
        query = query.filter_by(major_id=major_id)
    
    if search:
        query = query.filter(
            db.or_(
                StudentProfile.first_name.ilike(f'%{search}%'),
                StudentProfile.last_name.ilike(f'%{search}%'),
                StudentProfile.student_id.ilike(f'%{search}%')
            )
        )
    
    pagination = query.order_by(StudentProfile.last_name).paginate(
        page=page, per_page=min(per_page, 100)
    )
    
    students = [{
        'id': s.id,
        'student_id': s.student_id,
        'first_name': s.first_name,
        'last_name': s.last_name,
        'email': s.user.email if s.user else None,
        'class_id': s.class_id,
        'class_name': s.classe.name if s.classe else None,
        'major_id': s.major_id,
        'major_name': s.major.name if s.major else None,
        'current_semester': s.current_semester
    } for s in pagination.items]
    
    return success_response({
        'students': students,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@api_bp.route('/students/<int:student_id>/absences', methods=['GET'])
@api_login_required
def get_student_absences(student_id):
    """Get student's absences"""
    student = StudentProfile.query.get(student_id)
    if not student:
        return error_response('Étudiant non trouvé', 'NotFoundError', 404)
    
    # Check permissions
    if current_user.role == UserRole.STUDENT:
        if current_user.student_profile and current_user.student_profile.id != student_id:
            return error_response('Accès non autorisé', 'AuthorizationError', 403)
    elif current_user.role == UserRole.PROFESSOR:
        professor = current_user.professor_profile
        if professor:
            class_ids = [a.class_id for a in professor.teaching_assignments if a.class_id]
            if student.class_id not in class_ids:
                return error_response('Accès non autorisé', 'AuthorizationError', 403)
    
    module_id = request.args.get('module_id', type=int)
    
    query = StudentAbsence.query.filter_by(student_id=student_id)
    if module_id:
        query = query.filter_by(module_id=module_id)
    
    absences = query.order_by(StudentAbsence.date.desc()).all()
    
    absence_data = [{
        'id': a.id,
        'module_id': a.module_id,
        'module_name': a.module.name if a.module else None,
        'date': a.date.isoformat(),
        'hours': a.hours,
        'reason': a.reason,
        'is_justified': a.is_justified
    } for a in absences]
    
    # Calculate stats
    total_hours = sum(a.hours for a in absences)
    
    return success_response({
        'absences': absence_data,
        'total_hours': total_hours,
        'count': len(absences)
    })


# ==================== ABSENCE ENDPOINTS ====================
@api_bp.route('/absences/students', methods=['POST'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def create_student_absence():
    """Record a student absence"""
    data = request.get_json()
    
    if not data:
        return error_response('Données requises', 'ValidationError')
    
    student_id = data.get('student_id')
    module_id = data.get('module_id')
    date_str = data.get('date')
    hours = data.get('hours')
    
    if not all([student_id, module_id, date_str, hours]):
        return error_response('Tous les champs sont requis', 'ValidationError')
    
    student = StudentProfile.query.get(student_id)
    if not student:
        return error_response('Étudiant non trouvé', 'NotFoundError', 404)
    
    module = Module.query.get(module_id)
    if not module:
        return error_response('Module non trouvé', 'NotFoundError', 404)
    
    try:
        absence_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return error_response('Format de date invalide (YYYY-MM-DD)', 'ValidationError')
    
    # Check for duplicate
    existing = StudentAbsence.query.filter_by(
        student_id=student_id,
        module_id=module_id,
        date=absence_date
    ).first()
    
    if existing:
        return error_response('Cette absence existe déjà', 'DuplicateError', 409)
    
    try:
        absence = StudentAbsence(
            student_id=student_id,
            module_id=module_id,
            date=absence_date,
            hours=hours,
            reason=data.get('reason'),
            is_justified=data.get('is_justified', False),
            recorded_by_id=current_user.id
        )
        db.session.add(absence)
        db.session.commit()
        
        # Check threshold and send notifications
        total_hours = student.get_total_absence_hours(module_id)
        status = student.check_threshold_status(module_id)
        
        notification_sent = None
        if status == 'warning':
            percentage = (total_hours / module.absence_threshold) * 100
            try:
                EmailService.send_threshold_warning(
                    student.user, module.name, total_hours, 
                    module.absence_threshold, round(percentage)
                )
                notification_sent = 'warning'
            except Exception as e:
                current_app.logger.error(f"Failed to send warning: {e}")
        elif status == 'exceeded':
            try:
                EmailService.send_threshold_exceeded(
                    student.user, module.name, total_hours, module.absence_threshold
                )
                notification_sent = 'exceeded'
            except Exception as e:
                current_app.logger.error(f"Failed to send exceeded: {e}")
        
        return success_response({
            'id': absence.id,
            'total_hours': total_hours,
            'threshold_status': status,
            'notification_sent': notification_sent
        }, 'Absence enregistrée', 201)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating absence: {e}")
        return error_response(str(e), 'DatabaseError', 500)


@api_bp.route('/absences/students/<int:absence_id>/toggle-justified', methods=['POST'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def toggle_student_absence_justified(absence_id):
    """Toggle justified status of a student absence"""
    absence = StudentAbsence.query.get(absence_id)
    if not absence:
        return error_response('Absence non trouvée', 'NotFoundError', 404)
    
    try:
        absence.is_justified = not absence.is_justified
        db.session.commit()
        return success_response({
            'is_justified': absence.is_justified
        }, f"Absence {'justifiée' if absence.is_justified else 'non justifiée'}")
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 'DatabaseError', 500)

@api_bp.route('/absences/students/<int:absence_id>', methods=['DELETE'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def delete_student_absence(absence_id):
    """Delete a student absence"""
    absence = StudentAbsence.query.get(absence_id)
    if not absence:
        return error_response('Absence non trouvée', 'NotFoundError', 404)
    
    try:
        db.session.delete(absence)
        db.session.commit()
        return success_response(message='Absence supprimée')
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 'DatabaseError', 500)


# ==================== MODULE ENDPOINTS ====================
@api_bp.route('/modules', methods=['GET'])
@api_login_required
def get_modules():
    """Get all modules"""
    modules = Module.query.filter_by(is_active=True).order_by(Module.name).all()
    
    return success_response({
        'modules': [{
            'id': m.id,
            'code': m.code,
            'name': m.name,
            'total_hours': m.total_hours,
            'absence_threshold': m.absence_threshold,
            'credits': m.credits
        } for m in modules]
    })


# ==================== CLASS ENDPOINTS ====================
@api_bp.route('/classes', methods=['GET'])
@api_login_required
def get_classes():
    """Get all classes"""
    classes = Classe.query.filter_by(is_active=True).order_by(Classe.code).all()
    
    return success_response({
        'classes': [{
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'academic_year': c.academic_year,
            'semester': c.semester,
            'student_count': c.student_count
        } for c in classes]
    })


# ==================== STATISTICS ENDPOINTS ====================
@api_bp.route('/stats/dashboard', methods=['GET'])
@api_login_required
@api_role_required(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
def get_dashboard_stats():
    """Get dashboard statistics"""
    stats = {
        'users': {
            'total': User.query.count(),
            'students': User.query.filter_by(role=UserRole.STUDENT).count(),
            'professors': User.query.filter_by(role=UserRole.PROFESSOR).count(),
            'staff': User.query.filter_by(role=UserRole.ADMIN_STAFF).count()
        },
        'academic': {
            'classes': Classe.query.filter_by(is_active=True).count(),
            'modules': Module.query.filter_by(is_active=True).count(),
            'majors': Major.query.filter_by(is_active=True).count()
        },
        'absences': {
            'student_total': StudentAbsence.query.count(),
            'professor_total': ProfessorAbsence.query.count()
        }
    }
    
    return success_response(stats)


# ==================== SEARCH ENDPOINT ====================
@api_bp.route('/search', methods=['GET'])
@api_login_required
def search():
    """Global search endpoint"""
    query = request.args.get('q', '').strip()
    entity_type = request.args.get('type', 'all')
    
    if len(query) < 2:
        return error_response('La recherche doit contenir au moins 2 caractères', 'ValidationError')
    
    results = {
        'students': [],
        'professors': [],
        'modules': [],
        'classes': []
    }
    
    if entity_type in ['all', 'students']:
        students = StudentProfile.query.filter(
            db.or_(
                StudentProfile.first_name.ilike(f'%{query}%'),
                StudentProfile.last_name.ilike(f'%{query}%'),
                StudentProfile.student_id.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['students'] = [{
            'id': s.id,
            'student_id': s.student_id,
            'name': f'{s.first_name} {s.last_name}',
            'class': s.classe.name if s.classe else None
        } for s in students]
    
    if entity_type in ['all', 'professors']:
        professors = ProfessorProfile.query.filter(
            db.or_(
                ProfessorProfile.first_name.ilike(f'%{query}%'),
                ProfessorProfile.last_name.ilike(f'%{query}%'),
                ProfessorProfile.employee_id.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['professors'] = [{
            'id': p.id,
            'employee_id': p.employee_id,
            'name': f'{p.first_name} {p.last_name}',
            'department': p.department
        } for p in professors]
    
    if entity_type in ['all', 'modules']:
        modules = Module.query.filter(
            db.or_(
                Module.name.ilike(f'%{query}%'),
                Module.code.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['modules'] = [{
            'id': m.id,
            'code': m.code,
            'name': m.name
        } for m in modules]
    
    if entity_type in ['all', 'classes']:
        classes = Classe.query.filter(
            db.or_(
                Classe.name.ilike(f'%{query}%'),
                Classe.code.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['classes'] = [{
            'id': c.id,
            'code': c.code,
            'name': c.name
        } for c in classes]
    
    return success_response(results)
