# routes/professor.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import (db, User, UserRole, ProfessorProfile, StudentProfile, 
                   Module, Classe, TeachingAssignment, StudentAbsence, ProfessorAbsence)
from utils.decorators import professor_required, check_first_login

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')


@professor_bp.route('/dashboard')
@login_required
@professor_required
@check_first_login
def dashboard():
    """Professor Dashboard"""
    professor = current_user.professor_profile
    
    if not professor:
        flash('Profil professeur non trouvé.', 'danger')
        return redirect(url_for('main.landing'))
    
    # Get teaching assignments
    assignments = professor.teaching_assignments
    modules_taught = list(set([a.module for a in assignments]))
    classes_taught = list(set([a.classe for a in assignments if a.classe]))
    
    # Get own absences
    own_absences = ProfessorAbsence.query.filter_by(
        professor_id=professor.id
    ).order_by(ProfessorAbsence.date.desc()).limit(10).all()
    
    total_absence_hours = professor.get_total_absence_hours()
    
    # Stats
    stats = {
        'total_modules': len(modules_taught),
        'total_classes': len(classes_taught),
        'total_students': sum([c.student_count for c in classes_taught]),
        'my_absences': total_absence_hours
    }
    
    return render_template('professor/dashboard.html',
                          professor=professor,
                          stats=stats,
                          modules=modules_taught,
                          classes=classes_taught,
                          own_absences=own_absences)


@professor_bp.route('/my-absences')
@login_required
@professor_required
@check_first_login
def my_absences():
    """View professor's own absences"""
    professor = current_user.professor_profile
    
    page = request.args.get('page', 1, type=int)
    
    absences = ProfessorAbsence.query.filter_by(
        professor_id=professor.id
    ).order_by(ProfessorAbsence.date.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    total_hours = professor.get_total_absence_hours()
    
    return render_template('professor/my_absences.html',
                          absences=absences,
                          total_hours=total_hours)


@professor_bp.route('/my-modules')
@login_required
@professor_required
@check_first_login
def my_modules():
    """View modules taught by professor"""
    professor = current_user.professor_profile
    
    assignments = professor.teaching_assignments
    
    # Group by module
    module_data = {}
    for assignment in assignments:
        module = assignment.module
        if module.id not in module_data:
            module_data[module.id] = {
                'module': module,
                'classes': [],
                'total_students': 0
            }
        if assignment.classe:
            module_data[module.id]['classes'].append(assignment.classe)
            module_data[module.id]['total_students'] += assignment.classe.student_count
    
    return render_template('professor/my_modules.html',
                          module_data=module_data.values())


@professor_bp.route('/my-classes')
@login_required
@professor_required
@check_first_login
def my_classes():
    """View classes taught by professor"""
    professor = current_user.professor_profile
    
    assignments = professor.teaching_assignments
    
    # Group by class
    class_data = {}
    for assignment in assignments:
        if assignment.classe:
            classe = assignment.classe
            if classe.id not in class_data:
                class_data[classe.id] = {
                    'classe': classe,
                    'modules': [],
                    'students': classe.students
                }
            class_data[classe.id]['modules'].append(assignment.module)
    
    return render_template('professor/my_classes.html',
                          class_data=class_data.values())


@professor_bp.route('/class/<int:class_id>/students')
@login_required
@professor_required
@check_first_login
def class_students(class_id):
    """View students in a class"""
    professor = current_user.professor_profile
    
    # Verify professor teaches this class
    assignment = TeachingAssignment.query.filter_by(
        professor_id=professor.id,
        class_id=class_id
    ).first()
    
    if not assignment:
        flash('Vous n\'enseignez pas dans cette classe.', 'danger')
        return redirect(url_for('professor.my_classes'))
    
    classe = Classe.query.get_or_404(class_id)
    students = classe.students
    
    # Get modules taught by this professor in this class
    modules = [a.module for a in professor.teaching_assignments if a.class_id == class_id]
    
    # Calculate absence stats for each student
    student_stats = []
    for student in students:
        stats = {
            'student': student,
            'modules': []
        }
        for module in modules:
            total_hours = student.get_total_absence_hours(module.id)
            rate = student.get_absence_rate(module.id)
            status = student.check_threshold_status(module.id)
            stats['modules'].append({
                'module': module,
                'hours': total_hours,
                'rate': rate,
                'status': status
            })
        student_stats.append(stats)
    
    return render_template('professor/class_students.html',
                          classe=classe,
                          student_stats=student_stats,
                          modules=modules)


@professor_bp.route('/module/<int:module_id>/students')
@login_required
@professor_required
@check_first_login
def module_students(module_id):
    """View students enrolled in a module"""
    professor = current_user.professor_profile
    
    # Verify professor teaches this module
    assignment = TeachingAssignment.query.filter_by(
        professor_id=professor.id,
        module_id=module_id
    ).first()
    
    if not assignment:
        flash('Vous n\'enseignez pas ce module.', 'danger')
        return redirect(url_for('professor.my_modules'))
    
    module = Module.query.get_or_404(module_id)
    
    # Get all classes where this professor teaches this module
    class_ids = [a.class_id for a in professor.teaching_assignments 
                 if a.module_id == module_id and a.class_id]
    
    # Get all students in those classes
    students = StudentProfile.query.filter(
        StudentProfile.class_id.in_(class_ids)
    ).all() if class_ids else []
    
    # Calculate absence stats for each student
    student_stats = []
    for student in students:
        total_hours = student.get_total_absence_hours(module_id)
        rate = student.get_absence_rate(module_id)
        status = student.check_threshold_status(module_id)
        student_stats.append({
            'student': student,
            'hours': total_hours,
            'rate': rate,
            'status': status
        })
    
    # Sort by absence rate (highest first)
    student_stats.sort(key=lambda x: x['rate'], reverse=True)
    
    return render_template('professor/module_students.html',
                          module=module,
                          student_stats=student_stats)


@professor_bp.route('/student/<int:student_id>')
@login_required
@professor_required
@check_first_login
def view_student(student_id):
    """View student details (only for students in professor's classes)"""
    professor = current_user.professor_profile
    
    student = StudentProfile.query.get_or_404(student_id)
    
    # Verify professor teaches this student
    class_ids = [a.class_id for a in professor.teaching_assignments if a.class_id]
    if student.class_id not in class_ids:
        flash('Vous n\'enseignez pas à cet étudiant.', 'danger')
        return redirect(url_for('professor.dashboard'))
    
    # Get modules taught by this professor to this student
    modules = [a.module for a in professor.teaching_assignments 
               if a.class_id == student.class_id]
    
    # Calculate absence stats
    absence_stats = []
    for module in modules:
        total_hours = student.get_total_absence_hours(module.id)
        rate = student.get_absence_rate(module.id)
        status = student.check_threshold_status(module.id)
        absences = StudentAbsence.query.filter_by(
            student_id=student.id,
            module_id=module.id
        ).order_by(StudentAbsence.date.desc()).all()
        
        absence_stats.append({
            'module': module,
            'hours': total_hours,
            'rate': rate,
            'status': status,
            'absences': absences
        })
    
    return render_template('professor/view_student.html',
                          student=student,
                          absence_stats=absence_stats)
