from app.database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ─────────────────────────────────────────────
#  USER & AUTH
# ─────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role          = db.Column(db.String(20), default='guru')  # 'admin' or 'guru'
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    
    classroom_id   = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    prayer_session = db.Column(db.String(20), nullable=True)
    teaching_days  = db.Column(db.String(50), nullable=True)  # contoh: '0,1,2,3,4'
    profile_pic    = db.Column(db.String(256), nullable=True)
    subject_book   = db.Column(db.String(120), nullable=True)

    schedules     = db.relationship('Schedule', backref='teacher', lazy=True)
    classroom     = db.relationship('Classroom', foreign_keys=[classroom_id], backref='teachers_registered', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def avatar_url(self):
        if self.profile_pic:
            from flask import url_for
            try:
                return url_for('static', filename='uploads/profile_pics/' + self.profile_pic)
            except Exception:
                pass
        return f"https://api.dicebear.com/7.x/avataaars/svg?seed={self.username}"

    @property
    def formatted_teaching_days(self):
        if not self.teaching_days:
            return '-'
        try:
            days = [int(x) for x in self.teaching_days.split(',') if x.strip().isdigit()]
            return ", ".join([DAY_NAMES.get(d, '-') for d in days])
        except Exception:
            return self.teaching_days

    @property
    def subjects_dict(self):
        if not self.subject_book:
            return {}
        import json
        try:
            d = json.loads(self.subject_book)
            if isinstance(d, dict):
                return {int(k): v for k, v in d.items()}
        except Exception:
            pass
        if self.teaching_days:
            try:
                days = [int(x) for x in self.teaching_days.split(',') if x.strip().isdigit()]
                return {d: self.subject_book for d in days}
            except Exception:
                pass
        return {}

    @property
    def formatted_subject_book(self):
        if not self.subject_book:
            return '-'
        import json
        try:
            d = json.loads(self.subject_book)
            if isinstance(d, dict):
                parts = []
                for k in sorted(d.keys(), key=int):
                    day_idx = int(k)
                    day_name = DAY_NAMES.get(day_idx, '')
                    v = d[k]
                    if day_name and v:
                        parts.append(f"{day_name}: {v}")
                if parts:
                    return ", ".join(parts)
        except Exception:
            pass
        return self.subject_book

# ─────────────────────────────────────────────
#  ACADEMIC MASTER DATA
# ─────────────────────────────────────────────
class AcademicYear(db.Model):
    __tablename__ = 'academic_years'
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(50), nullable=False)  # e.g. "2024/2025"
    is_active = db.Column(db.Boolean, default=False)
    
    # Relationship ke pivot table
    classroom_students = db.relationship('ClassroomStudent', backref='academic_year', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(50), nullable=False)  # e.g. "Subuh 1", "Magrib 2"
    level               = db.Column(db.Integer, nullable=False)
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # ✅ RELATIONSHIP UPDATED: backref='classroom' agar bisa dipanggil cs.classroom
    students = db.relationship('ClassroomStudent', backref='classroom', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='classroom', lazy=True)

