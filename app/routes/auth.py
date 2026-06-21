# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, current_user
from app import db  # Menggunakan db dari app/__init__.py
from app.models import User, Subject, Classroom, PRAYER_SESSIONS, DAY_NAMES
import json
import time

# PENTING: Nama variabel Blueprint WAJIB 'auth_bp'
auth_bp = Blueprint('auth', __name__)

# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────
def _redirect_by_role(user):
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('guru.dashboard'))

# ─────────────────────────────────────────────
#  ROOT: Halaman Pilih Role
# ─────────────────────────────────────────────
from datetime import datetime  # Pastikan ada di atas file

@auth_bp.route('/login')
def login():
    """Halaman pemilihan login (Admin atau Guru)."""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    return render_template('auth/choose_role.html', now=datetime.now())

# ─────────────────────────────────────────────
#  ADMIN LOGIN
# ─────────────────────────────────────────────
# Pastikan baris ini ada di PALING ATAS file auth.py
from datetime import datetime

@auth_bp.route('/login')
def login():
    """Halaman pemilihan login (Admin atau Guru)."""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    
    # TAMBAHKAN: now=datetime.now() 👇
    return render_template('auth/choose_role.html', now=datetime.now())

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Email atau kata sandi salah.', 'error')
            return redirect(url_for('auth.admin_login'))

        if user.role != 'admin':
            flash('Akun ini bukan akun Admin. Silakan gunakan halaman login Guru.', 'error')
            return redirect(url_for('auth.admin_login'))

        login_user(user, remember=remember)
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html')

# ─────────────────────────────────────────────
#  GURU LOGIN
# ─────────────────────────────────────────────
@auth_bp.route('/guru/login', methods=['GET', 'POST'])
def guru_login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Email atau kata sandi salah.', 'error')
            return redirect(url_for('auth.guru_login'))

        if user.role != 'guru':
            flash('Akun ini bukan akun Guru/Ustadz. Silakan gunakan halaman login Admin.', 'error')
            return redirect(url_for('auth.guru_login'))

        if not user.is_active:
            flash('Akun Anda belum diaktivasi oleh Admin. Silakan hubungi Admin.', 'error')
            return redirect(url_for('auth.guru_login'))

        login_user(user, remember=remember)
        return redirect(url_for('guru.dashboard'))

    return render_template('auth/guru_login.html')

# ─────────────────────────────────────────────
#  DAFTAR AKUN GURU BARU (REGISTER)
# ─────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == 'POST':
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        prayer_session   = request.form.get('prayer_session')
        classroom_id     = request.form.get('classroom_id', type=int)
        teaching_days_list = request.form.getlist('teaching_days')
        teaching_days    = ",".join(teaching_days_list) if teaching_days_list else ""
        
        # Compile subjects per teaching day into a dict and serialize to JSON
        subjects_dict = {}
        for day in teaching_days_list:
            if day.isdigit():
                day_idx = int(day)
                val = request.form.get(f'subject_book_{day_idx}', '').strip()
                if val:
                    subjects_dict[day_idx] = val
                    
        subject_book_json = json.dumps(subjects_dict) if subjects_dict else ""

        # ✅ PERBAIKAN: Auto-Create Subject dengan penanganan error unik
        unique_subjects = set(subjects_dict.values())
        
        for sub_name in unique_subjects:
            if sub_name:
                sub_name_clean = sub_name.strip()
                # Buat kode otomatis (3 huruf pertama uppercase)
                sub_code = sub_name_clean[:3].upper()
                
                # Cek apakah subject sudah ada (berdasarkan nama ATAU kode)
                existing_subject = Subject.query.filter(
                    (Subject.name == sub_name_clean) | (Subject.code == sub_code)
                ).first()
                
                if not existing_subject:
                    try:
                        new_subject = Subject(name=sub_name_clean, code=sub_code)
                        db.session.add(new_subject)
                    except Exception as e:
                        db.session.rollback()
                        print(f"Subject creation skipped for {sub_name}: {e}")
        
        # Flush untuk memastikan ID subject tersedia sebelum menyimpan user
        if unique_subjects:
            db.session.flush()

        # Validasi OTP
        if not session.get('email_verified') or session.get('otp_email') != email:
            flash('Harap verifikasi email Anda terlebih dahulu menggunakan OTP.', 'error')
            return redirect(url_for('auth.register'))

        # Validasi Form
        if not username or not email or not password or not prayer_session or not classroom_id or not teaching_days or not subject_book_json:
            flash('Harap lengkapi semua field (termasuk Pelajaran/Kitab per Hari Mengajar dan minimal satu Hari Mengajar).', 'error')
            return redirect(url_for('auth.register'))

        if len(password) < 6:
            flash('Kata sandi minimal 6 karakter.', 'error')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Konfirmasi kata sandi tidak cocok.', 'error')
            return redirect(url_for('auth.register'))

        if not email.lower().endswith('@gmail.com'):
            flash('Registrasi dibatasi: Harap gunakan akun Google (@gmail.com).', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar. Silakan gunakan email lain.', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Nama sudah digunakan. Silakan gunakan nama lain.', 'error')
            return redirect(url_for('auth.register'))

        # Buat akun guru baru (belum aktif, menunggu approval admin)
        user = User(username=username, email=email, role='guru', is_active=False,
                    prayer_session=prayer_session, classroom_id=classroom_id,
                    teaching_days=teaching_days, subject_book=subject_book_json)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Pendaftaran berhasil! Akun Anda akan diaktivasi oleh Admin.', 'success')
        return redirect(url_for('auth.guru_login'))

    # Untuk Halaman GET (Menampilkan Form)
    classrooms = Classroom.query.order_by(Classroom.level).all()
    
    session_classrooms = {s: [] for s in PRAYER_SESSIONS}
    for c in classrooms:
        for s in PRAYER_SESSIONS:
            if c.name.startswith(s):
                session_classrooms[s].append({'id': c.id, 'name': f"Kelas {c.name} (Level {c.level})"})
                break

    return render_template('auth/register.html', classrooms=classrooms,
                           prayer_sessions=PRAYER_SESSIONS,
                           session_classrooms=session_classrooms,
                           day_names=DAY_NAMES)

