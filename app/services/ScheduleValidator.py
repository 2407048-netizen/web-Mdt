from datetime import datetime
from app.models import SessionRule

class ScheduleValidator:
    """
    Validasi khusus untuk membatasi input absensi berdasarkan jadwal.
    Contoh: Tidak boleh absen di hari libur, atau hari Jumat Magrib wajib Tawasulan.
    """
    
    @staticmethod
    def is_valid_for_attendance(date_obj, session_name):
        # 0 = Monday, ..., 4 = Friday, 6 = Sunday
        day_of_week = date_obj.weekday()
        
        # Check rule from DB
        rule = SessionRule.query.filter_by(
            day_of_week=day_of_week,
            prayer_session=session_name
        ).first()

        if not rule:
            # If no rule defined, assume it's valid
            return True, None

        if rule.is_holiday:
            return False, "Tidak dapat mengisi absensi pada hari libur."

        if rule.is_tawasulan:
            return False, "Sesi ini dikhususkan untuk Tawasulan. Gunakan menu Tawasulan."

        return True, None
