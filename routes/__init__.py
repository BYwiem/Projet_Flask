# routes/__init__.py
from .auth import auth_bp
from .main import main_bp
from .admin import admin_bp
from .professor import professor_bp
from .student import student_bp
from .api import api_bp

__all__ = ['auth_bp', 'main_bp', 'admin_bp', 'professor_bp', 'student_bp', 'api_bp']