# ─────────────────────────────────────────────
#  OTP EMAIL VERIFICATION
# ─────────────────────────────────────────────
@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    from app.services.email_service import EmailService

    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status': 'error', 'message': 'Email wajib diisi.'})
    if not email.lower().endswith('@gmail.com'):
        return jsonify({'status': 'error', 'message': 'Harap gunakan email Google (@gmail.com).'})
        
    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email ini sudah terdaftar.'})

    otp_code = EmailService.generate_otp()
    session['otp_code'] = otp_code
    session['otp_email'] = email
    session['otp_expiry'] = time.time() + 300  # 5 menit
    session['email_verified'] = False

    sent_smtp = EmailService.send_otp_email(email, otp_code)
    
    response_data = {
        'status': 'success',
        'message': 'OTP berhasil dikirim ke email Anda!' if sent_smtp else 'Kode OTP berhasil dibuat (Mode Pengembangan)!'
    }
    if not sent_smtp:
        response_data['demo_otp'] = otp_code
        
    return jsonify(response_data)

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email', '').strip()
    code = request.form.get('code', '').strip()

    if not email or not code:
        return jsonify({'status': 'error', 'message': 'Email dan Kode OTP wajib diisi.'})

    saved_code = session.get('otp_code')
    saved_email = session.get('otp_email')
    expiry = session.get('otp_expiry', 0)

    if not saved_code or saved_email != email:
        return jsonify({'status': 'error', 'message': 'Silakan minta OTP baru terlebih dahulu.'})

    if time.time() > expiry:
        return jsonify({'status': 'error', 'message': 'Kode OTP telah kedaluwarsa. Silakan minta kode baru.'})

    if saved_code != code:
        return jsonify({'status': 'error', 'message': 'Kode OTP salah. Harap periksa kembali.'})

    session['email_verified'] = True
    return jsonify({'status': 'success', 'message': 'Email berhasil diverifikasi!'})

# ─────────────────────────────────────────────
#  RESET KATA SANDI (FORGOT PASSWORD)
# ─────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    return render_template('auth/forgot_password.html')

@auth_bp.route('/forgot-password/send-otp', methods=['POST'])
def forgot_password_send_otp():
    from app.services.email_service import EmailService

    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status': 'error', 'message': 'Email wajib diisi.'})
    if not email.lower().endswith('@gmail.com'):
        return jsonify({'status': 'error', 'message': 'Harap gunakan email Google (@gmail.com).'})
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Email tidak terdaftar di sistem.'})

    otp_code = EmailService.generate_otp()
    session['reset_otp_code'] = otp_code
    session['reset_otp_email'] = email
    session['reset_otp_expiry'] = time.time() + 300
    session['reset_otp_verified'] = False

    sent_smtp = EmailService.send_otp_email(email, otp_code)
    
    response_data = {
        'status': 'success',
        'message': 'OTP berhasil dikirim ke email Anda!' if sent_smtp else 'Kode OTP reset berhasil dibuat (Mode Pengembangan)!'
    }
    if not sent_smtp:
        response_data['demo_otp'] = otp_code
        
    return jsonify(response_data)

@auth_bp.route('/forgot-password/verify-otp', methods=['POST'])
def forgot_password_verify_otp():
    email = request.form.get('email', '').strip()
    code = request.form.get('code', '').strip()

    if not email or not code:
        return jsonify({'status': 'error', 'message': 'Email dan Kode OTP wajib diisi.'})

    saved_code = session.get('reset_otp_code')
    saved_email = session.get('reset_otp_email')
    expiry = session.get('reset_otp_expiry', 0)

    if not saved_code or saved_email != email:
        return jsonify({'status': 'error', 'message': 'Silakan minta OTP baru terlebih dahulu.'})

    if time.time() > expiry:
        return jsonify({'status': 'error', 'message': 'Kode OTP telah kedaluwarsa. Silakan minta kode baru.'})

    if saved_code != code:
        return jsonify({'status': 'error', 'message': 'Kode OTP salah. Harap periksa kembali.'})

    session['reset_otp_verified'] = True
    return jsonify({'status': 'success', 'message': 'Email berhasil diverifikasi!'})

@auth_bp.route('/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not email or not password or not confirm_password:
        flash('Harap lengkapi semua bidang.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if not session.get('reset_otp_verified') or session.get('reset_otp_email') != email:
        flash('Akses tidak sah. Silakan verifikasi email Anda terlebih dahulu.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if len(password) < 6:
        flash('Kata sandi baru minimal harus 6 karakter.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if password != confirm_password:
        flash('Konfirmasi kata sandi baru tidak cocok.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User tidak ditemukan.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user.set_password(password)
    db.session.commit()

    session.pop('reset_otp_code', None)
    session.pop('reset_otp_email', None)
    session.pop('reset_otp_expiry', None)
    session.pop('reset_otp_verified', None)

    flash('Kata sandi Anda berhasil diperbarui! Silakan masuk.', 'success')
    return redirect(url_for('auth.guru_login'))

# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    role = current_user.role if current_user.is_authenticated else 'guru'
    logout_user()
    if role == 'admin':
        return redirect(url_for('auth.admin_login'))
    return redirect(url_for('auth.guru_login'))