# Bloom Women's Clinic — Appointment & Cycle Tracker

A Flask web app for a single-doctor, female-patients-only practice. Patients can
book/track appointments, view their medication and visit history, and log a
monthly cycle & symptom tracker. The doctor (admin) has one login for the whole
practice and can manage every patient's chart, schedule, and medications.

## Setup

```bash
pip install flask flask-sqlalchemy flask-login
cd doctors_office
python app.py
```

The app creates `clinic.db` (SQLite) automatically on first run, along with a
default doctor login:

- **Email:** doctor@clinic.com
- **Password:** changeme123

Change this password (or the seed code in `app.py`) before real use.

Open **http://127.0.0.1:5000** in your browser.

## How it's organized

- `app.py` — all routes, the cycle-prediction logic, and app setup
- `models.py` — database tables: User, Patient, Appointment, Medication, CycleLog
- `templates/` — HTML pages (`patient/` for the patient side, `admin/` for the
  doctor's side)
- `static/css/style.css` — the cream & pink theme

## Patient side

- Register/login (`/register`, `/login`)
- Dashboard with upcoming appointments, cycle prediction, active meds
- Request/cancel appointments (`/appointments`)
- Full history: medications + visit notes + follow-ups (`/history`)
- Daily cycle & symptom log with period/flow/mood/symptom tags and a simple
  average-cycle-length prediction (`/cycle-tracker`)

## Doctor (admin) side

- Dashboard: today's schedule, pending requests, flagged follow-ups
- Patient list with search (`/admin/patients`)
- Full patient chart: notes/allergies, add medications, update appointment
  status/notes/follow-ups, and a read-only view of the patient's cycle log
  (`/admin/patients/<id>`)
- 14-day schedule view (`/admin/schedule`)

## Notes for taking this further

- Swap the dev `SECRET_KEY` and doctor password before deploying anywhere real.
- This stores real health data — for production use, add HTTPS, a proper
  production server (gunicorn, etc.), and check your local data-privacy
  requirements (e.g. HIPAA if this is US-based).
- The cycle prediction is a simple average — nothing clinical, just a
  convenience estimate for the patient.
