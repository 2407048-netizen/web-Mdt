# app/routes/guru.py
from datetime import date, datetime
from collections import OrderedDict
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db  # Menggunakan db dari app/__init__.py
from app.models import (Schedule, Classroom, ClassroomStudent, Student,
                         Attendance, Exam, ExamScore, DAY_NAMES, PRAYER_SESSIONS,
                         SppPayment, CashFlow, User)
from app.services.AttendanceService import AttendanceService
import os
import time
import json

# PENTING: Nama variabel Blueprint WAJIB 'guru_bp'
guru_bp = Blueprint('guru', __name__)

@guru_bp.before_request
@login_required
def require_guru():
    if current_user.role not in ('guru', 'admin'):
        abort(403)

# ─────────────────────────────────────────────
#  DASHBOARD: Jadwal Mengajar Hari Ini
# ────────────────────────────────────────────
@guru_bp.route('/dashboard')
def dashboard():
    today      = date.today()
    today_dow  = today.weekday()

    today_schedules = (Schedule.query
                       .filter_by(teacher_id=current_user.id,
                                  day_of_week=today_dow,
                                  is_active=True)
                       .all())

    schedule_status = {}
    for sch in today_schedules:
        count = Attendance.query.filter_by(
            schedule_id=sch.id, date=today
        ).count()
        schedule_status[sch.id] = count > 0

    # Hitung jumlah kelas per sesi dari SEMUA jadwal guru
    session_counts = {}
    for sesi in PRAYER_SESSIONS:
        session_counts[sesi] = (Schedule.query
                                .filter_by(teacher_id=current_user.id,
                                           prayer_session=sesi,
                                           is_active=True)
                                .count())

    return render_template('guru/dashboard.html',
                           today_schedules=today_schedules,
                           schedule_status=schedule_status,
                           today=today,
                           day_name=DAY_NAMES[today_dow],
                           session_counts=session_counts)

# ─────────────────────────────────────────────
#  JADWAL MENGAJAR LENGKAP
# ─────────────────────────────────────────────
@guru_bp.route('/jadwal')
def jadwal():
    all_schedules = (Schedule.query
                     .filter_by(teacher_id=current_user.id, is_active=True)
                     .order_by(Schedule.day_of_week, Schedule.prayer_session)
                     .all())

    schedules_by_day = OrderedDict()
    for sch in all_schedules:
        if sch.day_of_week not in schedules_by_day:
            schedules_by_day[sch.day_of_week] = []
        schedules_by_day[sch.day_of_week].append(sch)

    return render_template('guru/jadwal.html',
                           schedules_by_day=schedules_by_day,
                           day_names=DAY_NAMES)

# ─────────────────────────────────────────────
#  REKAP ABSENSI PER JADWAL
# ─────────────────────────────────────────────
@guru_bp.route('/rekap/<int:schedule_id>')
def rekap_absensi(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)

    if schedule.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)

    # Ambil murid di kelas ini
    pivot = ClassroomStudent.query.filter_by(classroom_id=schedule.classroom_id).all()
    student_ids = [p.student_id for p in pivot]
    students = (Student.query
                .filter(Student.id.in_(student_ids), Student.status == 'active')
                .order_by(Student.name)
                .all())

    # Ambil semua absensi untuk jadwal ini
    all_att = (Attendance.query
               .filter_by(schedule_id=schedule_id)
               .order_by(Attendance.date)
               .all())

    # Kumpulkan tanggal unik
    dates = sorted(set(a.date for a in all_att))

    # Buat map (student_id, date_iso) -> attendance
    attendance_map = {}
    for a in all_att:
        attendance_map[(a.student_id, a.date.isoformat())] = a

    # Stats
    stats = {'hadir': 0, 'sakit': 0, 'izin': 0, 'alpa': 0}
    for a in all_att:
        if a.status in stats:
            stats[a.status] += 1

    return render_template('guru/rekap_absensi.html',
                           schedule=schedule,
                           students=students,
                           dates=dates,
                           attendance_map=attendance_map,
                           stats=stats,
                           total_sessions=len(dates),
                           day_names=DAY_NAMES)

