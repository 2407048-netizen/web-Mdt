# app/routes/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, render_template_string, make_response
from flask_login import login_required, current_user
from app import db  # Menggunakan db dari app/__init__.py agar konsisten
from app.models import (User, Classroom, Subject, Schedule, Student,
                         ClassroomStudent, AcademicYear, ActivityLog,
                         Attendance, ExamScore, DAY_NAMES, PRAYER_SESSIONS,
                         SppPayment, CashFlow, Exam, ExamScore)
from datetime import datetime, date
import pandas as pd
from werkzeug.utils import secure_filename
from io import BytesIO
import qrcode
import base64
import os

# PENTING: Nama variabel Blueprint WAJIB 'admin_bp'
admin_bp = Blueprint('admin', __name__)

def log_activity(action, detail=''):
    log = ActivityLog(user_id=current_user.id, action=action, detail=detail, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()

@admin_bp.before_request
@login_required
def require_admin():
    if current_user.role != 'admin':
        abort(403)

# ─────────────────────────────────────────────
#  DASHBOARD
# ────────────────────────────────────────────
@admin_bp.route('/dashboard')
def dashboard():
    total_students = Student.query.filter_by(status='active').count()
    total_teachers = User.query.filter_by(role='guru').count()
    total_schedules = Schedule.query.filter_by(is_active=True).count()
    recent_logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(8).all()
    return render_template('admin/dashboard.html', total_students=total_students,
                           total_teachers=total_teachers, total_schedules=total_schedules, recent_logs=recent_logs)

# ─────────────────────────────────────────────
#  DATA SANTRI (UPLOAD & CRUD)
# ─────────────────────────────────────────────
@admin_bp.route('/students')
def students():
    kelas_id = request.args.get('kelas_id', type=int)
    query = Student.query
    
    if kelas_id:
        cs_records = ClassroomStudent.query.filter_by(classroom_id=kelas_id).all()
        student_ids = [cs.student_id for cs in cs_records]
        query = query.filter(Student.id.in_(student_ids))
    
    all_students = query.order_by(Student.name).all()
    all_classes = Classroom.query.order_by(Classroom.level, Classroom.name).all()
    
    return render_template('admin/students.html', 
                           students=all_students, 
                           classes=all_classes, 
                           selected_classroom_id=kelas_id)

@admin_bp.route('/upload-students', methods=['POST'])
def upload_students():
    """Handle upload Excel santri dengan normalisasi data & typo handling"""
    file = request.files.get('file')
    
    if not file:
        flash('Mohon pilih file Excel.', 'error')
        return redirect(url_for('admin.students'))

    try:
        df = pd.read_excel(file)
        
        # Normalisasi header
        df.columns = [str(col).strip().upper() for col in df.columns]
        required_cols = ['NAMA', 'JADWAL', 'KELAS', 'JENIS KELAMIN', 'STATUS']
        
        if not all(col in df.columns for col in required_cols):
            flash('Format file salah. Pastikan header: NAMA, JADWAL, KELAS, JENIS KELAMIN, STATUS', 'error')
            return redirect(url_for('admin.students'))

        # Pastikan Tahun Ajaran Aktif
        active_year = AcademicYear.query.filter_by(is_active=True).first()
        if not active_year:
            active_year = AcademicYear.query.order_by(AcademicYear.id.desc()).first()
        if not active_year:
            flash('Tahun ajaran tidak ditemukan.', 'error')
            return redirect(url_for('admin.students'))

        count = 0
        for _, row in df.iterrows():
            nama = str(row['NAMA']).strip()
            
            # Skip baris kosong
            if not nama or nama.lower() == 'nan':
                continue

            jadwal_raw = str(row['JADWAL']).strip().upper()
            kelas_level = str(row['KELAS']).strip()
            gender_raw = str(row['JENIS KELAMIN']).strip().upper()
            status_raw = str(row.get('STATUS', '')).strip().lower()

            # ✅ Normalisasi Jadwal (Typo)
            if 'ASHAR' in jadwal_raw or 'ASAR' in jadwal_raw:
                jadwal = 'Ashar'
            elif 'MAGRIB' in jadwal_raw:
                jadwal = 'Magrib'
            elif 'SUBUH' in jadwal_raw:
                jadwal = 'Subuh'
            elif 'DZUHUR' in jadwal_raw or 'DHUHUR' in jadwal_raw:
                jadwal = 'Dzuhur'
            else:
                jadwal = jadwal_raw.capitalize()

            # ✅ Normalisasi Status (Typo "aktip" -> "active")
            status = 'active'
            if 'tidak' in status_raw or 'non' in status_raw:
                status = 'inactive'

            gender = 'L' if gender_raw in ['L', 'LAKI-LAKI', 'LELAKI'] else 'P'

            # Cari atau Buat Kelas
            target_classroom = None
            class_name_search = f"{jadwal} {kelas_level}"
            target_classroom = Classroom.query.filter_by(name=class_name_search).first()
            
            if not target_classroom:
                candidates = Classroom.query.filter_by(level=int(kelas_level)).all()
                for c in candidates:
                    if jadwal.lower() in c.name.lower():
                        target_classroom = c
                        break
            
            if not target_classroom:
                target_classroom = Classroom(name=class_name_search, level=int(kelas_level))
                db.session.add(target_classroom)
                db.session.flush()

            # Cek Duplikat Santri
            existing_student = Student.query.filter_by(name=nama).first()
            if existing_student:
                existing_student.status = status
                cs = ClassroomStudent.query.filter_by(student_id=existing_student.id, academic_year_id=active_year.id).first()
                if cs:
                    cs.classroom_id = target_classroom.id
                else:
                    db.session.add(ClassroomStudent(student_id=existing_student.id, classroom_id=target_classroom.id, academic_year_id=active_year.id))
                count += 1
                continue

            # Buat Santri Baru
            last = Student.query.order_by(Student.id.desc()).first()
            next_id = (last.id + 1) if last else 1
            nis = f"MDT{datetime.now().year}{next_id:04d}"

            student = Student(nis=nis, name=nama, gender=gender, status=status, parent_name="-", parent_phone="-")
            db.session.add(student)
            db.session.flush()
            db.session.add(ClassroomStudent(student_id=student.id, classroom_id=target_classroom.id, academic_year_id=active_year.id))
            count += 1

        db.session.commit()
        flash(f'✅ Berhasil upload {count} data santri!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error upload: {str(e)}', 'error')
        print(e)
    return redirect(url_for('admin.students'))

@admin_bp.route('/students/add', methods=['GET', 'POST'])
def add_student():
    classrooms = Classroom.query.order_by(Classroom.level).all()
    academic_years = AcademicYear.query.all()
    if request.method == 'POST':
        current_year = datetime.now().year
        last_student = Student.query.order_by(Student.id.desc()).first()
        next_id = (last_student.id + 1) if last_student else 1
        nis = f"MDT{current_year}{next_id:04d}"
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '')
        birth_date = request.form.get('birth_date', '')
        parent_name = request.form.get('parent_name', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        classroom_id = request.form.get('classroom_id', type=int)
        ay_id = request.form.get('academic_year_id', type=int)

        if not name or not gender:
            flash('Nama dan Jenis Kelamin wajib diisi.', 'error')
            return redirect(url_for('admin.add_student'))

        bd = None
        if birth_date:
            try: bd = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except: pass

        student = Student(nis=nis, name=name, gender=gender, birth_date=bd, parent_name=parent_name, parent_phone=parent_phone)
        db.session.add(student)
        db.session.flush()

        if classroom_id:
            if not ay_id:
                active_yr = AcademicYear.query.filter_by(is_active=True).first()
                ay_id = active_yr.id if active_yr else None
            if ay_id:
                db.session.add(ClassroomStudent(student_id=student.id, classroom_id=classroom_id, academic_year_id=ay_id))

        log_activity('TAMBAH_SANTRI', f'Santri: {name}')
        db.session.commit()
        flash(f'Santri {name} berhasil ditambahkan!', 'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', student=None, classrooms=classrooms, academic_years=academic_years, current_classroom_id=None, prayer_sessions=PRAYER_SESSIONS, session_classrooms={}, current_session=None)

@admin_bp.route('/students/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    classrooms = Classroom.query.order_by(Classroom.level).all()
    academic_years = AcademicYear.query.all()
    current_cs = ClassroomStudent.query.filter_by(student_id=id).first()
    current_classroom_id = current_cs.classroom_id if current_cs else None

    if request.method == 'POST':
        student.name = request.form.get('name', '').strip()
        student.gender = request.form.get('gender', '')
        student.parent_name = request.form.get('parent_name', '').strip()
        student.parent_phone = request.form.get('parent_phone', '').strip()
        classroom_id = request.form.get('classroom_id', type=int)
        ay_id = request.form.get('academic_year_id', type=int)

        if classroom_id:
            if not ay_id:
                active_yr = AcademicYear.query.filter_by(is_active=True).first()
                ay_id = active_yr.id if active_yr else None
            if current_cs:
                current_cs.classroom_id = classroom_id
                if ay_id: current_cs.academic_year_id = ay_id
            elif ay_id:
                db.session.add(ClassroomStudent(student_id=id, classroom_id=classroom_id, academic_year_id=ay_id))

        log_activity('EDIT_SANTRI', f'Santri: {student.name}')
        db.session.commit()
        flash(f'Data {student.name} berhasil diperbarui!', 'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', student=student, classrooms=classrooms, academic_years=academic_years, current_classroom_id=current_classroom_id, prayer_sessions=PRAYER_SESSIONS, session_classrooms={}, current_session=None)

@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
def delete_student(id):
    student = Student.query.get_or_404(id)
    student.status = 'inactive'
    log_activity('HAPUS_SANTRI', f'Santri: {student.name}')
    db.session.commit()
    flash(f'Santri {student.name} berhasil dihapus.', 'success')
    return redirect(url_for('admin.students'))

# ─────────────────────────────────────────────
#  JADWAL
# ─────────────────────────────────────────────
@admin_bp.route('/schedules')
def schedules():
    all_schedules = (Schedule.query
                     .join(User, Schedule.teacher_id == User.id)
                     .join(Classroom, Schedule.classroom_id == Classroom.id)
                     .join(Subject, Schedule.subject_id == Subject.id)
                     .order_by(Schedule.day_of_week, Schedule.prayer_session)
                     .all())
    return render_template('admin/schedules.html', schedules=all_schedules, day_names=DAY_NAMES)

@admin_bp.route('/schedules/add', methods=['GET', 'POST'])
def add_schedule():
    teachers = User.query.filter_by(role='guru', is_active=True).all()
    classrooms = Classroom.query.order_by(Classroom.level).all()
    subjects = Subject.query.order_by(Subject.name).all()
    session_classrooms = {s: [] for s in PRAYER_SESSIONS}
    for c in classrooms:
        for s in PRAYER_SESSIONS:
            if c.name.startswith(s):
                session_classrooms[s].append({'id': c.id, 'name': f"Kelas {c.name} (Level {c.level})"})
                break

    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id', type=int)
        classroom_id = request.form.get('classroom_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        days_of_week = request.form.getlist('days_of_week')
        prayer_session = request.form.get('prayer_session')
        selected_days = [int(d) for d in days_of_week if d.isdigit()]
        
        if not selected_days:
            flash('Harap pilih minimal satu hari mengajar.', 'error')
            return redirect(url_for('admin.add_schedule'))

        added_count = 0
        for day in selected_days:
            existing = Schedule.query.filter_by(teacher_id=teacher_id, classroom_id=classroom_id, day_of_week=day, prayer_session=prayer_session, is_active=True).first()
            if not existing:
                schedule = Schedule(teacher_id=teacher_id, classroom_id=classroom_id, subject_id=subject_id, day_of_week=day, prayer_session=prayer_session)
                db.session.add(schedule)
                added_count += 1

        if added_count > 0:
            db.session.commit()
            flash(f'{added_count} jadwal baru berhasil dibuat!', 'success')
        else:
            flash('Jadwal tersebut sudah ada sebelumnya!', 'error')
        return redirect(url_for('admin.schedules'))
    return render_template('admin/schedule_form.html', teachers=teachers, classrooms=classrooms, subjects=subjects, day_names=DAY_NAMES, prayer_sessions=PRAYER_SESSIONS, session_classrooms=session_classrooms, schedule=None)

@admin_bp.route('/schedules/edit/<int:id>', methods=['GET', 'POST'])
def edit_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    teachers = User.query.filter_by(role='guru', is_active=True).all()
    classrooms = Classroom.query.order_by(Classroom.level).all()
    subjects = Subject.query.order_by(Subject.name).all()
    session_classrooms = {s: [] for s in PRAYER_SESSIONS}
    for c in classrooms:
        for s in PRAYER_SESSIONS:
            if c.name.startswith(s):
                session_classrooms[s].append({'id': c.id, 'name': f"Kelas {c.name} (Level {c.level})"})
                break

    if request.method == 'POST':
        days_of_week = request.form.getlist('days_of_week')
        selected_days = [int(d) for d in days_of_week if d.isdigit()]
        if not selected_days:
            flash('Harap pilih minimal satu hari mengajar.', 'error')
            return redirect(url_for('admin.edit_schedule', id=id))

        schedule.teacher_id = request.form.get('teacher_id', type=int)
        schedule.classroom_id = request.form.get('classroom_id', type=int)
        schedule.subject_id = request.form.get('subject_id', type=int)
        schedule.day_of_week = selected_days[0]
        schedule.prayer_session = request.form.get('prayer_session')

        for day in selected_days[1:]:
            existing = Schedule.query.filter_by(teacher_id=schedule.teacher_id, classroom_id=schedule.classroom_id, day_of_week=day, prayer_session=schedule.prayer_session, is_active=True).first()
            if not existing:
                sch = Schedule(teacher_id=schedule.teacher_id, classroom_id=schedule.classroom_id, subject_id=schedule.subject_id, day_of_week=day, prayer_session=schedule.prayer_session)
                db.session.add(sch)

        db.session.commit()
        flash('Jadwal berhasil diperbarui!', 'success')
        return redirect(url_for('admin.schedules'))
    return render_template('admin/schedule_form.html', teachers=teachers, classrooms=classrooms, subjects=subjects, day_names=DAY_NAMES, prayer_sessions=PRAYER_SESSIONS, session_classrooms=session_classrooms, schedule=schedule)

@admin_bp.route('/schedules/delete/<int:id>', methods=['POST'])
def delete_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    schedule.is_active = False
    db.session.commit()
    flash('Jadwal berhasil dihapus.', 'success')
    return redirect(url_for('admin.schedules'))

# ─────────────────────────────────────────────
#  GURU
# ─────────────────────────────────────────────
@admin_bp.route('/registrations')
def registrations():
    status_filter = request.args.get('status', '')
    query = User.query.filter_by(role='guru').order_by(User.created_at.desc())
    if status_filter == 'pending': query = query.filter_by(is_active=False)
    elif status_filter == 'active': query = query.filter_by(is_active=True)
    teachers = query.all()
    stats = {'pending': User.query.filter_by(role='guru', is_active=False).count(), 'active': User.query.filter_by(role='guru', is_active=True).count(), 'total': User.query.filter_by(role='guru').count()}
    return render_template('admin/registrations.html', teachers=teachers, stats=stats, status_filter=status_filter)

@admin_bp.route('/registrations/toggle/<int:id>', methods=['POST'])
def toggle_guru(id):
    guru = User.query.get_or_404(id)
    if guru.role != 'guru': abort(403)
    action = request.form.get('action')
    if action == 'activate':
        guru.is_active = True
        flash(f'Akun {guru.username} berhasil diaktivasi!', 'success')
    elif action == 'deactivate':
        guru.is_active = False
        flash(f'Akun {guru.username} dinonaktifkan.', 'warning')
    db.session.commit()
    return redirect(url_for('admin.registrations'))

# ─────────────────────────────────────────────
#  KELAS
# ─────────────────────────────────────────────
@admin_bp.route('/classrooms')
def classrooms():
    all_cls = Classroom.query.order_by(Classroom.level, Classroom.name).all()
    student_counts = {cls.id: ClassroomStudent.query.filter_by(classroom_id=cls.id).count() for cls in all_cls}
    return render_template('admin/classrooms.html', classrooms=all_cls, student_counts=student_counts)

@admin_bp.route('/classrooms/add', methods=['POST'])
def add_classroom():
    name = request.form.get('name', '').strip()
    level = request.form.get('level', type=int)
    if not name or not level:
        flash('Nama dan tingkat wajib diisi.', 'error')
        return redirect(url_for('admin.classrooms'))
    if Classroom.query.filter_by(name=name).first():
        flash('Nama kelas sudah ada!', 'error')
        return redirect(url_for('admin.classrooms'))
    cls = Classroom(name=name, level=level)
    db.session.add(cls)
    log_activity('TAMBAH_KELAS', f'Kelas: {name} (Tingkat {level})')
    db.session.commit()
    flash(f'Kelas {name} berhasil ditambahkan!', 'success')
    return redirect(url_for('admin.classrooms'))

@admin_bp.route('/classrooms/delete/<int:id>', methods=['POST'])
def delete_classroom(id):
    cls = Classroom.query.get_or_404(id)
    log_activity('HAPUS_KELAS', f'Kelas: {cls.name}')
    db.session.delete(cls)
    db.session.commit()
    flash(f'Kelas {cls.name} berhasil dihapus.', 'success')
    return redirect(url_for('admin.classrooms'))

# ─────────────────────────────────────────────
#  LAPORAN ABSENSI
# ─────────────────────────────────────────────
@admin_bp.route('/reports')
def reports():
    all_cls = Classroom.query.order_by(Classroom.level).all()
    selected_classroom = request.args.get('classroom_id', type=int)
    selected_session = request.args.get('prayer_session', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query
    schedule_query = Schedule.query
    if selected_classroom: schedule_query = schedule_query.filter_by(classroom_id=selected_classroom)
    if selected_session: schedule_query = schedule_query.filter_by(prayer_session=selected_session)
    
    if selected_classroom or selected_session:
        schedule_ids = [s.id for s in schedule_query.all()]
        query = query.filter(Attendance.schedule_id.in_(schedule_ids))

    if date_from:
        try: query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except: pass
    if date_to:
        try: query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except: pass

    records = query.all()
    stats = {'hadir': 0, 'sakit': 0, 'izin': 0, 'alpa': 0}
    student_data = {}
    for r in records:
        if r.status in stats: stats[r.status] += 1
        if r.student_id not in student_data:
            student = Student.query.get(r.student_id)
            cs = ClassroomStudent.query.filter_by(student_id=r.student_id).first()
            cls_name = Classroom.query.get(cs.classroom_id).name if cs else '-'
            student_data[r.student_id] = {'name': student.name, 'gender': student.gender, 'classroom': cls_name, 'hadir': 0, 'sakit': 0, 'izin': 0, 'alpa': 0}
        if r.status in student_data[r.student_id]: student_data[r.student_id][r.status] += 1

    student_summary = sorted(student_data.values(), key=lambda x: x['name'])
    return render_template('admin/reports.html', classrooms=all_cls, selected_classroom=selected_classroom, selected_session=selected_session, prayer_sessions=PRAYER_SESSIONS, session_classrooms={}, date_from=date_from, date_to=date_to, total_records=len(records), stats=stats, student_summary=student_summary)

# ─────────────────────────────────────────────
#  PERINGKAT
# ─────────────────────────────────────────────
@admin_bp.route('/rankings')
def rankings():
    all_cls = Classroom.query.order_by(Classroom.level).all()
    selected_classroom = request.args.get('classroom_id', type=int)
    selected_session = request.args.get('prayer_session', '')

    student_query = Student.query.filter_by(status='active')
    if selected_classroom:
        cs_ids = [c.student_id for c in ClassroomStudent.query.filter_by(classroom_id=selected_classroom).all()]
        student_query = student_query.filter(Student.id.in_(cs_ids))
    students = student_query.order_by(Student.name).all()

    schedule_ids = []
    exam_ids = []
    if selected_session:
        schedule_ids = [s.id for s in Schedule.query.filter_by(prayer_session=selected_session).all()]
        exam_ids = [e.id for e in Exam.query.filter(Exam.schedule_id.in_(schedule_ids)).all()]

    rankings = []
    for student in students:
        cs = ClassroomStudent.query.filter_by(student_id=student.id).first()
        cls_name = Classroom.query.get(cs.classroom_id).name if cs else '-'

        # --- PERBAIKAN LOGIKA NILAI KEHADIRAN ---
        att_query = Attendance.query.filter_by(student_id=student.id)
        if selected_session: att_query = att_query.filter(Attendance.schedule_id.in_(schedule_ids))
        
        total_att = att_query.count()
        
        if total_att > 0:
            hadir_att = att_query.filter_by(status='hadir').count()
            sakit_att = att_query.filter_by(status='sakit').count()
            izin_att = att_query.filter_by(status='izin').count()
            
            # Rumus Bobot: Hadir=100, Sakit=50, Izin=50, Alpa=0
            weighted_score = (hadir_att * 100) + (sakit_att * 50) + (izin_att * 50)
            attendance_pct = weighted_score / total_att
            
            # Nilai Akhir Kehadiran (70% dari bobot)
            attendance_score = attendance_pct * 0.7
        else:
            attendance_pct = 0
            attendance_score = 0

        exam_score_query = ExamScore.query.filter_by(student_id=student.id)
        if selected_session: exam_score_query = exam_score_query.filter(ExamScore.exam_id.in_(exam_ids))
        all_scores = exam_score_query.all()
        exam_avg = (sum(s.score for s in all_scores) / len(all_scores)) if all_scores else 0
        exam_score = exam_avg * 0.3

        rankings.append({
            'name': student.name, 
            'gender': student.gender, 
            'classroom': cls_name, 
            'attendance_pct': attendance_pct, 
            'attendance_score': attendance_score, 
            'exam_avg': exam_avg, 
            'exam_score': exam_score, 
            'final_score': attendance_score + exam_score
        })

    rankings.sort(key=lambda x: x['final_score'], reverse=True)
    return render_template('admin/rankings.html', classrooms=all_cls, selected_classroom=selected_classroom, selected_session=selected_session, prayer_sessions=PRAYER_SESSIONS, session_classrooms={}, rankings=rankings)

# ─────────────────────────────────────────────
#  SPP
# ─────────────────────────────────────────────
@admin_bp.route('/spp', methods=['GET'])
def spp():
    classrooms = Classroom.query.filter(Classroom.name.like('Magrib%')).order_by(Classroom.level).all()
    selected_classroom_id = request.args.get('classroom_id', type=int, default=0)
    selected_year = request.args.get('year', type=int, default=datetime.now().year)
    selected_month = request.args.get('month', type=int, default=0)
    
    magrib_classroom_ids = [c.id for c in classrooms]
    
    if not magrib_classroom_ids:
        return render_template('admin/spp.html',
                               classrooms=[],
                               selected_classroom_id=0,
                               selected_year=selected_year,
                               selected_month=selected_month,
                               months_names={},
                               years_range=range(2024, 2028),
                               history_payments=[])
    
    query = SppPayment.query.filter(SppPayment.year == selected_year)
    
    # ✅ FILTER BULAN (jika dipilih)
    if selected_month > 0:
        query = query.filter(SppPayment.month == selected_month)
    
    # Filter Kelas
    if selected_classroom_id > 0 and selected_classroom_id in magrib_classroom_ids:
        pivot = ClassroomStudent.query.filter_by(classroom_id=selected_classroom_id).all()
        student_ids = [p.student_id for p in pivot]
        if student_ids:
            query = query.filter(SppPayment.student_id.in_(student_ids))
        else:
            query = query.filter(SppPayment.id == -1)
    else:
        pivot = ClassroomStudent.query.filter(ClassroomStudent.classroom_id.in_(magrib_classroom_ids)).all()
        student_ids = [p.student_id for p in pivot]
        if student_ids:
            query = query.filter(SppPayment.student_id.in_(student_ids))
        else:
            query = query.filter(SppPayment.id == -1)
            
    history_payments = query.order_by(SppPayment.paid_date.desc(), SppPayment.created_at.desc()).all()
    
    months_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    years_range = range(datetime.now().year - 2, datetime.now().year + 3)
    
    return render_template('admin/spp.html',
                           classrooms=classrooms,
                           selected_classroom_id=selected_classroom_id if selected_classroom_id in magrib_classroom_ids else 0,
                           selected_year=selected_year,
                           selected_month=selected_month,
                           months_names=months_names,
                           years_range=years_range,
                           history_payments=history_payments)

@admin_bp.route('/spp/cancel/<int:id>', methods=['POST'])
def cancel_spp(id):
    """Membatalkan pembayaran SPP"""
    payment = SppPayment.query.get_or_404(id)
    
    try:
        db.session.delete(payment)
        db.session.commit()
        flash('Pembayaran SPP berhasil dibatalkan.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal membatalkan pembayaran: {str(e)}', 'error')
    
    return redirect(url_for('admin.spp'))

# ─────────────────────────────────────────────
#  ARUS KAS
# ─────────────────────────────────────────────
@admin_bp.route('/arus-kas', methods=['GET'])
def arus_kas():
    filter_year = request.args.get('year', type=int, default=datetime.now().year)
    filter_month = request.args.get('month', type=int)
    filter_class_id = request.args.get('class_id', type=int)

    months_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
        7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }

    # Query dasar
    spp_payments = SppPayment.query.filter_by(year=filter_year).all()
    cash_flows = CashFlow.query.all()

    # Apply filter bulan
    if filter_month:
        spp_payments = [p for p in spp_payments if p.month == filter_month]
        cash_flows = [cf for cf in cash_flows if cf.transaction_date.month == filter_month]

    transactions = []
    class_totals = {}

    # ✅ Hanya ambil kelas Magrib untuk filter dropdown di Arus Kas
    all_classrooms = Classroom.query.filter(Classroom.name.like('Magrib%'))\
                                    .order_by(Classroom.level, Classroom.name)\
                                    .all()

    for p in spp_payments:
        # Ambil nama kelas santri
        cls_name = '-'
        cs = ClassroomStudent.query.filter_by(student_id=p.student_id).first()
        if cs and cs.classroom:
            cls_name = cs.classroom.name

        # Hitung total per kelas untuk ringkasan
        if cls_name != '-':
            class_totals[cls_name] = class_totals.get(cls_name, 0) + p.amount

        transactions.append({
            'id': f"spp_{p.id}", 'type': 'income', 'category': 'SPP Santri',
            'amount': p.amount, 'class': cls_name,
            'description': f"Setoran SPP {months_names[p.month]} {p.year} - {p.student.name}",
            'date': p.paid_date, 'recorder': p.recorder.username,
            'is_spp': True, 'db_id': p.id
        })

    for cf in cash_flows:
        transactions.append({
            'id': f"cf_{cf.id}", 'type': cf.type, 'category': cf.category,
            'amount': cf.amount, 'class': '-',
            'description': cf.description or '-',
            'date': cf.transaction_date, 'recorder': cf.recorder.username,
            'is_spp': False, 'db_id': cf.id
        })

    # Jika filter kelas aktif, filter transaksi SPP
    if filter_class_id:
        target_class = Classroom.query.get(filter_class_id)
        if target_class:
            transactions = [t for t in transactions if t.get('class') == target_class.name or not t.get('is_spp')]

    transactions.sort(key=lambda t: t['date'], reverse=True)

    total_income = sum(p.amount for p in spp_payments)
    total_expense = sum(cf.amount for cf in cash_flows if cf.type == 'expense')
    balance = total_income - total_expense

    years_range = range(datetime.now().year - 2, datetime.now().year + 3)

    return render_template('admin/arus_kas.html',
                           transactions=transactions,
                           total_income=total_income,
                           total_expense=total_expense,
                           balance=balance,
                           now=datetime.now(),
                           classes=all_classrooms,
                           years_range=years_range,
                           filter_month=filter_month,
                           filter_class_id=filter_class_id,
                           filter_year=filter_year,
                           class_totals=class_totals,
                           months_names=months_names)

@admin_bp.route('/arus-kas/add', methods=['POST'])
def arus_kas_add():
    category = request.form.get('category')
    amount_str = request.form.get('amount')
    description = request.form.get('description')
    date_str = request.form.get('transaction_date')
    
    try:
        amount = float(amount_str)
        t_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
        cf = CashFlow(type='expense', category=category, amount=amount, description=description, transaction_date=t_date, recorded_by=current_user.id)
        db.session.add(cf)
        db.session.commit()
        flash('Transaksi pengeluaran berhasil dicatat!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mencatat transaksi: {str(e)}', 'danger')
    return redirect(url_for('admin.arus_kas'))

@admin_bp.route('/arus-kas/delete/<int:id>', methods=['POST'])
def arus_kas_delete(id):
    cf = CashFlow.query.get_or_404(id)
    try:
        db.session.delete(cf)
        db.session.commit()
        flash('Transaksi arus kas berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus transaksi: {str(e)}', 'danger')
    return redirect(url_for('admin.arus_kas'))

# ─────────────────────────────────────────────
#  CETAK IJAZAH
# ────────────────────────────────────────────
@admin_bp.route('/ijazah')
def ijazah():
    level = request.args.get('level', type=int)
    academic_year_id = request.args.get('academic_year_id', type=int)

    query = Student.query.filter_by(status='active')

    if level:
        classrooms = Classroom.query.filter_by(level=level).all()
        cls_ids = [c.id for c in classrooms]
        cs_records = ClassroomStudent.query.filter(ClassroomStudent.classroom_id.in_(cls_ids)).all()
        student_ids = [cs.student_id for cs in cs_records]
        if student_ids:
            query = query.filter(Student.id.in_(student_ids))
        else:
            query = query.filter(Student.id == -1)

    if academic_year_id:
        cs_records = ClassroomStudent.query.filter_by(academic_year_id=academic_year_id).all()
        student_ids = [cs.student_id for cs in cs_records]
        if student_ids:
            query = query.filter(Student.id.in_(student_ids))
        else:
            query = query.filter(Student.id == -1)

    students = query.order_by(Student.name).all()
    
    # Ambil daftar level unik
    levels = db.session.query(Classroom.level).distinct().order_by(Classroom.level).all()
    levels = [l[0] for l in levels]
    academic_years = AcademicYear.query.all()

    return render_template('admin/ijazah.html', students=students, levels=levels,
                           academic_years=academic_years, selected_level=level,
                           selected_ay=academic_year_id)

@admin_bp.route('/ijazah/print/<int:student_id>')
def print_ijazah(student_id):
    from datetime import datetime as dt
    
    student = Student.query.get_or_404(student_id)
    
    cs = ClassroomStudent.query.filter_by(student_id=student_id).first()
    classroom = cs.classroom if cs else None
    academic_year = cs.academic_year if cs and cs.academic_year else AcademicYear.query.filter_by(is_active=True).first()

    # Generate QR Code untuk verifikasi
    verify_url = url_for('admin.verify_ijazah', student_id=student.id, _external=True)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    current_year = dt.now().year
    school_info = {
        'name': 'MDT Miftahul Hidayah',
        'npsn': 'PENDING_NPSN',
        'address': 'Alamat Lengkap Madrasah',
        'principal': 'Nama Kepala MDT',
        'graduation_date': dt.now().strftime('%d %B %Y')
    }

    return render_template('admin/ijazah_print.html', 
                           student=student, 
                           classroom=classroom,
                           academic_year=academic_year,
                           school_info=school_info,
                           qr_code=qr_base64,
                           verify_url=verify_url,
                           current_year=current_year)

@admin_bp.route('/ijazah/verify/<int:student_id>')
def verify_ijazah(student_id):
    """Halaman verifikasi keaslian ijazah via QR Code"""
    student = Student.query.get_or_404(student_id)
    
    cs = ClassroomStudent.query.filter_by(student_id=student_id).first()
    classroom = cs.classroom if cs else None
    academic_year = cs.academic_year if cs and cs.academic_year else None
    
    verified = True  # Karena student ada di database
    
    return render_template('admin/ijazah_verify.html',
                           student=student,
                           classroom=classroom,
                           academic_year=academic_year,
                           verified=verified,
                           verified_at=datetime.now())