# app.py
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from config import config
from models import db, User, UserRole

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure upload directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)
    os.makedirs(app.config.get('UPLOADED_PHOTOS_DEST', 'static/image'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes import auth_bp, main_bp, admin_bp, professor_bp, student_bp, api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        init_default_data()
    
    return app


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500


def init_default_data():
    """Initialize default data including super admin"""
    from models import (User, UserRole, StaffProfile, Major, Module, Classe, 
                       MajorModule, ProfessorProfile, StudentProfile, TeachingAssignment)
    
    # Create super admin if not exists
    if not User.query.filter_by(role=UserRole.SUPER_ADMIN).first():
        print("📦 Creating default super admin...")
        
        super_admin = User(
            email='admin@gestionscol.tn',
            role=UserRole.SUPER_ADMIN,
            is_first_login=False
        )
        super_admin.set_password('admin123')
        db.session.add(super_admin)
        db.session.flush()
        
        # Create admin profile
        admin_profile = StaffProfile(
            user_id=super_admin.id,
            employee_id='ADMIN001',
            first_name='Super',
            last_name='Admin',
            position='Administrateur Système'
        )
        db.session.add(admin_profile)
        db.session.commit()
        
        print("✅ Super admin created: admin@gestionscol.tn / admin123")
    
    # Create sample data if database is empty
    if not Major.query.first():
        print("📦 Creating sample academic data...")
        
        # Create Majors
        majors = [
            Major(code='GL', name='Génie Logiciel', total_semesters=6),
            Major(code='RT', name='Réseaux et Télécommunications', total_semesters=6),
            Major(code='IA', name='Intelligence Artificielle', total_semesters=4),
        ]
        for m in majors:
            db.session.add(m)
        db.session.flush()
        
        # Create Modules
        modules = [
            Module(code='PROG1', name='Programmation 1', total_hours=42, absence_threshold=10, credits=4),
            Module(code='PROG2', name='Programmation 2', total_hours=42, absence_threshold=10, credits=4),
            Module(code='BDD', name='Bases de Données', total_hours=36, absence_threshold=8, credits=3),
            Module(code='ALGO', name='Algorithmique', total_hours=48, absence_threshold=12, credits=4),
            Module(code='WEB', name='Développement Web', total_hours=42, absence_threshold=10, credits=3),
            Module(code='RESEAU', name='Réseaux Informatiques', total_hours=36, absence_threshold=8, credits=3),
            Module(code='MATH', name='Mathématiques', total_hours=48, absence_threshold=12, credits=4),
            Module(code='ANGLAIS', name='Anglais Technique', total_hours=24, absence_threshold=6, credits=2),
        ]
        for m in modules:
            db.session.add(m)
        db.session.flush()
        
        # Create Major-Module associations
        gl_major = Major.query.filter_by(code='GL').first()
        associations = [
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='PROG1').first().id, semester=1),
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='ALGO').first().id, semester=1),
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='MATH').first().id, semester=1),
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='PROG2').first().id, semester=2),
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='BDD').first().id, semester=2),
            MajorModule(major_id=gl_major.id, module_id=Module.query.filter_by(code='WEB').first().id, semester=3),
        ]
        for a in associations:
            db.session.add(a)
        
        # Create Classes
        classes = [
            Classe(code='GL1-A', name='Génie Logiciel 1ère année - Section A', academic_year='2025-2026', semester=1),
            Classe(code='GL1-B', name='Génie Logiciel 1ère année - Section B', academic_year='2025-2026', semester=1),
            Classe(code='GL2-A', name='Génie Logiciel 2ème année - Section A', academic_year='2025-2026', semester=3),
            Classe(code='RT1-A', name='Réseaux 1ère année - Section A', academic_year='2025-2026', semester=1),
        ]
        for c in classes:
            db.session.add(c)
        
        db.session.commit()
        print("✅ Sample academic data created!")
    
    print("✅ Application initialized successfully!")


# Create the application instance
app = create_app(os.environ.get('FLASK_CONFIG', 'development'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
