from app.database import db
from app.models import Student, Classroom, AcademicYear, StudentHistory

class MassPromotionService:
    """
    Service untuk menangani kenaikan kelas massal di akhir tahun ajaran.
    """

    @staticmethod
    def promote_all_students(from_year_id, to_year_id):
        try:
            # 1. Ambil semua siswa aktif
            students = Student.query.filter_by(status='active').all()
            
            for student in students:
                # Cari history kelas saat ini (asumsi data terakhir di from_year_id)
                current_history = StudentHistory.query.filter_by(
                    student_id=student.id, 
                    academic_year_id=from_year_id
                ).order_by(StudentHistory.id.desc()).first()
                
                if current_history:
                    current_class = Classroom.query.get(current_history.classroom_id)
                    
                    # Logic kenaikan kelas (level + 1)
                    # Di skenario nyata, mungkin perlu logic mapping ID kelas tujuan
                    next_level = current_class.level + 1
                    next_class = Classroom.query.filter_by(level=next_level).first()
                    
                    if next_class:
                        # Buat history baru untuk tahun ajaran baru
                        new_history = StudentHistory(
                            student_id=student.id,
                            classroom_id=next_class.id,
                            academic_year_id=to_year_id,
                            status='passed'
                        )
                        db.session.add(new_history)
                    else:
                        # Jika mentok (Lulus)
                        student.status = 'graduated'
                        
            db.session.commit()
            return True, "Kenaikan kelas massal berhasil diproses."
        except Exception as e:
            db.session.rollback()
            return False, f"Terjadi kesalahan: {str(e)}"
