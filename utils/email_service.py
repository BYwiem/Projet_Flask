# utils/email_service.py
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from threading import Thread
from datetime import datetime

mail = Mail()


class EmailService:
    """Service for sending email notifications"""
    
    @staticmethod
    def init_app(app):
        """Initialize the mail extension with the app"""
        mail.init_app(app)
    
    @staticmethod
    def send_async_email(app, msg):
        """Send email asynchronously"""
        with app.app_context():
            try:
                mail.send(msg)
            except Exception as e:
                current_app.logger.error(f"Failed to send email: {str(e)}")
    
    @staticmethod
    def send_email(subject, recipients, body, html_body=None, async_mode=True):
        """
        Send an email
        
        Args:
            subject: Email subject
            recipients: List of recipient email addresses
            body: Plain text body
            html_body: Optional HTML body
            async_mode: Whether to send asynchronously (default True)
        """
        app = current_app._get_current_object()
        
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients],
            body=body,
            html=html_body,
            sender=app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        if async_mode:
            thread = Thread(target=EmailService.send_async_email, args=(app, msg))
            thread.start()
            return thread
        else:
            mail.send(msg)
            return None
    
    @staticmethod
    def send_welcome_email(user, initial_password):
        """Send welcome email with initial credentials"""
        subject = f"Bienvenue sur {current_app.config.get('APP_NAME', 'Gestion Scolaire')}"
        
        body = f"""
Bonjour {user.full_name},

Bienvenue sur la plateforme de gestion scolaire!

Voici vos identifiants de connexion:
- Email: {user.email}
- Mot de passe temporaire: {initial_password}

Veuillez vous connecter et changer votre mot de passe lors de votre première connexion.

Cordialement,
L'équipe administrative
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #0d6efd; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .credentials {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        .warning {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bienvenue!</h1>
        </div>
        <div class="content">
            <p>Bonjour <strong>{user.full_name}</strong>,</p>
            <p>Bienvenue sur la plateforme de gestion scolaire!</p>
            
            <div class="credentials">
                <h3>Vos identifiants de connexion:</h3>
                <p><strong>Email:</strong> {user.email}</p>
                <p><strong>Mot de passe temporaire:</strong> {initial_password}</p>
            </div>
            
            <p class="warning">⚠️ Veuillez changer votre mot de passe lors de votre première connexion.</p>
            
            <p>Cordialement,<br>L'équipe administrative</p>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} Gestion Scolaire - Tous droits réservés</p>
        </div>
    </div>
</body>
</html>
        """
        
        return EmailService.send_email(subject, user.email, body, html_body)
    
    @staticmethod
    def send_threshold_warning(user, module_name, current_hours, threshold_hours, percentage):
        """Send warning when 50% of absence threshold is reached"""
        subject = f"⚠️ Alerte Absence - {percentage}% du seuil atteint"
        
        body = f"""
Bonjour {user.full_name},

Ceci est une notification automatique concernant vos absences.

Module: {module_name}
Heures d'absence actuelles: {current_hours}h
Seuil maximum: {threshold_hours}h
Pourcentage atteint: {percentage}%

Vous avez atteint {percentage}% de votre quota d'absences autorisées pour ce module.
Veuillez être vigilant(e) et éviter d'autres absences.

Cordialement,
L'équipe administrative
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #ffc107; color: #333; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .stats {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .progress {{ background-color: #e9ecef; border-radius: 10px; height: 20px; overflow: hidden; }}
        .progress-bar {{ background-color: #ffc107; height: 100%; width: {percentage}%; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Alerte Absence</h1>
        </div>
        <div class="content">
            <p>Bonjour <strong>{user.full_name}</strong>,</p>
            <p>Ceci est une notification automatique concernant vos absences.</p>
            
            <div class="stats">
                <h3>📚 Module: {module_name}</h3>
                <p><strong>Heures d'absence:</strong> {current_hours}h / {threshold_hours}h</p>
                <p><strong>Pourcentage atteint:</strong> {percentage}%</p>
                <div class="progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
            
            <p>⚠️ <strong>Attention:</strong> Vous avez atteint {percentage}% de votre quota d'absences autorisées.</p>
            <p>Veuillez être vigilant(e) et éviter d'autres absences non justifiées.</p>
            
            <p>Cordialement,<br>L'équipe administrative</p>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} Gestion Scolaire - Notification automatique</p>
        </div>
    </div>
</body>
</html>
        """
        
        return EmailService.send_email(subject, user.email, body, html_body)
    
    @staticmethod
    def send_threshold_exceeded(user, module_name, current_hours, threshold_hours):
        """Send notification when absence threshold is exceeded"""
        subject = f"🚨 URGENT - Seuil d'absence dépassé pour {module_name}"
        
        body = f"""
Bonjour {user.full_name},

ATTENTION: Vous avez dépassé le seuil d'absences autorisées.

Module: {module_name}
Heures d'absence: {current_hours}h
Seuil maximum: {threshold_hours}h
Dépassement: {current_hours - threshold_hours}h

Le dépassement du seuil d'absences peut entraîner des conséquences académiques.
Veuillez contacter l'administration dans les plus brefs délais.

Cordialement,
L'équipe administrative
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .stats {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }}
        .alert {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 SEUIL DÉPASSÉ</h1>
        </div>
        <div class="content">
            <p>Bonjour <strong>{user.full_name}</strong>,</p>
            
            <div class="alert">
                <strong>⚠️ ATTENTION:</strong> Vous avez dépassé le seuil d'absences autorisées!
            </div>
            
            <div class="stats">
                <h3>📚 Module: {module_name}</h3>
                <p><strong>Heures d'absence:</strong> {current_hours}h</p>
                <p><strong>Seuil maximum:</strong> {threshold_hours}h</p>
                <p><strong>Dépassement:</strong> <span style="color: #dc3545; font-weight: bold;">+{current_hours - threshold_hours}h</span></p>
            </div>
            
            <p>🚨 <strong>Action requise:</strong> Veuillez contacter l'administration dans les plus brefs délais pour régulariser votre situation.</p>
            
            <p>Cordialement,<br>L'équipe administrative</p>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} Gestion Scolaire - Notification urgente</p>
        </div>
    </div>
</body>
</html>
        """
        
        return EmailService.send_email(subject, user.email, body, html_body)
    
    @staticmethod
    def send_password_reset_email(user, reset_token):
        """Send password reset email"""
        subject = "Réinitialisation de mot de passe"
        
        # In production, use url_for with _external=True
        reset_url = f"/auth/reset-password/{reset_token}"
        
        body = f"""
Bonjour {user.full_name},

Vous avez demandé une réinitialisation de votre mot de passe.

Cliquez sur le lien suivant pour réinitialiser votre mot de passe:
{reset_url}

Ce lien expire dans 1 heure.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Cordialement,
L'équipe administrative
        """
        
        return EmailService.send_email(subject, user.email, body)
