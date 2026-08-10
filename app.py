import os
from datetime import datetime, date, timedelta
from collections import Counter

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from models import db, User, Patient, Appointment, Medication, CycleLog

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-this-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'clinic.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


SYMPTOM_OPTIONS = [
    "Cramps", "Headache", "Bloating", "Fatigue", "Acne", "Tender breasts",
    "Backache", "Nausea", "Food cravings", "Insomnia", "Hot flashes",
    "Anxiety", "Irritability"
]
MOOD_OPTIONS = ["Happy", "Calm", "Sensitive", "Sad", "Irritable", "Anxious", "Energetic"]
FLOW_OPTIONS = ["Spotting", "Light", "Medium", "Heavy"]
TIME_SLOTS = [f"{h}:00 {'AM' if h < 12 else 'PM'}" for h in [9, 10, 11]] + \
             [f"{h - 12 if h > 12 else h}:00 {'AM' if h < 12 else 'PM'}" for h in [13, 14, 15, 16]]


# ---------------------------------------------------------------- helpers
def patient_or_404():
    if not current_user.patient_profile:
        abort(404)
    return current_user.patient_profile


def require_admin():
    if current_user.role != "admin":
        abort(403)


def predict_cycle(patient):
    """Very simple average-cycle-length prediction from logged period-start days."""
    period_starts = (
        CycleLog.query
        .filter_by(patient_id=patient.id, is_period_day=True)
        .order_by(CycleLog.log_date.asc())
        .all()
    )
    # collapse consecutive period days into distinct "starts"
    starts = []
    prev = None
    for log in period_starts:
        if prev is None or (log.log_date - prev).days > 3:
            starts.append(log.log_date)
        prev = log.log_date

    if len(starts) < 2:
        return {"avg_length": None, "next_predicted": None, "last_start": starts[-1] if starts else None}

    gaps = [(starts[i] - starts[i - 1]).days for i in range(1, len(starts))]
    avg_length = round(sum(gaps) / len(gaps))
    next_predicted = starts[-1] + timedelta(days=avg_length)
    return {"avg_length": avg_length, "next_predicted": next_predicted, "last_start": starts[-1]}


