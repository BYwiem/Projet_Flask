# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string

db = SQLAlchemy()


# ==================== ENUMS ====================
class UserRole:
    SUPER_ADMIN = 'super_admin'
    ADMIN_STAFF = 'admin_staff'
    PROFESSOR = 'professor'
    STUDENT = 'student'
    
    @classmethod
    def choices(cls):
        return [
            (cls.SUPER_ADMIN, 'Super Administrateur'),
            (cls.ADMIN_STAFF, 'Personnel Administratif'),
            (cls.PROFESSOR, 'Professeur'),
            (cls.STUDENT, 'Étudiant')
        ]
    
    @classmethod
    def all(cls):
        return [cls.SUPER_ADMIN, cls.ADMIN_STAFF, cls.PROFESSOR, cls.STUDENT]


# ==================== USER & AUTHENTICATION ====================
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    is_first_login = db.Column(db.Boolean, default=True)
    initial_password = db.Column(db.String(50), nullable=True)  # Stores initial password temporarily
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships to profiles
    student_profile = db.relationship('StudentProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    professor_profile = db.relationship('ProfessorProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    staff_profile = db.relationship('StaffProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    created_by = db.relationship('User', remote_side=[id], backref='created_users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def generate_initial_password(length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @property
    def profile(self):
        """Get the appropriate profile based on role"""
        if self.role == UserRole.STUDENT:
            return self.student_profile
        elif self.role == UserRole.PROFESSOR:
            return self.professor_profile
        elif self.role in [UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN]:
            return self.staff_profile
        return None
    
    @property
    def full_name(self):
        """Get full name from profile"""
        profile = self.profile
        if profile:
            return f"{profile.first_name} {profile.last_name}"
        return self.email
    
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN
    
    def is_admin_staff(self):
        return self.role == UserRole.ADMIN_STAFF
    
    def is_professor(self):
        return self.role == UserRole.PROFESSOR
    
    def is_student(self):
        return self.role == UserRole.STUDENT
    
    def can_create_users(self):
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF]
    
    def __str__(self):
        return f"{self.full_name} ({self.role})"
    
    def __repr__(self):
        return f'<User {self.email}>'


# ==================== USER PROFILES ====================
class StudentProfile(db.Model):
    __tablename__ = 'student_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    place_of_birth = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Academic info
    major_id = db.Column(db.Integer, db.ForeignKey('major.id'), nullable=True)
    current_semester = db.Column(db.Integer, default=1)
    class_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=True)
    enrollment_date = db.Column(db.Date, default=date.today)
    
    # Relationships
    user = db.relationship('User', back_populates='student_profile')
    major = db.relationship('Major', back_populates='students')
    classe = db.relationship('Classe', back_populates='students')
    absences = db.relationship('StudentAbsence', back_populates='student', cascade='all, delete-orphan')
    
    def get_total_absence_hours(self, module_id=None, count_justified=False):
        """Calculate total absence hours, optionally for a specific module
        By default, justified absences are NOT counted"""
        query = StudentAbsence.query.filter_by(student_id=self.id)
        if module_id:
            query = query.filter_by(module_id=module_id)
        if not count_justified:
            query = query.filter_by(is_justified=False)
        return sum(a.hours for a in query.all())
    
    def get_absence_rate(self, module_id):
        """Calculate absence rate as percentage of absence threshold"""
        module = Module.query.get(module_id)
        if not module or module.absence_threshold == 0:
            return 0
        total_absence = self.get_total_absence_hours(module_id)
        return (total_absence / module.absence_threshold) * 100
    
    def check_threshold_status(self, module_id):
        """Check threshold status: 'ok', 'warning' (50%), 'exceeded'"""
        module = Module.query.get(module_id)
        if not module:
            return 'ok'
        
        total_absence = self.get_total_absence_hours(module_id)
        threshold = module.absence_threshold
        
        if total_absence >= threshold:
            return 'exceeded'
        elif total_absence >= (threshold * 0.5):
            return 'warning'
        return 'ok'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<StudentProfile {self.student_id}>'


class ProfessorProfile(db.Model):
    __tablename__ = 'professor_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    office = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='professor_profile')
    absences = db.relationship('ProfessorAbsence', back_populates='professor', cascade='all, delete-orphan')
    teaching_assignments = db.relationship('TeachingAssignment', back_populates='professor', cascade='all, delete-orphan')
    
    def get_total_absence_hours(self, count_justified=False):
        """Calculate total absence hours
        By default, justified absences are NOT counted"""
        absences = self.absences
        if not count_justified:
            absences = [a for a in absences if not a.is_justified]
        return sum(a.hours for a in absences)
    
    def get_total_absence_days(self, count_justified=False):
        """Calculate total absence days (8 hours = 1 day)
        By default, justified absences are NOT counted"""
        hours = self.get_total_absence_hours(count_justified)
        return hours / 8
    
    def get_modules_taught(self):
        """Get list of modules this professor teaches"""
        return [ta.module for ta in self.teaching_assignments]
    
    def get_classes_taught(self):
        """Get list of classes this professor teaches"""
        return list(set([ta.classe for ta in self.teaching_assignments if ta.classe]))
    
    def __str__(self):
        return f"Prof. {self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<ProfessorProfile {self.employee_id}>'


class StaffProfile(db.Model):
    __tablename__ = 'staff_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    office = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='staff_profile')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<StaffProfile {self.employee_id}>'


# ==================== ACADEMIC STRUCTURE ====================
class Major(db.Model):
    """Filière / Spécialité"""
    __tablename__ = 'major'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_semesters = db.Column(db.Integer, default=6)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('StudentProfile', back_populates='major')
    modules = db.relationship('MajorModule', back_populates='major', cascade='all, delete-orphan')
    classes = db.relationship('Classe', back_populates='major')
    
    def get_modules_for_semester(self, semester):
        """Get modules for a specific semester"""
        return [mm.module for mm in self.modules if mm.semester == semester]
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f'<Major {self.code}>'


class Module(db.Model):
    """Course / Matière"""
    __tablename__ = 'module'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_hours = db.Column(db.Float, default=42)
    absence_threshold = db.Column(db.Float, default=10)
    credits = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    majors = db.relationship('MajorModule', back_populates='module', cascade='all, delete-orphan')
    teaching_assignments = db.relationship('TeachingAssignment', back_populates='module', cascade='all, delete-orphan')
    student_absences = db.relationship('StudentAbsence', back_populates='module', cascade='all, delete-orphan')
    
    def get_professors(self):
        """Get all professors teaching this module"""
        return [ta.professor for ta in self.teaching_assignments]
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f'<Module {self.code}>'


class MajorModule(db.Model):
    """Association table between Major and Module with semester info"""
    __tablename__ = 'major_module'
    
    id = db.Column(db.Integer, primary_key=True)
    major_id = db.Column(db.Integer, db.ForeignKey('major.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id', ondelete='CASCADE'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    
    major = db.relationship('Major', back_populates='modules')
    module = db.relationship('Module', back_populates='majors')
    
    __table_args__ = (
        db.UniqueConstraint('major_id', 'module_id', name='unique_major_module'),
    )


class Classe(db.Model):
    """Class / Section"""
    __tablename__ = 'classe'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(9), nullable=True)
    semester = db.Column(db.Integer, default=1)
    max_students = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    major_id = db.Column(db.Integer, db.ForeignKey('major.id'), nullable=True)
    
    # Relationships
    students = db.relationship('StudentProfile', back_populates='classe')
    teaching_assignments = db.relationship('TeachingAssignment', back_populates='classe', cascade='all, delete-orphan')
    major = db.relationship('Major', back_populates='classes')
    
    @property
    def student_count(self):
        return len(self.students)
    
    def get_professors(self):
        """Get all professors teaching this class"""
        return list(set([ta.professor for ta in self.teaching_assignments]))
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def __repr__(self):
        return f'<Classe {self.code}>'


class TeachingAssignment(db.Model):
    """Professor teaching a module to a class"""
    __tablename__ = 'teaching_assignment'
    
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professor_profile.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classe.id', ondelete='CASCADE'), nullable=True)
    academic_year = db.Column(db.String(9), nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    professor = db.relationship('ProfessorProfile', back_populates='teaching_assignments')
    module = db.relationship('Module', back_populates='teaching_assignments')
    classe = db.relationship('Classe', back_populates='teaching_assignments')
    
    __table_args__ = (
        db.UniqueConstraint('professor_id', 'module_id', 'class_id', 'academic_year', name='unique_teaching'),
    )


# ==================== ABSENCE MANAGEMENT ====================
class StudentAbsence(db.Model):
    """Student absence records"""
    __tablename__ = 'student_absence'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    hours = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    is_justified = db.Column(db.Boolean, default=False)
    justification_document = db.Column(db.String(200), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('StudentProfile', back_populates='absences')
    module = db.relationship('Module', back_populates='student_absences')
    recorded_by = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'module_id', 'date', name='unique_student_absence'),
    )
    
    def __str__(self):
        return f"{self.student} - {self.module} - {self.date}"
    
    def __repr__(self):
        return f'<StudentAbsence {self.id}>'


class ProfessorAbsence(db.Model):
    """Professor absence records"""
    __tablename__ = 'professor_absence'
    
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professor_profile.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    hours = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    is_justified = db.Column(db.Boolean, default=False)
    justification_document = db.Column(db.String(200), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    professor = db.relationship('ProfessorProfile', back_populates='absences')
    recorded_by = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('professor_id', 'date', name='unique_professor_absence'),
    )
    
    def __str__(self):
        return f"{self.professor} - {self.date}"
    
    def __repr__(self):
        return f'<ProfessorAbsence {self.id}>'


# ==================== THRESHOLD SETTINGS ====================
class ThresholdSetting(db.Model):
    """Global threshold settings for professors"""
    __tablename__ = 'threshold_setting'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_type = db.Column(db.String(20), nullable=False, default='professor_global')
    threshold_days = db.Column(db.Integer, default=0)  # For professors: global limit in days
    threshold_hours = db.Column(db.Integer, default=0)  # Additional hours
    warning_percentage = db.Column(db.Float, default=50)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    updated_by = db.relationship('User')
    
    def get_total_hours(self):
        """Get total threshold in hours (days * 8 + hours)"""
        return (self.threshold_days * 8) + self.threshold_hours


# ==================== NOTIFICATION LOGS ====================
class NotificationLog(db.Model):
    """Log of sent notifications"""
    __tablename__ = 'notification_log'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    recipient = db.relationship('User')
    
    def __repr__(self):
        return f'<NotificationLog {self.id}>'


# ==================== LEGACY COMPATIBILITY ====================
class Etudiant(db.Model):
    """Legacy student model - for migration"""
    __tablename__ = 'etudiant'
    
    NCE = db.Column(db.String(20), primary_key=True)
    Nom = db.Column(db.String(100), nullable=False)
    Prenom = db.Column(db.String(100), nullable=False)
    DateNais = db.Column(db.Date, nullable=True)
    LieuNais = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=True)
    updated_at = db.Column(db.TIMESTAMP, onupdate=db.func.now(), nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    CodClass = db.Column(db.String(20), nullable=True)
    
    def __str__(self):
        return f"{self.Nom} {self.Prenom}"


class Matiere(db.Model):
    """Legacy module model - for migration"""
    __tablename__ = 'matiere'
    
    CodMat = db.Column(db.String(20), primary_key=True)
    IntMat = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    
    def __str__(self):
        return self.IntMat


class Absence(db.Model):
    """Legacy absence model - for migration"""
    __tablename__ = 'absence'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CodMat = db.Column(db.String(20), nullable=False)
    NCE = db.Column(db.String(20), nullable=False)
    DateA = db.Column(db.Date, nullable=False, default=date.today)
    NHA = db.Column(db.Float, nullable=False)
    
    def __str__(self):
        return f"{self.NCE} - {self.CodMat} - {self.DateA}"
