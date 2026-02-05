# routes/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from models import (db, User, UserRole, StudentProfile, ProfessorProfile, StaffProfile, 
                   Classe, Module, Major, TeachingAssignment, StudentAbsence, 
                   ProfessorAbsence, ThresholdSetting, MajorModule)
from forms import (CreateStudentForm, CreateProfessorForm, CreateStaffForm, 
                  ClasseForm, ModuleForm, MajorForm, ThresholdSettingForm,
                  StudentAbsenceForm, ProfessorAbsenceForm, TeachingAssignmentForm)
from utils.decorators import admin_required, super_admin_required, can_create_users
from utils.email_service import EmailService
from utils.exceptions import ValidationError, DuplicateError

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== DASHBOARDS ====================
@admin_bp.route('/super-admin')
@login_required
@super_admin_required
def super_admin_dashboard():
    """Super Admin Dashboard"""
    stats = {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role=UserRole.STUDENT).count(),
        'total_professors': User.query.filter_by(role=UserRole.PROFESSOR).count(),
        'total_staff': User.query.filter_by(role=UserRole.ADMIN_STAFF).count(),
        'total_classes': Classe.query.count(),
        'total_modules': Module.query.count(),
        'total_majors': Major.query.count(),
        'total_absences': StudentAbsence.query.count() + ProfessorAbsence.query.count(),
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get recent absences
    recent_absences = StudentAbsence.query.order_by(StudentAbsence.date.desc()).limit(10).all()
    
    # Get alerts for students exceeding thresholds
    alerts = []
    for student in StudentProfile.query.all():
        for absence in student.absences:
            status = student.check_threshold_status(absence.module_id)
            if status in ['warning', 'exceeded']:
                existing = next((a for a in alerts if a['student_id'] == student.id and a['module_id'] == absence.module_id), None)
                if not existing:
                    alerts.append({
                        'student_id': student.id,
                        'module_id': absence.module_id,
                        'student_name': f"{student.first_name} {student.last_name}",
                        'type': status,
                        'message': f"Seuil d'absence {'dépassé' if status == 'exceeded' else 'proche'} pour {absence.module.name}"
                    })
    
    return render_template('admin/super_admin_dashboard.html', 
                          stats=stats, 
                          recent_users=recent_users,
                          recent_absences=recent_absences,
                          alerts=alerts[:10])


@admin_bp.route('/staff')
@login_required
@admin_required
def staff_dashboard():
    """Administration Staff Dashboard"""
    from datetime import date
    today = date.today()
    
    # Count absences today
    absences_today = StudentAbsence.query.filter(
        db.func.date(StudentAbsence.date) == today
    ).count()
    
    # Get students with high absence rates and count alerts
    threshold_alerts = []
    for student in StudentProfile.query.all():
        seen_modules = set()
        for absence in student.absences:
            if absence.module_id in seen_modules:
                continue
            seen_modules.add(absence.module_id)
            status = student.check_threshold_status(absence.module_id)
            if status in ['warning', 'exceeded']:
                hours = student.get_total_absence_hours(absence.module_id)
                threshold = absence.module.absence_threshold
                percentage = int((hours / threshold) * 100) if threshold > 0 else 0
                threshold_alerts.append({
                    'student_name': f"{student.first_name} {student.last_name}",
                    'class_name': student.classe.name if student.classe else 'N/A',
                    'module_name': absence.module.name,
                    'hours': hours,
                    'threshold': threshold,
                    'percentage': percentage,
                    'status': status
                })
    
    stats = {
        'total_students': StudentProfile.query.count(),
        'total_professors': ProfessorProfile.query.count(),
        'absences_today': absences_today,
        'threshold_alerts': len(threshold_alerts),
    }
    
    return render_template('admin/staff_dashboard.html', 
                          stats=stats,
                          threshold_alerts=threshold_alerts[:10])


# ==================== USER MANAGEMENT ====================
@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if search:
        query = query.filter(User.email.ilike(f'%{search}%'))
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    return render_template('admin/users/list.html', 
                          users=users,
                          role_filter=role_filter,
                          search=search,
                          roles=UserRole.choices())


