from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Base login account. role = 'admin' (the doctor) or 'patient'."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="patient")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient_profile = db.relationship(
        "Patient", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    allergies = db.Column(db.Text)
    notes = db.Column(db.Text)  # general clinical notes, doctor-editable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship(
        "Appointment", backref="patient", cascade="all, delete-orphan",
        order_by="Appointment.date.desc()"
    )
    medications = db.relationship(
        "Medication", backref="patient", cascade="all, delete-orphan",
        order_by="Medication.start_date.desc()"
    )
    cycle_logs = db.relationship(
        "CycleLog", backref="patient", cascade="all, delete-orphan",
        order_by="CycleLog.log_date.desc()"
    )

    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)  # e.g. "10:30 AM"
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Requested")
    # Requested -> Confirmed -> Completed  (or Cancelled)
    doctor_notes = db.Column(db.Text)
    follow_up_needed = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    prescribed_by = db.Column(db.String(150), default="Dr. Office")
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)


class CycleLog(db.Model):
    """One entry per logged day for the cycle & symptom tracker."""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    log_date = db.Column(db.Date, nullable=False, default=date.today)
    is_period_day = db.Column(db.Boolean, default=False)
    flow = db.Column(db.String(20))  # Light / Medium / Heavy / Spotting
    mood = db.Column(db.String(50))
    symptoms = db.Column(db.String(255))  # comma-separated tags
    notes = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint("patient_id", "log_date", name="uq_patient_day"),
    )
