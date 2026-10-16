# 🏥 MediCore – Hospital Management System

A modern Hospital Management System built with **Django** and **PostgreSQL** for managing patients, doctors, appointments, billing, and payments. The application is deployed on Railway and uses Neon PostgreSQL as the production database.

## 🌐 Live Demo

https://medicore-production-8796.up.railway.app

> **Admin Panel**
>
> https://medicore-production-8796.up.railway.app/admin/

---

# ✨ Features

### 👨‍⚕️ Doctor Management
- Register doctors (optionally with a portal login)
- Edit doctor information
- Doctor directory and doctor profile pages

### 🩺 Doctor Portal
- Personal dashboard: today's and upcoming appointments
- Search and select a patient, view full patient history
- Write prescriptions (start a consultation straight from an appointment)
- Send a prescription to the pharmacy

### 💊 Pharmacy
- Medicine inventory with stock, price, expiry and low-stock alerts
- Sell medicines to patients, or dispense a prescription
- Stock is deducted automatically and a bill is raised (pay now or later)

### 🧑‍🤝‍🧑 Patient Management
- Add patients
- Update patient records
- Soft delete & restore patients
- Patient listing

### 📅 Appointment Management
- Schedule appointments
- Update appointment status
- View appointments

### 💳 Billing System
- Generate bills
- Track paid amount
- Calculate remaining balance
- Bill status (Paid / Partial / Unpaid)

### 💰 Payment Management
- Record payments
- Payment history
- Multiple payment methods

### 📄 PDF Generation
- Download printable invoices
- Professional PDF bills using ReportLab

### 🔐 Authentication
- Django Admin authentication
- Secure login
- Session management

### ☁️ Deployment
- Railway hosting
- Neon PostgreSQL database
- WhiteNoise static file serving
- Gunicorn production server

---

# 🛠 Tech Stack

- Python 3
- Django 6
- PostgreSQL (Neon)
- Railway
- HTML5
- CSS3
- Bootstrap 5
- WhiteNoise
- Gunicorn
- ReportLab

---

# 📷 Screenshots

## Dashboard

![Dashboard](screenshots/dashboard.png)

---

## Patients

![Patients](screenshots/patients.png)

---

## Doctors

![Doctors](screenshots/doctors.png)

---

## Appointments

![Appointments](screenshots/appointments.png)

---

## Bills

![Bills](screenshots/bills.png)

---

## Payments

![Payments](screenshots/payments.png)

---

# 🚀 Local Installation

Clone the repository

```bash
git clone https://github.com/FurqanAthar28/medicore.git
cd medicore
```

Create virtual environment

```bash
python -m venv env
```

Activate environment

### Windows

```bash
env\Scripts\activate
```

### Linux / macOS

```bash
source env/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run migrations

```bash
python manage.py migrate
```

Create superuser

```bash
python manage.py createsuperuser
```

`migrate` also loads a starter list of 32 common medicines into the pharmacy
(sample prices; edit them from the Medicines page). If you delete them and want
them back, run:

```bash
python manage.py seed_medicines
```

Run server

```bash
python manage.py runserver
```

---

# ⚙️ Environment Variables

Create a `.env` file in the project root.

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=your_database_url
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

Optional variables:

```env
HOSPITAL_NAME=MediCore
CURRENCY_SYMBOL=Rs.
ADMIN_GROUP_NAME=Admin
PHARMACIST_GROUP_NAME=Pharmacist
DATABASE_SSL_REQUIRE=True
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
```

---

# 👥 User Roles

| Role | How to set up | Can do |
|------|---------------|--------|
| Admin | Superuser, or user in the `Admin` group | Everything, including managing doctors |
| Doctor | Register a doctor with a username/password | Doctor portal, prescriptions, own appointments, pharmacy sales |
| Pharmacist | User in the `Pharmacist` group | Manage medicine inventory |
| Staff | Any other logged-in user | Patients, appointments, billing, pharmacy sales |

Create the `Admin` and `Pharmacist` groups from the Django admin panel (`/admin/`).

---

# 📦 Deployment

This project is deployed using:

- Railway
- Neon PostgreSQL
- WhiteNoise
- Gunicorn

---

# 📁 Project Structure

```
core/
patients/
pharmacy/
templates/
static/
screenshots/
manage.py
requirements.txt
build.sh
README.md
```

---

# 👨‍💻 Author

**Furqan Athar**

GitHub:
https://github.com/FurqanAthar28

LinkedIn:
https://www.linkedin.com/in/furqan-athar/

---

# 📄 License

This project is intended for educational and portfolio purposes.