# ─────────────────────────────────────────────
#  STUDENT & PIVOT TABLES
# ─────────────────────────────────────────────
class Student(db.Model):
    __tablename__ = 'students'
    id           = db.Column(db.Integer, primary_key=True)
    nis          = db.Column(db.String(20), unique=True, nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    birth_date   = db.Column(db.Date)
    gender       = db.Column(db.String(10))  # 'L' or 'P'
    address      = db.Column(db.Text)
    parent_name  = db.Column(db.String(100))
    parent_phone = db.Column(db.String(20))
    status       = db.Column(db.String(20), default='active')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ RELATIONSHIP UPDATED: backref='student' agar bisa dipanggil cs.student
    # Nama 'classroom_students' (plural) agar konsisten dengan loop di template
    classroom_students = db.relationship('ClassroomStudent', backref='student', lazy=True, cascade='all, delete-orphan')
    attendances  = db.relationship('Attendance', backref='student', lazy=True)
    exam_scores  = db.relationship('ExamScore', backref='student', lazy=True)
    spp_payments = db.relationship('SppPayment', backref='student', lazy=True)

class ClassroomStudent(db.Model):
    """Pivot: Murid yang terdaftar di kelas tertentu pada tahun ajaran tertentu."""
    __tablename__ = 'classroom_students'
    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    classroom_id     = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    joined_at        = db.Column(db.DateTime, default=datetime.utcnow)

class StudentHistory(db.Model):
    __tablename__ = 'student_history'
    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    classroom_id     = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    status           = db.Column(db.String(20), default='passed')

# ─────────────────────────────────────────────
#  SCHEDULE (JADWAL MENGAJAR)
# ─────────────────────────────────────────────
DAY_NAMES = {0:'Senin', 1:'Selasa', 2:'Rabu', 3:'Kamis', 4:"Jum'at", 5:'Sabtu', 6:'Minggu'}
PRAYER_SESSIONS = ['Subuh', 'Dzuhur', 'Ashar', 'Magrib']

HOLIDAY_RULES = {
    'Subuh':  [4],
    'Dzuhur': [5],
    'Ashar':  [5],
    'Magrib': [1],   # Selasa = libur; Jumat = Tawasulan (special)
}
TAWASULAN_DAY = 4   # Jumat Magrib = Tawasulan

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id             = db.Column(db.Integer, primary_key=True)
    teacher_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id   = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    subject_id     = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    day_of_week    = db.Column(db.Integer, nullable=False)        # 0=Senin … 6=Minggu
    prayer_session = db.Column(db.String(20), nullable=False)     # Subuh/Dzuhur/Ashar/Magrib
    is_active      = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship('Subject', backref='schedules', lazy=True)
    attendances = db.relationship('Attendance', backref='schedule', lazy=True, cascade='all, delete-orphan')
    exams = db.relationship('Exam', backref='schedule', lazy=True, cascade='all, delete-orphan')

# ─────────────────────────────────────────────
#  ATTENDANCE (ABSENSI MURID)
# ─────────────────────────────────────────────
class Attendance(db.Model):
    __tablename__ = 'attendances'
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    status      = db.Column(db.String(10), nullable=False)  # hadir/sakit/izin/alpa
    notes       = db.Column(db.String(200))
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────
#  ACTIVITY LOG (AUDIT TRAIL)
# ─────────────────────────────────────────────
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='logs', lazy=True)

# ─────────────────────────────────────────────
#  REGISTRATION (PENDAFTARAN SANTRI BARU)
# ─────────────────────────────────────────────
class Registration(db.Model):
    __tablename__ = 'registrations'
    id              = db.Column(db.Integer, primary_key=True)
    # Data Calon Santri
    full_name       = db.Column(db.String(100), nullable=False)
    nickname        = db.Column(db.String(50))
    birth_place     = db.Column(db.String(100))
    birth_date      = db.Column(db.Date, nullable=False)
    gender          = db.Column(db.String(10), nullable=False)
    address         = db.Column(db.Text)
    previous_school = db.Column(db.String(150))
    # Data Orang Tua / Wali
    parent_name     = db.Column(db.String(100), nullable=False)
    parent_phone    = db.Column(db.String(20), nullable=False)
    parent_job      = db.Column(db.String(100))
    # Status Pendaftaran
    status          = db.Column(db.String(20), default='pending')
    admin_notes     = db.Column(db.Text)
    academic_year   = db.Column(db.String(50))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at     = db.Column(db.DateTime)
    reviewed_by     = db.Column(db.Integer, db.ForeignKey('users.id'))

# ─────────────────────────────────────────────
#  EXAM (ULANGAN MINGGUAN)
# ─────────────────────────────────────────────
class Exam(db.Model):
    __tablename__ = 'exams'
    id          = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    title       = db.Column(db.String(150), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    scores = db.relationship('ExamScore', backref='exam', lazy=True, cascade='all, delete-orphan')

class ExamScore(db.Model):
    __tablename__ = 'exam_scores'
    id         = db.Column(db.Integer, primary_key=True)
    exam_id    = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    score      = db.Column(db.Float, default=0)

# ─────────────────────────────────────────────
#  KEUANGAN (SPP & CASHFLOW)
# ─────────────────────────────────────────────
class SppPayment(db.Model):
    __tablename__ = 'spp_payments'
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    month       = db.Column(db.Integer, nullable=False)  # 1-12
    year        = db.Column(db.Integer, nullable=False)
    amount      = db.Column(db.Float, nullable=False, default=10000.0)
    paid_date   = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship('User', backref='recorded_spp_payments', lazy=True)

class CashFlow(db.Model):
    __tablename__ = 'cash_flows'
    id               = db.Column(db.Integer, primary_key=True)
    type             = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    category         = db.Column(db.String(50), nullable=False)
    amount           = db.Column(db.Float, nullable=False)
    description      = db.Column(db.Text, nullable=True)
    transaction_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    recorded_by      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship('User', backref='recorded_cash_flows', lazy=True)