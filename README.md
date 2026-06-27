# 🏥 MediCore — Hospital Management System

A full-featured hospital management system built with Django. MediCore allows hospital staff to manage patients, doctors, appointments, and billing — all from a clean, professional dashboard with role-based access control.

## ✨ Features

- **Secure Login** — Django authentication with role-based access control
- **Patient Management** — Add, edit, soft-delete patients with trash/restore functionality
- **Doctor Management** — Register and manage doctors with specializations
- **Appointment Scheduling** — Create and track appointments with status badges (Scheduled, Completed, Cancelled)
- **Billing System** — Create bills, record payments, track balance automatically
- **PDF Invoice Generation** — Download professional invoices via ReportLab
- **Dashboard** — Real-time stats for patients, doctors, appointments and unpaid bills
- **Bootstrap 5 UI** — Clean dark navy sidebar with responsive layout

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, Django 4.2 |
| Database | SQLite (development) |
| Frontend | Bootstrap 5, HTML, CSS |
| PDF Generation | ReportLab |
| Auth | Django built-in + Group-based RBAC |
| Config | python-decouple (.env) |

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/FurqanAthar28/medicore.git
cd medicore
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install django reportlab python-decouple
```

### 4. Create `.env` file
```
SECRET_KEY=your-secret-key-here
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create superuser
```bash
python manage.py createsuperuser
```

### 7. Run the server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

## 📁 Project Structure

```
medicore/
├── core/                  # Project settings and URLs
│   ├── settings.py
│   └── urls.py
├── patients/              # Main app
│   ├── models.py          # Patient, Doctor, Appointment, Bill, Payment
│   ├── views.py           # All views including PDF generation
│   ├── forms.py           # ModelForms with Bootstrap styling
│   ├── urls.py            # App URLs
│   └── admin.py
├── templates/
│   ├── base.html          # Dark navy sidebar layout
│   ├── login.html
│   ├── dashboard/
│   │   └── admin_dashboard.html
│   └── patients/          # All patient, doctor, appointment, bill templates
├── .env                   # Environment variables (not committed)
├── .gitignore
└── manage.py
```

## 🔐 Role-Based Access

- **Admin/Superuser** — Full access to all features including registering doctors
- **Staff** — Can manage patients, appointments and billing

## 👨‍💻 Author

**Furqan Athar**
- GitHub: https://github.com/FurqanAthar28
- LinkedIn: https://www.linkedin.com/in/furqan-athar-a0090a207
