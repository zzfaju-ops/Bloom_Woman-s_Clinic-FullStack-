##Bloom Women's Clinic — Appointment & Cycle Tracker


A full-stack Flask web app for a single-doctor, female-patients-only practice. Patients can book and track appointments, view their medication and visit history, and log a monthly cycle and symptom tracker. The doctor (admin) has one login for the whole practice and can manage every patient's chart, schedule, and medications.


##Features


##Patient side
Register / login (/register, /login)
Dashboard with upcoming appointments, cycle prediction, and active medications
Request or cancel appointments (/appointments)
Full history: medications, visit notes, and follow-ups (/history)
Daily cycle and symptom log with period/flow/mood/symptom tags and a simple average-cycle-length prediction (/cycle-tracker)


##Doctor (admin) side
Dashboard: today's schedule, pending requests, flagged follow-ups
Patient list with search (/admin/patients)
Full patient chart: notes/allergies, add medications, update appointment status/notes/follow-ups, and a read-only view of the patient's cycle log (/admin/patients/<id>)
14-day schedule view (/admin/schedule)


##Tech Stack


Language: Python
Backend: Flask, Flask-SQLAlchemy, Flask-Login
Frontend: HTML, CSS (custom cream & pink theme)
Database: SQLAlchemy models (User, Patient, Appointment, Medication, CycleLog)

##Getting Started
##Prerequisites


Python 3.10+
pip
Installation
bash
git clone https://github.com/zzfaju-ops/Bloom_Woman-s_Clinic-FullStack-.git
cd Bloom_Woman-s_Clinic-FullStack-
pip install flask flask-sqlalchemy flask-login


##Usage


bash
cd doctors_office
python app.py
Then open the app in your browser at http://localhost:5000 (adjust the port if yours differs).


##Project Structure


doctors_office/
├── app.py              # All routes, cycle-prediction logic, and app setup
├── models.py           # Database tables: User, Patient, Appointment, Medication, CycleLog
├── templates/
│   ├── patient/        # Patient-facing pages
│   └── admin/          # Doctor-facing pages
└── static/
    └── css/
        └── style.css   # Cream & pink theme

        


Add appointment reminders (email/SMS)
Expand cycle prediction with more historical data points
Add data export for patients to download their own history
