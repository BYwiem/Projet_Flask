# routes/student.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import (db, User, UserRole, StudentProfile, Module, 
                   StudentAbsence, Major, MajorModule)
from utils.decorators import student_required, check_first_login

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@student_required
@check_first_login
def dashboard():
    """Student Dashboard"""
    student = current_user.student_profile
    
    if not student:
        flash('Profil étudiant non trouvé.', 'danger')
        return redirect(url_for('main.landing'))
    
    # Get absence stats
    absences = StudentAbsence.query.filter_by(
        student_id=student.id
    ).order_by(StudentAbsence.date.desc()).all()
    
    total_absence_hours = sum([a.hours for a in absences])
    
    # Get modules with absence info
    module_stats = []
    module_ids = set([a.module_id for a in absences])
    
    # Also get modules from major if enrolled
    if student.major:
        major_modules = MajorModule.query.filter_by(
            major_id=student.major_id,
            semester=student.current_semester
        ).all()
        for mm in major_modules:
            module_ids.add(mm.module_id)
    
    for module_id in module_ids:
        module = Module.query.get(module_id)
        if module:
            total_hours = student.get_total_absence_hours(module_id)
            rate = student.get_absence_rate(module_id)
            status = student.check_threshold_status(module_id)
            module_stats.append({
                'module': module,
                'hours': total_hours,
                'rate': rate,
                'status': status
            })
    
    # Sort by rate (highest first)
    module_stats.sort(key=lambda x: x['rate'], reverse=True)
    
    # Calculate average threshold and rate
    if module_stats:
        avg_rate = sum(m['rate'] for m in module_stats) / len(module_stats)
        avg_threshold = sum(m['module'].absence_threshold for m in module_stats) / len(module_stats)
    else:
        avg_rate = 0
        avg_threshold = 10
    
    remaining_hours = max(0, avg_threshold - total_absence_hours)
    
    # Stats summary
    stats = {
        'total_modules': len(module_stats),
        'total_absence_hours': total_absence_hours,
        'threshold': avg_threshold,
        'absence_rate': round(avg_rate, 1),
        'remaining_hours': round(remaining_hours, 1),
        'warnings': sum(1 for m in module_stats if m['status'] == 'warning'),
        'exceeded': sum(1 for m in module_stats if m['status'] == 'exceeded')
    }
    
    # Generate alerts
    alerts = []
    for m in module_stats:
        if m['status'] == 'exceeded':
            alerts.append(f"Seuil dépassé pour {m['module'].name}: {m['hours']}h / {m['module'].absence_threshold}h")
        elif m['status'] == 'warning':
            alerts.append(f"Attention: {m['module'].name} - {m['hours']}h / {m['module'].absence_threshold}h ({round(m['rate'], 1)}%)")
    
    # Recent absences
    recent_absences = absences[:5]
    
    return render_template('student/dashboard.html',
                          student=student,
                          student_profile=student,
                          stats=stats,
                          module_stats=module_stats[:5],  # Top 5 by absence rate
                          recent_absences=recent_absences,
                          alerts=alerts[:5])


@student_bp.route('/my-absences')
@login_required
@student_required
@check_first_login
def my_absences():
    """View student's absences"""
    student = current_user.student_profile
    
    page = request.args.get('page', 1, type=int)
    module_filter = request.args.get('module_id', 0, type=int)
    
    query = StudentAbsence.query.filter_by(student_id=student.id)
    
    if module_filter:
        query = query.filter_by(module_id=module_filter)
    
    absences = query.order_by(StudentAbsence.date.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20)
    )
    
    # Get modules for filter dropdown
    module_ids = db.session.query(StudentAbsence.module_id).filter_by(
        student_id=student.id
    ).distinct().all()
    modules = Module.query.filter(Module.id.in_([m[0] for m in module_ids])).all()
    
    # Calculate stats for summary cards
    all_absences = StudentAbsence.query.filter_by(student_id=student.id).all()
    total_hours = sum([a.hours for a in all_absences])
    total_count = len(all_absences)
    justified_count = sum(1 for a in all_absences if a.is_justified)
    
    # Calculate global rate (average across all modules)
    if modules:
        rates = [student.get_absence_rate(m.id) for m in modules]
        global_rate = round(sum(rates) / len(rates), 1) if rates else 0
    else:
        global_rate = 0
    
    return render_template('student/my_absences.html',
                          absences=absences,
                          modules=modules,
                          module_filter=module_filter,
                          total_hours=total_hours,
                          global_rate=global_rate,
                          total_count=total_count,
                          justified_count=justified_count)


@student_bp.route('/my-modules')
@login_required
@student_required
@check_first_login
def my_modules():
    """View student's modules with absence rates"""
    student = current_user.student_profile
    
    # Get all modules with absences
    module_stats = []
    
    # Get modules from absences
    absence_module_ids = db.session.query(StudentAbsence.module_id).filter_by(
        student_id=student.id
    ).distinct().all()
    module_ids = set([m[0] for m in absence_module_ids])
    
    # Add modules from major curriculum
    if student.major:
        major_modules = MajorModule.query.filter_by(
            major_id=student.major_id
        ).filter(MajorModule.semester <= student.current_semester).all()
        for mm in major_modules:
            module_ids.add(mm.module_id)
    
    for module_id in module_ids:
        module = Module.query.get(module_id)
        if module:
            total_hours = student.get_total_absence_hours(module_id)
            rate = student.get_absence_rate(module_id)
            status = student.check_threshold_status(module_id)
            
            # Get recent absences for this module
            recent = StudentAbsence.query.filter_by(
                student_id=student.id,
                module_id=module_id
            ).order_by(StudentAbsence.date.desc()).limit(3).all()
            
            module_stats.append({
                'module': module,
                'hours': total_hours,
                'rate': rate,
                'status': status,
                'recent_absences': recent
            })
    
    # Sort by name
    module_stats.sort(key=lambda x: x['module'].name)
    
    return render_template('student/my_modules.html',
                          module_stats=module_stats,
                          student=student)


@student_bp.route('/module/<int:module_id>')
@login_required
@student_required
@check_first_login
def module_detail(module_id):
    """View detailed absence info for a specific module"""
    student = current_user.student_profile
    module = Module.query.get_or_404(module_id)
    
    # Get all absences for this module
    absences = StudentAbsence.query.filter_by(
        student_id=student.id,
        module_id=module_id
    ).order_by(StudentAbsence.date.desc()).all()
    
    total_hours = student.get_total_absence_hours(module_id)
    rate = student.get_absence_rate(module_id)
    status = student.check_threshold_status(module_id)
    
    remaining_hours = max(0, module.absence_threshold - total_hours)
    
    return render_template('student/module_detail.html',
                          module=module,
                          absences=absences,
                          total_hours=total_hours,
                          rate=rate,
                          status=status,
                          remaining_hours=remaining_hours)


@student_bp.route('/academic-info')
@login_required
@student_required
@check_first_login
def academic_info():
    """View student's academic information"""
    student = current_user.student_profile
    
    # Get major info
    major = student.major
    
    # Get current semester modules
    current_modules = []
    if major:
        major_modules = MajorModule.query.filter_by(
            major_id=major.id,
            semester=student.current_semester
        ).all()
        current_modules = [mm.module for mm in major_modules]
    
    # Get class info
    classe = student.classe
    classmates = []
    if classe:
        classmates = [s for s in classe.students if s.id != student.id]
    
    return render_template('student/academic_info.html',
                          student=student,
                          major=major,
                          current_modules=current_modules,
                          classe=classe,
                          classmates_count=len(classmates))