@admin_bp.route('/users/create-student', methods=['GET', 'POST'])
@login_required
@can_create_users
def create_student():
    """Create a new student user"""
    form = CreateStudentForm()
    
    # Populate select fields
    form.major_id.choices = [(0, '-- Sélectionner --')] + [
        (m.id, m.name) for m in Major.query.filter_by(is_active=True).all()
    ]
    form.class_id.choices = [(0, '-- Sélectionner --')] + [
        (c.id, f'{c.code} - {c.name}') for c in Classe.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        # Check for duplicate email
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/users/create_student.html', form=form)
        
        # Check for duplicate student ID
        if StudentProfile.query.filter_by(student_id=form.student_id.data).first():
            flash('Ce numéro étudiant est déjà utilisé.', 'danger')
            return render_template('admin/users/create_student.html', form=form)
        
        try:
            # Generate initial password
            initial_password = User.generate_initial_password()
            
            # Create user
            user = User(
                email=form.email.data.lower(),
                role=UserRole.STUDENT,
                created_by_id=current_user.id,
                initial_password=initial_password  # Store for admin visibility
            )
            user.set_password(initial_password)
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Handle photo upload
            photo_filename = None
            if form.photo.data:
                filename = secure_filename(form.photo.data.filename)
                filename = f"student_{user.id}_{filename}"
                upload_path = os.path.join(
                    current_app.config['UPLOADED_PHOTOS_DEST'],
                    filename
                )
                form.photo.data.save(upload_path)
                photo_filename = filename
            
            # Create student profile
            profile = StudentProfile(
                user_id=user.id,
                student_id=form.student_id.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                date_of_birth=form.date_of_birth.data,
                place_of_birth=form.place_of_birth.data,
                phone=form.phone.data,
                address=form.address.data,
                photo=photo_filename,
                major_id=form.major_id.data if form.major_id.data else None,
                current_semester=form.current_semester.data,
                class_id=form.class_id.data if form.class_id.data else None
            )
            db.session.add(profile)
            db.session.commit()
            
            # Send welcome email
            try:
                EmailService.send_welcome_email(user, initial_password)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email: {e}")
            
            flash(f'Étudiant créé avec succès! Mot de passe initial: {initial_password}', 'success')
            return redirect(url_for('admin.list_students'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating student: {e}")
            flash(f'Erreur lors de la création: {str(e)}', 'danger')
    
    return render_template('admin/users/create_student.html', form=form)


@admin_bp.route('/users/create-professor', methods=['GET', 'POST'])
@login_required
@can_create_users
def create_professor():
    """Create a new professor user"""
    form = CreateProfessorForm()
    
    # Populate choices for modules
    form.modules.choices = [(m.id, f"{m.code} - {m.name}") for m in Module.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Check for duplicate email
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/users/create_professor.html', form=form)
        
        # Check for duplicate employee ID
        if ProfessorProfile.query.filter_by(employee_id=form.employee_id.data).first():
            flash('Ce matricule est déjà utilisé.', 'danger')
            return render_template('admin/users/create_professor.html', form=form)
        
        try:
            # Generate initial password
            initial_password = User.generate_initial_password()
            
            # Create user
            user = User(
                email=form.email.data.lower(),
                role=UserRole.PROFESSOR,
                created_by_id=current_user.id,
                initial_password=initial_password  # Store for admin visibility
            )
            user.set_password(initial_password)
            db.session.add(user)
            db.session.flush()
            
            # Handle photo upload
            photo_filename = None
            if form.photo.data:
                filename = secure_filename(form.photo.data.filename)
                filename = f"professor_{user.id}_{filename}"
                upload_path = os.path.join(
                    current_app.config['UPLOADED_PHOTOS_DEST'],
                    filename
                )
                form.photo.data.save(upload_path)
                photo_filename = filename
            
            # Create professor profile
            profile = ProfessorProfile(
                user_id=user.id,
                employee_id=form.employee_id.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                office=form.office.data,
                department=form.department.data,
                specialization=form.specialization.data,
                hire_date=form.hire_date.data,
                photo=photo_filename
            )
            db.session.add(profile)
            db.session.flush()  # Get the profile ID
            
            # Associate with selected modules (create TeachingAssignments)
            for module_id in form.modules.data:
                ta = TeachingAssignment(
                    professor_id=profile.id,
                    module_id=module_id
                )
                db.session.add(ta)
            
            db.session.commit()
            
            # Send welcome email
            try:
                EmailService.send_welcome_email(user, initial_password)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email: {e}")
            
            flash(f'Professeur créé avec succès! Mot de passe initial: {initial_password}', 'success')
            return redirect(url_for('admin.list_professors'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating professor: {e}")
            flash(f'Erreur lors de la création: {str(e)}', 'danger')
    
    return render_template('admin/users/create_professor.html', form=form)


@admin_bp.route('/users/create-staff', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_staff():
    """Create a new administration staff user (Super Admin only)"""
    form = CreateStaffForm()
    
    if form.validate_on_submit():
        # Check for duplicate email
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/users/create_staff.html', form=form)
        
        # Check for duplicate employee ID
        if StaffProfile.query.filter_by(employee_id=form.employee_id.data).first():
            flash('Ce matricule est déjà utilisé.', 'danger')
            return render_template('admin/users/create_staff.html', form=form)
        
        try:
            # Generate initial password
            initial_password = User.generate_initial_password()
            
            # Create user
            user = User(
                email=form.email.data.lower(),
                role=UserRole.ADMIN_STAFF,
                created_by_id=current_user.id,
                initial_password=initial_password  # Store for admin visibility
            )
            user.set_password(initial_password)
            db.session.add(user)
            db.session.flush()
            
            # Handle photo upload
            photo_filename = None
            if form.photo.data:
                filename = secure_filename(form.photo.data.filename)
                filename = f"staff_{user.id}_{filename}"
                upload_path = os.path.join(
                    current_app.config['UPLOADED_PHOTOS_DEST'],
                    filename
                )
                form.photo.data.save(upload_path)
                photo_filename = filename
            
            # Create staff profile
            profile = StaffProfile(
                user_id=user.id,
                employee_id=form.employee_id.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                office=form.office.data,
                department=form.department.data,
                position=form.position.data,
                hire_date=form.hire_date.data,
                photo=photo_filename
            )
            db.session.add(profile)
            db.session.commit()
            
            # Send welcome email
            try:
                EmailService.send_welcome_email(user, initial_password)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email: {e}")
            
            flash(f'Personnel créé avec succès! Mot de passe initial: {initial_password}', 'success')
            return redirect(url_for('admin.list_users'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating staff: {e}")
            flash(f'Erreur lors de la création: {str(e)}', 'danger')
    
    return render_template('admin/users/create_staff.html', form=form)


@admin_bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    """Toggle user active status"""
    user = User.query.get_or_404(id)
    
    # Prevent deactivating self
    if user.id == current_user.id:
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    # Only super admin can modify other super admins
    if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        flash('Seul un super administrateur peut modifier un autre super administrateur.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activé' if user.is_active else 'désactivé'
    flash(f'Compte {status} avec succès.', 'success')
    return redirect(url_for('admin.list_users'))


# ==================== STUDENT MANAGEMENT ====================
@admin_bp.route('/students')
@login_required
@admin_required
def list_students():
    """List all students"""
    page = request.args.get('page', 1, type=int)
    class_filter = request.args.get('class_id', 0, type=int)
    major_filter = request.args.get('major_id', 0, type=int)
    search = request.args.get('search', '')
    
    query = StudentProfile.query
    
    if class_filter:
        query = query.filter_by(class_id=class_filter)
    
    if major_filter:
        query = query.filter_by(major_id=major_filter)
    
    if search:
        query = query.filter(
            db.or_(
                StudentProfile.first_name.ilike(f'%{search}%'),
                StudentProfile.last_name.ilike(f'%{search}%'),
                StudentProfile.student_id.ilike(f'%{search}%')
            )
        )
    
    students = query.order_by(StudentProfile.last_name).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    classes = Classe.query.filter_by(is_active=True).all()
    majors = Major.query.filter_by(is_active=True).all()
    
    return render_template('admin/students/list.html',
                          students=students,
                          classes=classes,
                          majors=majors,
                          class_filter=class_filter,
                          major_filter=major_filter,
                          search=search)


@admin_bp.route('/students/<int:id>')
@login_required
@admin_required
def view_student(id):
    """View student details"""
    student = StudentProfile.query.get_or_404(id)
    
    # Calculate absence stats per module
    absence_stats = []
    modules = set([a.module for a in student.absences])
    for module in modules:
        total_hours = student.get_total_absence_hours(module.id)
        rate = student.get_absence_rate(module.id)
        status = student.check_threshold_status(module.id)
        absence_stats.append({
            'module': module,
            'hours': total_hours,
            'rate': rate,
            'status': status
        })
    
    return render_template('admin/students/view.html',
                          student=student,
                          absence_stats=absence_stats)


# ==================== PROFESSOR MANAGEMENT ====================
@admin_bp.route('/professors')
@login_required
@admin_required
def list_professors():
    """List all professors"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = ProfessorProfile.query
    
    if search:
        query = query.filter(
            db.or_(
                ProfessorProfile.first_name.ilike(f'%{search}%'),
                ProfessorProfile.last_name.ilike(f'%{search}%'),
                ProfessorProfile.employee_id.ilike(f'%{search}%')
            )
        )
    
    professors = query.order_by(ProfessorProfile.last_name).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    return render_template('admin/professors/list.html',
                          professors=professors,
                          search=search)


@admin_bp.route('/professors/<int:id>')
@login_required
@admin_required
def view_professor(id):
    """View professor details"""
    professor = ProfessorProfile.query.get_or_404(id)
    
    return render_template('admin/professors/view.html', professor=professor)


# ==================== CLASS MANAGEMENT ====================
@admin_bp.route('/classes')
@login_required
@admin_required
def list_classes():
    """List all classes"""
    classes = Classe.query.order_by(Classe.code).all()
    return render_template('admin/classes/list.html', classes=classes)


@admin_bp.route('/classes/<int:id>')
@login_required
@admin_required
def view_class(id):
    """View class details"""
    classe = Classe.query.get_or_404(id)
    return render_template('admin/classes/view.html', classe=classe)


@admin_bp.route('/classes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_class():
    """Create a new class"""
    form = ClasseForm()
    
    if form.validate_on_submit():
        if Classe.query.filter_by(code=form.code.data).first():
            flash('Ce code de classe existe déjà.', 'danger')
            return render_template('admin/classes/create.html', form=form)
        
        classe = Classe(
            code=form.code.data,
            name=form.name.data,
            academic_year=form.academic_year.data,
            semester=form.semester.data,
            max_students=form.max_students.data,
            is_active=form.is_active.data
        )
        db.session.add(classe)
        db.session.commit()
        
        flash('Classe créée avec succès!', 'success')
        return redirect(url_for('admin.list_classes'))
    
    return render_template('admin/classes/create.html', form=form)


# ==================== MODULE MANAGEMENT ====================
@admin_bp.route('/modules')
@login_required
@admin_required
def list_modules():
    """List all modules"""
    modules = Module.query.order_by(Module.code).all()
    return render_template('admin/modules/list.html', modules=modules)


@admin_bp.route('/modules/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_module():
    """Create a new module"""
    form = ModuleForm()
    
    # Populate choices for majors and professors
    form.majors.choices = [(m.id, f"{m.code} - {m.name}") for m in Major.query.filter_by(is_active=True).all()]
    form.professors.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in ProfessorProfile.query.order_by(ProfessorProfile.last_name).all()]
    
    if form.validate_on_submit():
        if Module.query.filter_by(code=form.code.data).first():
            flash('Ce code de module existe déjà.', 'danger')
            return render_template('admin/modules/create.html', form=form)
        
        # Calculate absence threshold from hours and minutes
        absence_threshold = form.absence_threshold_hours.data + (form.absence_threshold_minutes.data / 60)
        
        module = Module(
            code=form.code.data,
            name=form.name.data,
            description=form.description.data,
            total_hours=form.total_hours.data,
            absence_threshold=absence_threshold,
            credits=form.credits.data,
            is_active=form.is_active.data
        )
        db.session.add(module)
        db.session.flush()  # Get the module ID
        
        # Associate with selected majors (default semester 1)
        for major_id in form.majors.data:
            mm = MajorModule(major_id=major_id, module_id=module.id, semester=1)
            db.session.add(mm)
        
        # Create teaching assignments for selected professors
        for professor_id in form.professors.data:
            ta = TeachingAssignment(
                professor_id=professor_id,
                module_id=module.id,
                academic_year=f"{datetime.now().year}-{datetime.now().year + 1}"
            )
            db.session.add(ta)
        
        db.session.commit()
        
        flash('Module créé avec succès!', 'success')
        return redirect(url_for('admin.list_modules'))
    
    return render_template('admin/modules/create.html', form=form)


@admin_bp.route('/modules/<int:id>')
@login_required
@admin_required
def view_module(id):
    """View module details"""
    module = Module.query.get_or_404(id)
    # Get all teaching assignments for this module
    assignments = module.teaching_assignments
    return render_template('admin/modules/view.html', module=module, assignments=assignments)


@admin_bp.route('/modules/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_module(id):
    """Edit a module"""
    module = Module.query.get_or_404(id)
    form = ModuleForm(obj=module)
    
    # Populate choices for majors and professors
    form.majors.choices = [(m.id, f"{m.code} - {m.name}") for m in Major.query.filter_by(is_active=True).all()]
    form.professors.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in ProfessorProfile.query.order_by(ProfessorProfile.last_name).all()]
    
    if request.method == 'GET':
        # Pre-populate hours and minutes from absence_threshold
        form.absence_threshold_hours.data = int(module.absence_threshold)
        form.absence_threshold_minutes.data = int((module.absence_threshold % 1) * 60)
        # Pre-populate selected majors and professors
        form.majors.data = [mm.major_id for mm in module.majors]
        form.professors.data = [ta.professor_id for ta in module.teaching_assignments]
    
    if form.validate_on_submit():
        # Check if new code already exists for another module
        existing = Module.query.filter_by(code=form.code.data).first()
        if existing and existing.id != module.id:
            flash('Ce code de module existe déjà.', 'danger')
            return render_template('admin/modules/edit.html', form=form, module=module)
        
        module.code = form.code.data
        module.name = form.name.data
        module.description = form.description.data
        module.total_hours = form.total_hours.data
        module.absence_threshold = form.absence_threshold_hours.data + (form.absence_threshold_minutes.data / 60)
        module.credits = form.credits.data
        module.is_active = form.is_active.data
        
        # Update major associations
        MajorModule.query.filter_by(module_id=module.id).delete()
        for major_id in form.majors.data:
            mm = MajorModule(major_id=major_id, module_id=module.id, semester=1)
            db.session.add(mm)
        
        # Update teaching assignments
        TeachingAssignment.query.filter_by(module_id=module.id).delete()
        for professor_id in form.professors.data:
            ta = TeachingAssignment(
                professor_id=professor_id,
                module_id=module.id,
                academic_year=f"{datetime.now().year}-{datetime.now().year + 1}"
            )
            db.session.add(ta)
        
        db.session.commit()
        flash('Module mis à jour avec succès!', 'success')
        return redirect(url_for('admin.view_module', id=module.id))
    
    return render_template('admin/modules/edit.html', form=form, module=module)


# ==================== MAJOR MANAGEMENT ====================
@admin_bp.route('/majors')
@login_required
@admin_required
def list_majors():
    """List all majors"""
    majors = Major.query.order_by(Major.code).all()
    return render_template('admin/majors/list.html', majors=majors)


@admin_bp.route('/majors/<int:id>')
@login_required
@admin_required
def view_major(id):
    """View major details"""
    major = Major.query.get_or_404(id)
    return render_template('admin/majors/view.html', major=major)


@admin_bp.route('/majors/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_major():
    """Create a new major"""
    form = MajorForm()
    
    # Populate choices for modules and classes
    form.modules.choices = [(m.id, f"{m.code} - {m.name}") for m in Module.query.filter_by(is_active=True).all()]
    form.classes.choices = [(c.id, f"{c.code} - {c.name}") for c in Classe.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        if Major.query.filter_by(code=form.code.data).first():
            flash('Ce code de filière existe déjà.', 'danger')
            return render_template('admin/majors/create.html', form=form)
        
        major = Major(
            code=form.code.data,
            name=form.name.data,
            description=form.description.data,
            total_semesters=form.total_semesters.data,
            is_active=form.is_active.data
        )
        db.session.add(major)
        db.session.flush()  # Get the major ID
        
        # Associate with selected modules (default semester 1)
        for module_id in form.modules.data:
            mm = MajorModule(major_id=major.id, module_id=module_id, semester=1)
            db.session.add(mm)
        
        # Associate with selected classes
        for class_id in form.classes.data:
            classe = Classe.query.get(class_id)
            if classe:
                classe.major_id = major.id
        
        db.session.commit()
        
        flash('Filière créée avec succès!', 'success')
        return redirect(url_for('admin.list_majors'))
    
    return render_template('admin/majors/create.html', form=form)


@admin_bp.route('/majors/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_major(id):
    """Edit an existing major"""
    major = Major.query.get_or_404(id)
    form = MajorForm(obj=major)
    
    # Populate choices for modules and classes
    form.modules.choices = [(m.id, f"{m.code} - {m.name}") for m in Module.query.filter_by(is_active=True).all()]
    form.classes.choices = [(c.id, f"{c.code} - {c.name}") for c in Classe.query.filter_by(is_active=True).all()]
    
    if request.method == 'GET':
        # Pre-populate selected modules and classes
        form.modules.data = [mm.module_id for mm in major.modules]
        form.classes.data = [c.id for c in major.classes]
    
    if form.validate_on_submit():
        # Check for duplicate code (excluding current)
        existing = Major.query.filter(Major.code == form.code.data, Major.id != major.id).first()
        if existing:
            flash('Ce code de filière existe déjà.', 'danger')
            return render_template('admin/majors/edit.html', form=form, major=major)
        
        major.code = form.code.data
        major.name = form.name.data
        major.description = form.description.data
        major.total_semesters = form.total_semesters.data
        major.is_active = form.is_active.data
        
        # Update module associations
        MajorModule.query.filter_by(major_id=major.id).delete()
        for module_id in form.modules.data:
            mm = MajorModule(major_id=major.id, module_id=module_id, semester=1)
            db.session.add(mm)
        
        # Update class associations - first unassign all classes from this major
        Classe.query.filter_by(major_id=major.id).update({'major_id': None})
        # Then assign selected classes
        for class_id in form.classes.data:
            classe = Classe.query.get(class_id)
            if classe:
                classe.major_id = major.id
        
        db.session.commit()
        
        flash('Filière mise à jour avec succès!', 'success')
        return redirect(url_for('admin.view_major', id=major.id))
    
    return render_template('admin/majors/edit.html', form=form, major=major)


# ==================== ABSENCE MANAGEMENT ====================
@admin_bp.route('/absences/students')
@login_required
@admin_required
def list_student_absences():
    """List student absences"""
    page = request.args.get('page', 1, type=int)
    student_filter = request.args.get('student_id', 0, type=int)
    module_filter = request.args.get('module_id', 0, type=int)
    
    query = StudentAbsence.query
    
    if student_filter:
        query = query.filter_by(student_id=student_filter)
    
    if module_filter:
        query = query.filter_by(module_id=module_filter)
    
    absences = query.order_by(StudentAbsence.date.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    students = StudentProfile.query.order_by(StudentProfile.last_name).all()
    modules = Module.query.filter_by(is_active=True).all()
    
    return render_template('admin/absences/student_list.html',
                          absences=absences,
                          students=students,
                          modules=modules,
                          student_filter=student_filter,
                          module_filter=module_filter)


@admin_bp.route('/absences/students/<int:absence_id>/toggle-justified', methods=['POST'])
@login_required
@admin_required
def toggle_student_absence_justified(absence_id):
    """Toggle justified status of a student absence"""
    absence = StudentAbsence.query.get_or_404(absence_id)
    absence.is_justified = not absence.is_justified
    db.session.commit()
    flash(f"Absence {'justifiée' if absence.is_justified else 'non justifiée'} avec succès!", 'success')
    return redirect(url_for('admin.list_student_absences'))


@admin_bp.route('/absences/students/<int:absence_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student_absence(absence_id):
    """Delete a student absence"""
    absence = StudentAbsence.query.get_or_404(absence_id)
    db.session.delete(absence)
    db.session.commit()
    flash('Absence supprimée avec succès!', 'success')
    return redirect(url_for('admin.list_student_absences'))


@admin_bp.route('/absences/students/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_student_absence():
    """Record a student absence"""
    form = StudentAbsenceForm()
    
    form.student_id.choices = [
        (s.id, f'{s.student_id} - {s.first_name} {s.last_name}')
        for s in StudentProfile.query.order_by(StudentProfile.last_name).all()
    ]
    form.module_id.choices = [
        (m.id, f'{m.code} - {m.name}')
        for m in Module.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        # Check for duplicate
        existing = StudentAbsence.query.filter_by(
            student_id=form.student_id.data,
            module_id=form.module_id.data,
            date=form.date.data
        ).first()
        
        if existing:
            flash('Cette absence a déjà été enregistrée.', 'danger')
            return render_template('admin/absences/create_student.html', form=form)
        
        absence = StudentAbsence(
            student_id=form.student_id.data,
            module_id=form.module_id.data,
            date=form.date.data,
            hours=form.hours.data,
            reason=form.reason.data,
            is_justified=form.is_justified.data,
            recorded_by_id=current_user.id
        )
        db.session.add(absence)
        db.session.commit()
        
        # Check threshold and send notifications
        student = StudentProfile.query.get(form.student_id.data)
        module = Module.query.get(form.module_id.data)
        total_hours = student.get_total_absence_hours(module.id)
        status = student.check_threshold_status(module.id)
        
        if status == 'warning':
            percentage = (total_hours / module.absence_threshold) * 100
            try:
                EmailService.send_threshold_warning(
                    student.user, module.name, total_hours, 
                    module.absence_threshold, round(percentage)
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send warning email: {e}")
        elif status == 'exceeded':
            try:
                EmailService.send_threshold_exceeded(
                    student.user, module.name, total_hours, module.absence_threshold
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send exceeded email: {e}")
        
        flash('Absence enregistrée avec succès!', 'success')
        return redirect(url_for('admin.list_student_absences'))
    
    return render_template('admin/absences/create_student.html', form=form)


@admin_bp.route('/absences/professors')
@login_required
@admin_required
def list_professor_absences():
    """List professor absences"""
    page = request.args.get('page', 1, type=int)
    professor_filter = request.args.get('professor_id', 0, type=int)
    
    query = ProfessorAbsence.query
    
    if professor_filter:
        query = query.filter_by(professor_id=professor_filter)
    
    absences = query.order_by(ProfessorAbsence.date.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    professors = ProfessorProfile.query.order_by(ProfessorProfile.last_name).all()
    
    return render_template('admin/absences/professor_list.html',
                          absences=absences,
                          professors=professors,
                          professor_filter=professor_filter)


@admin_bp.route('/absences/professors/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_professor_absence():
    """Record a professor absence"""
    form = ProfessorAbsenceForm()
    
    form.professor_id.choices = [
        (p.id, f'{p.employee_id} - {p.first_name} {p.last_name}')
        for p in ProfessorProfile.query.order_by(ProfessorProfile.last_name).all()
    ]
    
    if form.validate_on_submit():
        # Check for duplicate
        existing = ProfessorAbsence.query.filter_by(
            professor_id=form.professor_id.data,
            date=form.date.data
        ).first()
        
        if existing:
            flash('Cette absence a déjà été enregistrée.', 'danger')
            return render_template('admin/absences/create_professor.html', form=form)
        
        absence = ProfessorAbsence(
            professor_id=form.professor_id.data,
            date=form.date.data,
            hours=form.hours.data,
            reason=form.reason.data,
            is_justified=form.is_justified.data,
            recorded_by_id=current_user.id
        )
        db.session.add(absence)
        db.session.commit()
        
        flash('Absence enregistrée avec succès!', 'success')
        return redirect(url_for('admin.list_professor_absences'))
    
    return render_template('admin/absences/create_professor.html', form=form)


# ==================== THRESHOLD SETTINGS ====================
@admin_bp.route('/settings/thresholds')
@login_required
@admin_required
def threshold_settings():
    """Manage threshold settings"""
    settings = ThresholdSetting.query.all()
    modules = Module.query.filter_by(is_active=True).all()
    
    return render_template('admin/settings/thresholds.html',
                          settings=settings,
                          modules=modules)


@admin_bp.route('/settings/thresholds/update', methods=['POST'])
@login_required
@admin_required
def update_threshold():
    """Update threshold setting"""
    setting_type = request.form.get('setting_type', 'professor_global')
    threshold_days = request.form.get('threshold_days', 0, type=int)
    threshold_hours = request.form.get('threshold_hours', 0, type=int)
    warning_percentage = request.form.get('warning_percentage', 50, type=float)
    
    if threshold_days == 0 and threshold_hours == 0:
        flash('Le seuil doit être supérieur à 0.', 'danger')
        return redirect(url_for('admin.threshold_settings'))
    
    # Find or create setting
    setting = ThresholdSetting.query.filter_by(setting_type=setting_type).first()
    
    if setting:
        setting.threshold_days = threshold_days
        setting.threshold_hours = threshold_hours
        setting.warning_percentage = warning_percentage
        setting.updated_by_id = current_user.id
    else:
        setting = ThresholdSetting(
            setting_type=setting_type,
            threshold_days=threshold_days,
            threshold_hours=threshold_hours,
            warning_percentage=warning_percentage,
            updated_by_id=current_user.id
        )
        db.session.add(setting)
    
    db.session.commit()
    flash('Seuil mis à jour avec succès!', 'success')
    return redirect(url_for('admin.threshold_settings'))


# ==================== TEACHING ASSIGNMENTS ====================
@admin_bp.route('/assignments')
@login_required
@admin_required
def list_assignments():
    """List teaching assignments"""
    assignments = TeachingAssignment.query.all()
    return render_template('admin/assignments/list.html', assignments=assignments)


@admin_bp.route('/assignments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assignment():
    """Create a teaching assignment"""
    form = TeachingAssignmentForm()
    
    form.professor_id.choices = [
        (p.id, f'{p.first_name} {p.last_name}')
        for p in ProfessorProfile.query.order_by(ProfessorProfile.last_name).all()
    ]
    form.module_id.choices = [
        (m.id, f'{m.code} - {m.name}')
        for m in Module.query.filter_by(is_active=True).all()
    ]
    form.class_id.choices = [(0, '-- Toutes les classes --')] + [
        (c.id, f'{c.code} - {c.name}')
        for c in Classe.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        assignment = TeachingAssignment(
            professor_id=form.professor_id.data,
            module_id=form.module_id.data,
            class_id=form.class_id.data if form.class_id.data else None,
            academic_year=form.academic_year.data,
            semester=form.semester.data
        )
        db.session.add(assignment)
        db.session.commit()
        
        flash('Affectation créée avec succès!', 'success')
        return redirect(url_for('admin.list_assignments'))
    
    return render_template('admin/assignments/create.html', form=form)
