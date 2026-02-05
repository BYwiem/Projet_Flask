# 🎓 Gestion Scolaire - School Management System

A comprehensive Flask-based school management application for tracking student and professor absences, managing classes, modules, and academic information.

## 📋 Features

- **Multi-role Authentication**: Super Admin, Admin Staff, Professor, Student
- **Absence Management**: Track and manage student/professor absences
- **Threshold Alerts**: Automatic warnings when absence thresholds are exceeded
- **Academic Management**: Classes, Modules, Majors, Teaching Assignments
- **Dashboard**: Role-specific dashboards with statistics
- **Profile Management**: User profile editing with photo upload

## 🚀 Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to: `http://127.0.0.1:5000`

## 👤 Test Accounts

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@gestionscol.tn | admin123 |
| Admin Staff | admin@test.com | Test1234 |
| Professor | professeur@test.com | Test1234 |
| Student | etudiant@test.com | Test1234 |

## 📁 Project Structure

```
├── app.py              # Application entry point
├── config.py           # Configuration settings
├── models.py           # Database models
├── forms.py            # WTForms definitions
├── requirements.txt    # Python dependencies
├── scol.db            # SQLite database
├── routes/            # Blueprint routes
│   ├── admin.py       # Admin routes
│   ├── auth.py        # Authentication routes
│   ├── main.py        # Main routes
│   ├── professor.py   # Professor routes
│   ├── student.py     # Student routes
│   └── api.py         # REST API routes
├── templates/         # Jinja2 templates
├── static/            # Static files (CSS, JS, images)
└── utils/             # Utility functions
```

## 🛠️ Technologies Used

- **Backend**: Flask 3.0, SQLAlchemy, Flask-Login
- **Frontend**: Bootstrap 5, Font Awesome
- **Database**: SQLite
- **Authentication**: Flask-Login with password hashing


