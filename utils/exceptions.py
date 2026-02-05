# utils/exceptions.py
from flask import jsonify


class AppException(Exception):
    """Base exception for the application"""
    
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['success'] = False
        rv['error'] = self.__class__.__name__
        rv['message'] = self.message
        return rv
    
    def to_response(self):
        response = jsonify(self.to_dict())
        response.status_code = self.status_code
        return response


class ValidationError(AppException):
    """Exception raised for validation errors"""
    
    def __init__(self, message, field=None, errors=None):
        super().__init__(message, status_code=400)
        self.field = field
        self.errors = errors or []
    
    def to_dict(self):
        rv = super().to_dict()
        if self.field:
            rv['field'] = self.field
        if self.errors:
            rv['errors'] = self.errors
        return rv


class AuthorizationError(AppException):
    """Exception raised for authorization errors"""
    
    def __init__(self, message="Vous n'avez pas les permissions nécessaires."):
        super().__init__(message, status_code=403)


class AuthenticationError(AppException):
    """Exception raised for authentication errors"""
    
    def __init__(self, message="Authentification requise."):
        super().__init__(message, status_code=401)


class NotFoundError(AppException):
    """Exception raised when a resource is not found"""
    
    def __init__(self, message="Ressource non trouvée.", resource_type=None, resource_id=None):
        super().__init__(message, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id
    
    def to_dict(self):
        rv = super().to_dict()
        if self.resource_type:
            rv['resource_type'] = self.resource_type
        if self.resource_id:
            rv['resource_id'] = self.resource_id
        return rv


class BusinessRuleError(AppException):
    """Exception raised for business rule violations"""
    
    def __init__(self, message, rule=None):
        super().__init__(message, status_code=422)
        self.rule = rule
    
    def to_dict(self):
        rv = super().to_dict()
        if self.rule:
            rv['rule'] = self.rule
        return rv


class ThresholdExceededError(BusinessRuleError):
    """Exception raised when an absence threshold is exceeded"""
    
    def __init__(self, message, current_hours=None, threshold_hours=None, module_name=None):
        super().__init__(message, rule='absence_threshold_exceeded')
        self.current_hours = current_hours
        self.threshold_hours = threshold_hours
        self.module_name = module_name
    
    def to_dict(self):
        rv = super().to_dict()
        if self.current_hours is not None:
            rv['current_hours'] = self.current_hours
        if self.threshold_hours is not None:
            rv['threshold_hours'] = self.threshold_hours
        if self.module_name:
            rv['module_name'] = self.module_name
        return rv


class DuplicateError(AppException):
    """Exception raised when a duplicate entry is detected"""
    
    def __init__(self, message="Cette entrée existe déjà.", field=None):
        super().__init__(message, status_code=409)
        self.field = field
    
    def to_dict(self):
        rv = super().to_dict()
        if self.field:
            rv['field'] = self.field
        return rv


class DatabaseError(AppException):
    """Exception raised for database errors"""
    
    def __init__(self, message="Erreur de base de données."):
        super().__init__(message, status_code=500)


class EmailError(AppException):
    """Exception raised for email sending errors"""
    
    def __init__(self, message="Erreur lors de l'envoi de l'email."):
        super().__init__(message, status_code=500)


def register_error_handlers(app):
    """Register custom error handlers with the Flask app"""
    
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        return error.to_response()
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            'success': False,
            'error': 'BadRequest',
            'message': 'Requête invalide.'
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentification requise.'
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'Accès refusé.'
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'success': False,
            'error': 'NotFound',
            'message': 'Ressource non trouvée.'
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'MethodNotAllowed',
            'message': 'Méthode non autorisée.'
        }), 405
    
    @app.errorhandler(422)
    def handle_unprocessable(error):
        return jsonify({
            'success': False,
            'error': 'UnprocessableEntity',
            'message': 'Données non traitables.'
        }), 422
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        return jsonify({
            'success': False,
            'error': 'TooManyRequests',
            'message': 'Trop de requêtes. Veuillez réessayer plus tard.'
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return jsonify({
            'success': False,
            'error': 'InternalServerError',
            'message': 'Erreur interne du serveur.'
        }), 500
