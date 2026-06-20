from datetime import date
from app.database import db
from app.models import Attendance, ActivityLog, HOLIDAY_RULES, TAWASULAN_DAY
from app.services.WhatsAppGateway import WhatsAppGateway

class AttendanceService:
    """
    Service untuk menyimpan absensi massal dan memvalidasi hari libur sesi salat.
    """

    @staticmethod
    def validate_session(prayer_session: str, check_date: date = None):
        """
        Mengembalikan (is_valid, message, is_tawasulan).
        Aturan MDT:
          Subuh  → LIBUR Jumat
          Dzuhur → LIBUR Sabtu
          Ashar  → LIBUR Sabtu
          Magrib → LIBUR Selasa; Jumat = Tawasulan (bukan absen biasa)
        """
        if check_date is None:
            check_date = date.today()

        day = check_date.weekday()  # 0=Senin, …, 6=Minggu

        holidays = HOLIDAY_RULES.get(prayer_session, [])
        if day in holidays:
            from app.models import DAY_NAMES
            return False, f"Sesi {prayer_session} LIBUR pada hari {DAY_NAMES[day]}.", False

        # Khusus Jumat Magrib = Tawasulan
        if prayer_session == 'Magrib' and day == TAWASULAN_DAY:
            return False, "Sesi Magrib Jumat dialihkan ke Agenda Tawasulan.", True

        return True, None, False

    @staticmethod
    def bulk_save(schedule_id: int, attendance_date: date,
                  attendance_data: list, recorded_by: int):
        """
        Menyimpan/mengupdate absensi banyak murid sekaligus.
        attendance_data = [{'student_id': int, 'status': str, 'notes': str}, …]
        """
        try:
            wa = WhatsAppGateway()
            saved_count = 0
            alpa_students = []

            for item in attendance_data:
                student_id = item['student_id']
                status     = item.get('status', 'hadir')
                notes      = item.get('notes', '')

                # Upsert: update jika sudah ada, insert jika belum
                existing = Attendance.query.filter_by(
                    student_id=student_id,
                    schedule_id=schedule_id,
                    date=attendance_date
                ).first()

                if existing:
                    existing.status      = status
                    existing.notes       = notes
                    existing.recorded_by = recorded_by
                else:
                    new_att = Attendance(
                        student_id=student_id,
                        schedule_id=schedule_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        recorded_by=recorded_by
                    )
                    db.session.add(new_att)
                    saved_count += 1

                if status == 'alpa':
                    from app.models import Student
                    student = Student.query.get(student_id)
                    if student:
                        alpa_students.append(student)

            # Activity Log
            log = ActivityLog(
                user_id=recorded_by,
                action='SIMPAN_ABSENSI',
                detail=f'Schedule #{schedule_id}, Tanggal {attendance_date}, '
                       f'{len(attendance_data)} murid diproses.'
            )
            db.session.add(log)
            db.session.commit()

            # Kirim notifikasi WA untuk murid yang Alpa
            for student in alpa_students:
                if student.parent_phone:
                    wa.send_absence_alert(
                        student_name=student.name,
                        parent_phone=student.parent_phone,
                        absence_date=str(attendance_date)
                    )

            return True, f"Absensi berhasil disimpan. {len(alpa_students)} notifikasi WA dikirim."

        except Exception as e:
            db.session.rollback()
            return False, f"Gagal menyimpan absensi: {str(e)}"
