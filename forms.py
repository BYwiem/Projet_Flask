# forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, EmailField, DateField, 
                     FloatField, TextAreaField, IntegerField, SelectField,
                     SubmitField, BooleanField, HiddenField, SelectMultipleField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo, 
                                 NumberRange, Optional, Regexp, ValidationError)
from wtforms.widgets import ListWidget, CheckboxInput
from datetime import date, timedelta


# ==================== CONSTANTS ====================
GOVERNORATES = [
    ('', '-- Sélectionner --'),
    ('Tunis', 'Tunis'),
    ('Ariana', 'Ariana'),
    ('Ben Arous', 'Ben Arous'),
    ('Manouba', 'Manouba'),
    ('Nabeul', 'Nabeul'),
    ('Zaghouan', 'Zaghouan'),
    ('Bizerte', 'Bizerte'),
    ('Béja', 'Béja'),
    ('Jendouba', 'Jendouba'),
    ('Le Kef', 'Le Kef'),
    ('Siliana', 'Siliana'),
    ('Sousse', 'Sousse'),
    ('Monastir', 'Monastir'),
    ('Mahdia', 'Mahdia'),
    ('Sfax', 'Sfax'),
    ('Kairouan', 'Kairouan'),
    ('Kasserine', 'Kasserine'),
    ('Sidi Bouzid', 'Sidi Bouzid'),
    ('Gabès', 'Gabès'),
    ('Médenine', 'Médenine'),
    ('Tataouine', 'Tataouine'),
    ('Gafsa', 'Gafsa'),
    ('Tozeur', 'Tozeur'),
    ('Kébili', 'Kébili'),
]


# ==================== CUSTOM VALIDATORS ====================
def validate_age_18(form, field):
    """Validate that the person is at least 18 years old"""
    if field.data:
        today = date.today()
        age = today.year - field.data.year - ((today.month, today.day) < (field.data.month, field.data.day))
        if age < 18:
            raise ValidationError('La personne doit avoir au moins 18 ans.')


def validate_future_date(form, field):
    """Validate that the date is not in the future"""
    if field.data and field.data > date.today():
        raise ValidationError('La date ne peut pas être dans le futur.')


# ==================== AUTHENTICATION FORMS ====================
class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Format d'email invalide")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis")
    ])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Mot de passe actuel', validators=[
        DataRequired(message="Le mot de passe actuel est requis")
    ])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(message="Le nouveau mot de passe est requis"),
        Length(min=8, message="Le mot de passe doit contenir au moins 8 caractères")
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message="Confirmez le mot de passe"),
        EqualTo('new_password', message="Les mots de passe ne correspondent pas")
    ])
    submit = SubmitField('Changer le mot de passe')


class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Format d'email invalide")
    ])
    submit = SubmitField('Réinitialiser le mot de passe')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis"),
        Length(min=8, message="Le mot de passe doit contenir au moins 8 caractères")
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message="Confirmez le mot de passe"),
        EqualTo('password', message="Les mots de passe ne correspondent pas")
    ])
    submit = SubmitField('Réinitialiser')


# ==================== USER CREATION FORMS ====================
class CreateStudentForm(FlaskForm):
    # Account Info
    email = EmailField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Format d'email invalide")
    ])
    
    # Profile Info
    student_id = StringField('Numéro Étudiant (NCE)', validators=[
        DataRequired(message="Le numéro étudiant est requis"),
        Length(max=20),
        Regexp(r'^[a-zA-Z0-9]+$', message="Le NCE ne doit contenir que des lettres et chiffres")
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(max=100),
        Regexp(r'^[a-zA-ZÀ-ÿ\s\-]+$', message="Le prénom ne doit contenir que des lettres")
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100),
        Regexp(r'^[a-zA-ZÀ-ÿ\s\-]+$', message="Le nom ne doit contenir que des lettres")
    ])
    date_of_birth = DateField('Date de naissance', validators=[
        DataRequired(message="La date de naissance est requise"),
        validate_age_18
    ], format='%Y-%m-%d')
    place_of_birth = SelectField('Lieu de naissance', choices=GOVERNORATES, validators=[
        DataRequired(message="Le lieu de naissance est requis")
    ])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    address = StringField('Adresse', validators=[Optional(), Length(max=255)])
    
    # Academic Info
    major_id = SelectField('Filière', coerce=int, validators=[Optional()])
    current_semester = IntegerField('Semestre actuel', default=1, validators=[
        NumberRange(min=1, max=12, message="Semestre invalide")
    ])
    class_id = SelectField('Classe', coerce=int, validators=[Optional()])
    
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images seulement!')
    ])
    
    submit = SubmitField('Créer l\'étudiant')


