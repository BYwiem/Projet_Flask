# utils/__init__.py
from .decorators import (
    login_required_with_role,
    super_admin_required,
    admin_required,
    professor_required,
    student_required,
    can_create_users,
    api_login_required,
    api_role_required,
    check_first_login
)
from .email_service import EmailService
from .exceptions import (
    AppException,
    ValidationError,
    AuthorizationError,
    NotFoundError,
    BusinessRuleError,
    ThresholdExceededError
)

__all__ = [
    'login_required_with_role',
    'super_admin_required',
    'admin_required',
    'professor_required',
    'student_required',
    'can_create_users',
    'api_login_required',
    'api_role_required',
    'check_first_login',
    'EmailService',
    'AppException',
    'ValidationError',
    'AuthorizationError',
    'NotFoundError',
    'BusinessRuleError',
    'ThresholdExceededError'
]