# ---------------------------------------------------------------- auth
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        full_name = request.form["full_name"].strip()
        dob = request.form.get("dob") or None

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        user = User(email=email, role="patient")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        patient = Patient(
            user_id=user.id,
            full_name=full_name,
            date_of_birth=datetime.strptime(dob, "%Y-%m-%d").date() if dob else None,
            phone=request.form.get("phone", ""),
            address=request.form.get("address", ""),
        )
        db.session.add(patient)
        db.session.commit()

        login_user(user)
        flash("Welcome! Your patient profile has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin_dashboard" if user.role == "admin" else "dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- patient side
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    patient = patient_or_404()
    upcoming = [a for a in patient.appointments if a.date >= date.today() and a.status != "Cancelled"]
    upcoming.sort(key=lambda a: a.date)
    cycle_info = predict_cycle(patient)
    active_meds = [m for m in patient.medications if m.active]
    return render_template(
        "patient/dashboard.html", patient=patient, upcoming=upcoming[:3],
        cycle_info=cycle_info, active_meds=active_meds
    )


@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    patient = patient_or_404()
    if request.method == "POST":
        appt = Appointment(
            patient_id=patient.id,
            date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
            time=request.form["time"],
            reason=request.form.get("reason", ""),
            status="Requested",
        )
        db.session.add(appt)
        db.session.commit()
        flash("Appointment requested. The office will confirm shortly.", "success")
        return redirect(url_for("appointments"))

    all_appts = sorted(patient.appointments, key=lambda a: a.date, reverse=True)
    return render_template(
        "patient/appointments.html", patient=patient, appts=all_appts,
        time_slots=TIME_SLOTS, today=date.today().isoformat()
    )


@app.route("/appointments/<int:appt_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appt_id):
    patient = patient_or_404()
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != patient.id:
        abort(403)
    appt.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for("appointments"))


@app.route("/history")
@login_required
def history():
    patient = patient_or_404()
    return render_template("patient/history.html", patient=patient)


@app.route("/cycle-tracker", methods=["GET", "POST"])
@login_required
def cycle_tracker():
    patient = patient_or_404()
    if request.method == "POST":
        log_date = datetime.strptime(request.form["log_date"], "%Y-%m-%d").date()
        existing = CycleLog.query.filter_by(patient_id=patient.id, log_date=log_date).first()
        symptoms = ",".join(request.form.getlist("symptoms"))

        if existing:
            log = existing
        else:
            log = CycleLog(patient_id=patient.id, log_date=log_date)
            db.session.add(log)

        log.is_period_day = "is_period_day" in request.form
        log.flow = request.form.get("flow") or None
        log.mood = request.form.get("mood") or None
        log.symptoms = symptoms
        log.notes = request.form.get("notes", "")
        db.session.commit()
        flash("Entry saved.", "success")
        return redirect(url_for("cycle_tracker"))

    logs = CycleLog.query.filter_by(patient_id=patient.id).order_by(CycleLog.log_date.desc()).all()
    cycle_info = predict_cycle(patient)

    # symptom frequency for a simple insights list
    tag_counter = Counter()
    for log in logs:
        if log.symptoms:
            tag_counter.update([t for t in log.symptoms.split(",") if t])
    top_symptoms = tag_counter.most_common(5)

    return render_template(
        "patient/cycle_tracker.html", patient=patient, logs=logs, cycle_info=cycle_info,
        symptom_options=SYMPTOM_OPTIONS, mood_options=MOOD_OPTIONS, flow_options=FLOW_OPTIONS,
        today=date.today().isoformat(), top_symptoms=top_symptoms
    )


# ---------------------------------------------------------------- admin (doctor) side
@app.route("/admin")
@login_required
def admin_dashboard():
    require_admin()
    today = date.today()
    todays_appts = (
        Appointment.query.filter_by(date=today).filter(Appointment.status != "Cancelled")
        .order_by(Appointment.time).all()
    )
    pending = (
        Appointment.query.filter_by(status="Requested")
        .order_by(Appointment.date).all()
    )
    follow_ups = Appointment.query.filter_by(follow_up_needed=True).order_by(Appointment.follow_up_date).all()
    total_patients = Patient.query.count()
    return render_template(
        "admin/dashboard.html", todays_appts=todays_appts, pending=pending,
        follow_ups=follow_ups, total_patients=total_patients, today=today
    )


@app.route("/admin/patients")
@login_required
def admin_patients():
    require_admin()
    q = request.args.get("q", "").strip()
    query = Patient.query
    if q:
        query = query.filter(Patient.full_name.ilike(f"%{q}%"))
    patients = query.order_by(Patient.full_name).all()
    return render_template("admin/patients.html", patients=patients, q=q)


@app.route("/admin/patients/<int:patient_id>", methods=["GET", "POST"])
@login_required
def admin_patient_detail(patient_id):
    require_admin()
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "notes":
            patient.notes = request.form.get("notes", "")
            patient.allergies = request.form.get("allergies", "")
            db.session.commit()
            flash("Patient notes updated.", "success")

        elif form_type == "medication":
            med = Medication(
                patient_id=patient.id,
                name=request.form["name"],
                dosage=request.form.get("dosage", ""),
                frequency=request.form.get("frequency", ""),
                start_date=datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
                if request.form.get("start_date") else None,
                end_date=datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
                if request.form.get("end_date") else None,
                notes=request.form.get("med_notes", ""),
                active=True,
            )
            db.session.add(med)
            db.session.commit()
            flash("Medication added.", "success")

        return redirect(url_for("admin_patient_detail", patient_id=patient.id))

    cycle_info = predict_cycle(patient)
    return render_template("admin/patient_detail.html", patient=patient, cycle_info=cycle_info, today=date.today().isoformat())


@app.route("/admin/medications/<int:med_id>/toggle", methods=["POST"])
@login_required
def toggle_medication(med_id):
    require_admin()
    med = Medication.query.get_or_404(med_id)
    med.active = not med.active
    db.session.commit()
    return redirect(url_for("admin_patient_detail", patient_id=med.patient_id))


@app.route("/admin/appointments/<int:appt_id>/update", methods=["POST"])
@login_required
def admin_update_appointment(appt_id):
    require_admin()
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = request.form.get("status", appt.status)
    appt.doctor_notes = request.form.get("doctor_notes", appt.doctor_notes)
    appt.follow_up_needed = "follow_up_needed" in request.form
    fu_date = request.form.get("follow_up_date")
    appt.follow_up_date = datetime.strptime(fu_date, "%Y-%m-%d").date() if fu_date else None
    db.session.commit()
    flash("Appointment updated.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin/schedule")
@login_required
def admin_schedule():
    require_admin()
    start = date.today()
    days = [start + timedelta(days=i) for i in range(14)]
    appts_by_day = {}
    for d in days:
        appts_by_day[d] = (
            Appointment.query.filter_by(date=d).filter(Appointment.status != "Cancelled")
            .order_by(Appointment.time).all()
        )
    return render_template("admin/schedule.html", appts_by_day=appts_by_day)


# ---------------------------------------------------------------- seed / cli
@app.cli.command("seed")
def seed():
    """Create tables and a default doctor (admin) account."""
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        admin = User(email="doctor@clinic.com", role="admin")
        admin.set_password("changeme123")
        db.session.add(admin)
        db.session.commit()
        print("Created admin login -> email: doctor@clinic.com  password: changeme123")
    else:
        print("Admin already exists.")


with app.app_context():
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        admin = User(email="doctor@clinic.com", role="admin")
        admin.set_password("changeme123")
        db.session.add(admin)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