class CreateProfessorForm(FlaskForm):
    # Account Info
    email = EmailField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Format d'email invalide")
    ])
    
    # Profile Info
    employee_id = StringField('Matricule', validators=[
        DataRequired(message="Le matricule est requis"),
        Length(max=20),
        Regexp(r'^[a-zA-Z0-9]+$', message="Le matricule ne doit contenir que des lettres et chiffres")
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(max=100)
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100)
    ])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    office = StringField('Bureau', validators=[Optional(), Length(max=50)])
    department = StringField('Département', validators=[Optional(), Length(max=100)])
    specialization = StringField('Spécialisation', validators=[Optional(), Length(max=200)])
    hire_date = DateField('Date d\'embauche', validators=[Optional()], format='%Y-%m-%d')
    
    # Multi-select for modules - populated dynamically
    modules = SelectMultipleField('Modules enseignés', coerce=int, validators=[Optional()])
    
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images seulement!')
    ])
    
    submit = SubmitField('Créer le professeur')


class CreateStaffForm(FlaskForm):
    # Account Info
    email = EmailField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Format d'email invalide")
    ])
    
    # Profile Info
    employee_id = StringField('Matricule', validators=[
        DataRequired(message="Le matricule est requis"),
        Length(max=20),
        Regexp(r'^[a-zA-Z0-9]+$', message="Le matricule ne doit contenir que des lettres et chiffres")
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(max=100)
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100)
    ])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    office = StringField('Bureau', validators=[Optional(), Length(max=50)])
    department = StringField('Département', validators=[Optional(), Length(max=100)])
    position = StringField('Poste', validators=[Optional(), Length(max=100)])
    hire_date = DateField('Date d\'embauche', validators=[Optional()], format='%Y-%m-%d')
    
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images seulement!')
    ])
    
    submit = SubmitField('Créer le personnel')


# ==================== PROFILE UPDATE FORMS ====================
class UpdateProfileForm(FlaskForm):
    first_name = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(max=100)
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100)
    ])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Date de naissance', validators=[Optional()])
    address = StringField('Adresse', validators=[Optional(), Length(max=255)])
    
    photo = FileField('Photo de profil', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images seulement!')
    ])
    
    submit = SubmitField('Mettre à jour')


# ==================== ACADEMIC FORMS ====================
class MajorForm(FlaskForm):
    code = StringField('Code', validators=[
        DataRequired(message="Le code est requis"),
        Length(max=20)
    ])
    name = StringField('Nom de la filière', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100)
    ])
    description = TextAreaField('Description', validators=[Optional()])
    total_semesters = IntegerField('Nombre de semestres', default=6, validators=[
        NumberRange(min=1, max=12, message="Nombre de semestres invalide")
    ])
    # Multi-select for modules - populated dynamically
    modules = SelectMultipleField('Modules associés', coerce=int, validators=[Optional()])
    # Multi-select for classes - populated dynamically
    classes = SelectMultipleField('Classes associées', coerce=int, validators=[Optional()])
    is_active = BooleanField('Actif', default=True)
    submit = SubmitField('Enregistrer')