# ─────────────────────────────────────────────
#  ABSENSI MURID
# ─────────────────────────────────────────────
@guru_bp.route('/attendance/<int:schedule_id>', methods=['GET', 'POST'])
def attendance(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)

    # Pastikan jadwal milik guru yang sedang login
    if schedule.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)

    today = date.today()

    # ── Validasi hari libur / Tawasulan ──
    is_valid, message, is_tawasulan = AttendanceService.validate_session(
        schedule.prayer_session, today
    )
    if not is_valid:
        flash(message, 'warning')
        return redirect(url_for('guru.dashboard'))

    # Ambil daftar murid di kelas jadwal ini
    pivot_entries = (ClassroomStudent.query
                     .filter_by(classroom_id=schedule.classroom_id)
                     .all())
    student_ids   = [p.student_id for p in pivot_entries]
    students      = (Student.query
                     .filter(Student.id.in_(student_ids), Student.status == 'active')
                     .order_by(Student.name)
                     .all())

    # Ambil data absensi hari ini jika sudah ada
    existing_records = {
        att.student_id: att
        for att in Attendance.query.filter_by(schedule_id=schedule_id, date=today).all()
    }

    # ── POST: Simpan absensi ──
    if request.method == 'POST':
        attendance_data = []
        for student in students:
            status = request.form.get(f'status_{student.id}', 'hadir')
            notes  = request.form.get(f'notes_{student.id}', '')
            attendance_data.append({
                'student_id': student.id,
                'status': status,
                'notes': notes
            })

        ok, msg = AttendanceService.bulk_save(
            schedule_id=schedule_id,
            attendance_date=today,
            attendance_data=attendance_data,
            recorded_by=current_user.id
        )
        flash(msg, 'success' if ok else 'error')
        return redirect(url_for('guru.rekap_absensi', schedule_id=schedule_id))

    return render_template('guru/attendance.html',
                           schedule=schedule,
                           students=students,
                           existing=existing_records,
                           today=today)

# ─────────────────────────────────────────────
#  MODUL PENDUKUNG
# ─────────────────────────────────────────────
@guru_bp.route('/tawasulan', methods=['GET', 'POST'])
def tawasulan():
    if request.method == 'POST':
        flash("Data absensi Tawasulan berhasil disimpan!", 'success')
        return redirect(url_for('guru.tawasulan'))
    return render_template('guru/tawasulan.html')

@guru_bp.route('/mutabaah', methods=['GET', 'POST'])
def mutabaah():
    if request.method == 'POST':
        flash("Catatan hafalan santri berhasil ditambahkan!", 'success')
        return redirect(url_for('guru.mutabaah'))
    return render_template('guru/mutabaah.html')

# ─────────────────────────────────────────────
#  ULANGAN MINGGUAN
# ─────────────────────────────────────────────
@guru_bp.route('/exams')
def exams():
    my_schedules = Schedule.query.filter_by(
        teacher_id=current_user.id, is_active=True
    ).all()
    schedule_ids = [s.id for s in my_schedules]
    all_exams = (Exam.query
                 .filter(Exam.schedule_id.in_(schedule_ids))
                 .order_by(Exam.date.desc())
                 .all())
    return render_template('guru/exams.html',
                           exams=all_exams,
                           schedules=my_schedules,
                           day_names=DAY_NAMES)