class ModuleForm(FlaskForm):
    code = StringField('Code', validators=[
        DataRequired(message="Le code est requis"),
        Length(max=20)
    ])
    name = StringField('Intitulé du module', validators=[
        DataRequired(message="L'intitulé est requis"),
        Length(max=100)
    ])
    description = TextAreaField('Description', validators=[Optional()])
    total_hours = FloatField('Heures totales', default=42, validators=[
        NumberRange(min=1, message="Les heures doivent être supérieures à 0")
    ])
    absence_threshold_hours = IntegerField('Seuil d\'absence (heures)', default=10, validators=[
        NumberRange(min=0, message="Les heures doivent être >= 0")
    ])
    absence_threshold_minutes = IntegerField('Seuil d\'absence (minutes)', default=0, validators=[
        NumberRange(min=0, max=59, message="Les minutes doivent être entre 0 et 59")
    ])
    credits = IntegerField('Crédits', default=3, validators=[
        NumberRange(min=1, max=10, message="Crédits invalides")
    ])
    # Multi-select for majors and professors - populated dynamically
    majors = SelectMultipleField('Filières associées', coerce=int, validators=[Optional()])
    professors = SelectMultipleField('Professeurs enseignants', coerce=int, validators=[Optional()])
    is_active = BooleanField('Actif', default=True)
    submit = SubmitField('Enregistrer')