@guru_bp.route('/exams/create', methods=['POST'])
def create_exam():
    title       = request.form.get('title', '').strip()
    schedule_id = request.form.get('schedule_id', type=int)
    exam_date   = request.form.get('date', '')

    if not title or not schedule_id or not exam_date:
        flash('Harap lengkapi semua field.', 'error')
        return redirect(url_for('guru.exams'))

    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.teacher_id != current_user.id:
        abort(403)

    try:
        d = datetime.strptime(exam_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Format tanggal tidak valid.', 'error')
        return redirect(url_for('guru.exams'))

    exam = Exam(title=title, schedule_id=schedule_id,
                date=d, created_by=current_user.id)
    db.session.add(exam)
    db.session.commit()
    flash(f'Ulangan "{title}" berhasil dibuat!', 'success')
    return redirect(url_for('guru.exam_scores', exam_id=exam.id))

@guru_bp.route('/exams/<int:exam_id>', methods=['GET', 'POST'])
def exam_scores(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    schedule = exam.schedule

    if schedule.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)

    # Ambil murid di kelas
    pivot = ClassroomStudent.query.filter_by(classroom_id=schedule.classroom_id).all()
    student_ids = [p.student_id for p in pivot]
    students = (Student.query
                .filter(Student.id.in_(student_ids), Student.status == 'active')
                .order_by(Student.name)
                .all())

    if request.method == 'POST':
        for student in students:
            score_val = request.form.get(f'score_{student.id}', type=float) or 0
            score_val = max(0, min(100, score_val))

            existing = ExamScore.query.filter_by(
                exam_id=exam_id, student_id=student.id
            ).first()
            if existing:
                existing.score = score_val
            else:
                es = ExamScore(exam_id=exam_id, student_id=student.id, score=score_val)
                db.session.add(es)

        db.session.commit()
        flash('Nilai berhasil disimpan!', 'success')
        return redirect(url_for('guru.exam_scores', exam_id=exam_id))

    scores_map = {
        s.student_id: s
        for s in ExamScore.query.filter_by(exam_id=exam_id).all()
    }

    return render_template('guru/exam_scores.html',
                           exam=exam, students=students,
                           scores_map=scores_map)

# ─────────────────────────────────────────────
#  PROFIL SAYA (EDIT PROFIL)
# ─────────────────────────────────────────────
@guru_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    classrooms = Classroom.query.order_by(Classroom.level).all()
    
    session_classrooms = {s: [] for s in PRAYER_SESSIONS}
    for c in classrooms:
        for s in PRAYER_SESSIONS:
            if c.name.startswith(s):
                session_classrooms[s].append({'id': c.id, 'name': c.name})
                break

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        teaching_days_list = request.form.getlist('teaching_days')
        prayer_session = request.form.get('prayer_session')
        classroom_id = request.form.get('classroom_id', type=int)

        if not username:
            flash('Nama Lengkap tidak boleh kosong.', 'error')
            return redirect(url_for('guru.profile'))

        # Compile subjects per teaching day into a dict and serialize to JSON
        subjects_dict = {}
        for day in teaching_days_list:
            if day.isdigit():
                day_idx = int(day)
                val = request.form.get(f'subject_book_{day_idx}', '').strip()
                if val:
                    subjects_dict[day_idx] = val

        subject_book_json = json.dumps(subjects_dict) if subjects_dict else ""

        # Update fields
        current_user.username = username
        current_user.subject_book = subject_book_json
        current_user.prayer_session = prayer_session
        current_user.classroom_id = classroom_id if classroom_id else None

        # Update teaching_days
        if teaching_days_list:
            current_user.teaching_days = ','.join(teaching_days_list)
        else:
            current_user.teaching_days = ''

        # Handle Profile Picture Upload
        file = request.files.get('profile_pic')
        if file and file.filename:
            # Validate extension
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            if ext not in {'png', 'jpg', 'jpeg', 'gif'}:
                flash('Format gambar tidak didukung (harus PNG, JPG, JPEG, atau GIF).', 'error')
                return redirect(url_for('guru.profile'))

            from flask import current_app

            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_pics')
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique clean filename
            filename = f"guru_{current_user.id}_{int(time.time())}.{ext}"
            filepath = os.path.join(upload_dir, filename)

            # Clean up old profile picture if exists
            if current_user.profile_pic:
                old_path = os.path.join(upload_dir, current_user.profile_pic)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

            # Save the new file
            file.save(filepath)
            current_user.profile_pic = filename

        db.session.commit()
        flash('Profil Anda berhasil diperbarui!', 'success')
        return redirect(url_for('guru.profile'))

    return render_template('guru/profile.html',
                           day_names=DAY_NAMES,
                           classrooms=classrooms,
                           prayer_sessions=PRAYER_SESSIONS,
                           session_classrooms=session_classrooms,
                           current_session=current_user.prayer_session,
                           current_classroom_id=current_user.classroom_id)


# ─────────────────────────────────────────────
#  SUMBANGAN PEMBINAAN PENDIDIKAN (SPP)
# ─────────────────────────────────────────────
@guru_bp.route('/spp', methods=['GET'])
def spp():
    if current_user.prayer_session != 'Magrib':
        abort(403)
        
    # Ambil daftar kelas yang diampu guru (kelas utama & kelas terjadwal)
    my_classroom_ids = set()
    if current_user.classroom_id:
        my_classroom_ids.add(current_user.classroom_id)
    
    # Ambil kelas dari jadwal
    schedules = Schedule.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    for s in schedules:
        my_classroom_ids.add(s.classroom_id)
        
    classrooms = Classroom.query.filter(Classroom.id.in_(list(my_classroom_ids))).all()
    if not classrooms:
        classrooms = Classroom.query.all() # Fallback ke semua kelas jika tidak punya kelas
        
    selected_classroom_id = request.args.get('classroom_id', type=int)
    if not selected_classroom_id and classrooms:
        selected_classroom_id = classrooms[0].id
        
    selected_year = request.args.get('year', type=int, default=datetime.now().year)
    
    # Ambil murid di kelas terpilih
    students = []
    if selected_classroom_id:
        pivot = ClassroomStudent.query.filter_by(classroom_id=selected_classroom_id).all()
        student_ids = [p.student_id for p in pivot]
        students = (Student.query
                    .filter(Student.id.in_(student_ids), Student.status == 'active')
                    .order_by(Student.name)
                    .all())
                    
    # Ambil pembayaran SPP untuk murid-murid ini pada tahun terpilih
    student_ids_list = [s.id for s in students]
    payments = []
    if student_ids_list:
        payments = SppPayment.query.filter(
            SppPayment.student_id.in_(student_ids_list),
            SppPayment.year == selected_year
        ).all()
        
    # Buat map (student_id, month) -> payment
    payments_map = {}
    for p in payments:
        payments_map[(p.student_id, p.month)] = p
        
    months_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    years_range = range(datetime.now().year - 2, datetime.now().year + 3)
    
    return render_template('guru/spp.html',
                           classrooms=classrooms,
                           selected_classroom_id=selected_classroom_id,
                           selected_year=selected_year,
                           students=students,
                           payments_map=payments_map,
                           months_names=months_names,
                           years_range=years_range)

@guru_bp.route('/spp/pay', methods=['POST'])
def spp_pay():
    if current_user.prayer_session != 'Magrib' and current_user.role != 'admin':
        abort(403)
        
    student_id = request.form.get('student_id', type=int)
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    amount = request.form.get('amount', type=float, default=50000.0)
    paid_date_str = request.form.get('paid_date', '')
    
    redirect_to_admin = request.form.get('redirect_to_admin') == 'true'
    dest = 'admin.spp' if redirect_to_admin else 'guru.spp'
    
    if not student_id or not month or not year:
        flash('Data tidak lengkap.', 'error')
        return redirect(url_for(dest))
        
    try:
        p_date = datetime.strptime(paid_date_str, '%Y-%m-%d').date() if paid_date_str else datetime.utcnow().date()
    except ValueError:
        p_date = datetime.utcnow().date()
        
    # Check if payment already exists
    existing = SppPayment.query.filter_by(student_id=student_id, month=month, year=year).first()
    if existing:
        flash('Pembayaran untuk bulan tersebut sudah tercatat.', 'warning')
        return redirect(url_for(dest, classroom_id=request.form.get('classroom_id'), year=year))
        
    payment = SppPayment(
        student_id=student_id,
        month=month,
        year=year,
        amount=amount,
        paid_date=p_date,
        recorded_by=current_user.id
    )
    db.session.add(payment)
    db.session.commit()
    
    std = Student.query.get(student_id)
    
    months_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    flash(f'Pembayaran SPP {std.name} bulan {months_names.get(month)} berhasil disimpan!', 'success')
    return redirect(url_for(dest, classroom_id=request.form.get('classroom_id'), year=year))

@guru_bp.route('/spp/delete/<int:id>', methods=['POST'])
def spp_delete(id):
    if current_user.prayer_session != 'Magrib' and current_user.role != 'admin':
        abort(403)
        
    payment = SppPayment.query.get_or_404(id)
    
    redirect_to_admin = request.form.get('redirect_to_admin') == 'true'
    dest = 'admin.spp' if redirect_to_admin else 'guru.spp'
    
    # Hanya boleh dihapus oleh pencatat atau admin
    if payment.recorded_by != current_user.id and current_user.role != 'admin':
        abort(403)
        
    db.session.delete(payment)
    db.session.commit()
    flash('Pembayaran SPP berhasil dihapus/dibatalkan.', 'success')
    return redirect(url_for(dest, classroom_id=request.form.get('classroom_id'), year=payment.year))