class ClasseForm(FlaskForm):
    code = StringField('Code Classe', validators=[
        DataRequired(message="Le code est requis"),
        Length(max=20)
    ])
    name = StringField('Nom de la Classe', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100)
    ])
    academic_year = StringField('Année académique', validators=[
        Optional(),
        Regexp(r'^\d{4}-\d{4}$', message="Format: YYYY-YYYY")
    ])
    semester = IntegerField('Semestre', default=1, validators=[
        NumberRange(min=1, max=12, message="Semestre invalide")
    ])
    max_students = IntegerField('Capacité maximale', default=30, validators=[
        NumberRange(min=1, message="La capacité doit être supérieure à 0")
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Enregistrer')


class TeachingAssignmentForm(FlaskForm):
    professor_id = SelectField('Professeur', coerce=int, validators=[
        DataRequired(message="Sélectionnez un professeur")
    ])
    module_id = SelectField('Module', coerce=int, validators=[
        DataRequired(message="Sélectionnez un module")
    ])
    class_id = SelectField('Classe', coerce=int, validators=[Optional()])
    academic_year = StringField('Année académique', validators=[
        Optional(),
        Regexp(r'^\d{4}-\d{4}$', message="Format: YYYY-YYYY")
    ])
    semester = IntegerField('Semestre', validators=[Optional()])
    submit = SubmitField('Assigner')


# ==================== ABSENCE FORMS ====================
class StudentAbsenceForm(FlaskForm):
    student_id = SelectField('Étudiant', coerce=int, validators=[
        DataRequired(message="Sélectionnez un étudiant")
    ])
    module_id = SelectField('Module', coerce=int, validators=[
        DataRequired(message="Sélectionnez un module")
    ])
    date = DateField('Date d\'absence', validators=[
        DataRequired(message="La date est requise"),
        validate_future_date
    ], format='%Y-%m-%d')
    hours = FloatField('Nombre d\'heures', validators=[
        DataRequired(message="Le nombre d'heures est requis"),
        NumberRange(min=0.5, max=12, message="Heures invalides (0.5 - 12)")
    ])
    reason = StringField('Motif', validators=[Optional(), Length(max=255)])
    is_justified = BooleanField('Justifiée')
    submit = SubmitField('Enregistrer')


class ProfessorAbsenceForm(FlaskForm):
    professor_id = SelectField('Professeur', coerce=int, validators=[
        DataRequired(message="Sélectionnez un professeur")
    ])
    date = DateField('Date d\'absence', validators=[
        DataRequired(message="La date est requise"),
        validate_future_date
    ], format='%Y-%m-%d')
    hours = FloatField('Nombre d\'heures', validators=[
        DataRequired(message="Le nombre d'heures est requis"),
        NumberRange(min=0.5, max=12, message="Heures invalides (0.5 - 12)")
    ])
    reason = StringField('Motif', validators=[Optional(), Length(max=255)])
    is_justified = BooleanField('Justifiée')
    submit = SubmitField('Enregistrer')


# ==================== THRESHOLD FORMS ====================
class ThresholdSettingForm(FlaskForm):
    setting_type = SelectField('Type de seuil', choices=[
        ('professor_global', 'Seuil global professeurs (jours/heures)')
    ], validators=[DataRequired()])
    threshold_days = IntegerField('Seuil (jours)', default=0, validators=[
        NumberRange(min=0, message="Les jours doivent être >= 0")
    ])
    threshold_hours = IntegerField('Seuil (heures)', default=0, validators=[
        NumberRange(min=0, max=23, message="Les heures doivent être entre 0 et 23")
    ])
    warning_percentage = FloatField('Pourcentage d\'alerte', default=50, validators=[
        NumberRange(min=10, max=100, message="Pourcentage invalide (10-100)")
    ])
    submit = SubmitField('Enregistrer')


# ==================== SEARCH/FILTER FORMS ====================
class SearchForm(FlaskForm):
    query = StringField('Rechercher', validators=[Optional()])
    submit = SubmitField('Rechercher')


class FilterStudentsForm(FlaskForm):
    class_id = SelectField('Classe', coerce=int, validators=[Optional()])
    major_id = SelectField('Filière', coerce=int, validators=[Optional()])
    semester = SelectField('Semestre', coerce=int, validators=[Optional()])
    submit = SubmitField('Filtrer')


class FilterAbsencesForm(FlaskForm):
    student_id = SelectField('Étudiant', coerce=int, validators=[Optional()])
    module_id = SelectField('Module', coerce=int, validators=[Optional()])
    date_from = DateField('Du', validators=[Optional()], format='%Y-%m-%d')
    date_to = DateField('Au', validators=[Optional()], format='%Y-%m-%d')
    is_justified = SelectField('Statut', choices=[
        ('', 'Tous'),
        ('1', 'Justifiée'),
        ('0', 'Non justifiée')
    ], validators=[Optional()])
    submit = SubmitField('Filtrer')


# ==================== LEGACY FORMS (backward compatibility) ====================
class EtudiantForm(FlaskForm):
    NCE = StringField('NCE (Numéro Carte Étudiant)', validators=[
        DataRequired(message="Le NCE est requis"),
        Length(max=20),
        Regexp(r'^[a-zA-Z0-9]+$', message="Le NCE ne doit contenir que des lettres et chiffres")
    ])
    Nom = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(max=100),
        Regexp(r'^[a-zA-ZÀ-ÿ\s\-]+$', message="Le nom ne doit contenir que des lettres")
    ])
    Prenom = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(max=100),
        Regexp(r'^[a-zA-ZÀ-ÿ\s\-]+$', message="Le prénom ne doit contenir que des lettres")
    ])
    DateNais = DateField('Date de Naissance', validators=[
        DataRequired(message="La date de naissance est requise"),
        validate_age_18
    ], format='%Y-%m-%d')
    LieuNais = SelectField('Lieu de Naissance', choices=GOVERNORATES, validators=[
        DataRequired(message="Le lieu de naissance est requis")
    ])
    CodClass = SelectField('Classe', validators=[DataRequired()])
    submit = SubmitField('Ajouter')


class MatiereForm(FlaskForm):
    CodMat = StringField('Code Matière', validators=[
        DataRequired(),
        Length(max=20)
    ])
    IntMat = StringField('Intitulé de la Matière', validators=[
        DataRequired(),
        Length(max=100)
    ])
    Description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Ajouter')


class AbsenceForm(FlaskForm):
    NCE = SelectField('Étudiant', validators=[
        DataRequired(message="Sélectionnez un étudiant")
    ])
    CodMat = SelectField('Matière', validators=[
        DataRequired(message="Sélectionnez une matière")
    ])
    DateA = DateField('Date d\'Absence', validators=[
        DataRequired(message="La date est requise")
    ], format='%Y-%m-%d')
    NHA = FloatField('Nombre d\'Heures', validators=[
        DataRequired(message="Le nombre d'heures est requis"),
        NumberRange(min=0.5, max=8, message="Entre 0.5 et 8 heures")
    ])
    submit = SubmitField('Enregistrer')
