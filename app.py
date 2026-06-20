# app.py (atau main.py) - Entry Point
from app import create_app
from app.database import db

app = create_app()

def get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True

def seed_database():
    from app.models import (User, AcademicYear, Classroom, Subject,
                             Student, ClassroomStudent, Schedule)
    from datetime import date

    # -- Tahun Ajaran --
    year, _ = get_or_create(AcademicYear, name='2024/2025', defaults={'is_active': True})

    # -- Users --
    admin, created = get_or_create(User, email='admin@miftahulhidayah.com',
                                   defaults={'username': 'admin', 'role': 'admin', 'is_active': True})
    if created:
        admin.set_password('password')

    guru1, created = get_or_create(User, email='ahmad@miftahulhidayah.com',
                                   defaults={'username': 'Ustadz Ahmad', 'role': 'guru', 'is_active': True})
    if created:
        guru1.set_password('password')

    guru2, created = get_or_create(User, email='fatimah@miftahulhidayah.com',
                                   defaults={'username': 'Ustadzah Fatimah', 'role': 'guru', 'is_active': True})
    if created:
        guru2.set_password('password')

    # -- Classrooms --
    subuh_1, _ = get_or_create(Classroom, name='Subuh 1', defaults={'level': 1})
    subuh_2, _ = get_or_create(Classroom, name='Subuh 2', defaults={'level': 1})
    subuh_3, _ = get_or_create(Classroom, name='Subuh 3', defaults={'level': 1})
    dzuhur_1, _ = get_or_create(Classroom, name='Dzuhur 1', defaults={'level': 2})
    ashar_1, _ = get_or_create(Classroom, name='Ashar 1', defaults={'level': 3})
    ashar_2, _ = get_or_create(Classroom, name='Ashar 2', defaults={'level': 3})
    ashar_3, _ = get_or_create(Classroom, name='Ashar 3', defaults={'level': 3})
    
    magrib_classes = []
    for i in range(1, 10):
        cls, _ = get_or_create(Classroom, name=f'Magrib {i}', defaults={'level': 4})
        magrib_classes.append(cls)

    # -- Subjects --
    subj_quran, _ = get_or_create(Subject, code='QRN', defaults={'name': 'Al-Quran / Tilawah'})
    subj_fiqih, _ = get_or_create(Subject, code='FQH', defaults={'name': 'Fiqih'})
    subj_nahwu, _ = get_or_create(Subject, code='NHS', defaults={'name': 'Nahwu Shorof'})
    get_or_create(Subject, code='HDT', defaults={'name': 'Hadits Arbain'})
    get_or_create(Subject, code='AKD', defaults={'name': 'Akidah Akhlak'})
    get_or_create(Subject, code='TWS', defaults={'name': 'Tawasulan'})

    # -- Students + Classroom Pivot --
    students_data = [
        {'nis': '2324001', 'name': 'Ahmad Fauzi', 'gender': 'L', 'phone': '08111222333', 'class': subuh_1},
        {'nis': '2324002', 'name': 'Siti Aisyah', 'gender': 'P', 'phone': '08222333444', 'class': subuh_2},
        {'nis': '2324003', 'name': 'Muhammad Rizky', 'gender': 'L', 'phone': '08333444555', 'class': subuh_3},
        {'nis': '2324004', 'name': 'Fatimah Azzahra', 'gender': 'P', 'phone': '08444555666', 'class': dzuhur_1},
        {'nis': '2324005', 'name': 'Umar Abdillah', 'gender': 'L', 'phone': '08555666777', 'class': ashar_1},
        {'nis': '2324006', 'name': 'Khadijah Salimah', 'gender': 'P', 'phone': '08666777888', 'class': ashar_2},
        {'nis': '2324007', 'name': 'Ali bin Abi Thalib', 'gender': 'L', 'phone': '08777888999', 'class': ashar_3},
        {'nis': '2324008', 'name': 'Aisyah Humaira', 'gender': 'P', 'phone': '08888999000', 'class': magrib_classes[0]},
        {'nis': '2324009', 'name': 'Hamzah Abdul', 'gender': 'L', 'phone': '08999000111', 'class': magrib_classes[1]},
        {'nis': '2324010', 'name': 'Bilal bin Rabah', 'gender': 'L', 'phone': '08123456789', 'class': magrib_classes[2]},
        {'nis': '2324011', 'name': 'Zainab binti Ali', 'gender': 'P', 'phone': '08987654321', 'class': magrib_classes[3]},
        {'nis': '2324012', 'name': 'Ja\'far Ash-Shidiq', 'gender': 'L', 'phone': '08543210987', 'class': magrib_classes[4]},
        {'nis': '2324013', 'name': 'Khadijah binti Khuwailid', 'gender': 'P', 'phone': '08123123123', 'class': magrib_classes[5]},
        {'nis': '2324014', 'name': 'Abdurrahman bin Auf', 'gender': 'L', 'phone': '08123123124', 'class': magrib_classes[6]},
        {'nis': '2324015', 'name': 'Sa\'ad bin Abi Waqqas', 'gender': 'L', 'phone': '08123123125', 'class': magrib_classes[7]},
        {'nis': '2324016', 'name': 'Salman Al-Farisi', 'gender': 'L', 'phone': '08123123126', 'class': magrib_classes[8]},
    ]
    
    for s in students_data:
        student, _ = get_or_create(Student, nis=s['nis'], defaults={
            'name': s['name'], 'gender': s['gender'],
            'parent_phone': s['phone'], 'birth_date': date(2015, 1, 1)
        })
        get_or_create(ClassroomStudent,
                      student_id=student.id,
                      classroom_id=s['class'].id,
                      academic_year_id=year.id)

    # -- Schedules --
    subuh_classes = [subuh_1, subuh_2, subuh_3]
    for i, cls in enumerate(subuh_classes):
        get_or_create(Schedule, teacher_id=guru1.id, classroom_id=cls.id,
                      subject_id=subj_quran.id, day_of_week=(i % 5), prayer_session='Subuh')

    get_or_create(Schedule, teacher_id=guru1.id, classroom_id=dzuhur_1.id,
                  subject_id=subj_fiqih.id, day_of_week=0, prayer_session='Dzuhur')

    ashar_classes = [ashar_1, ashar_2, ashar_3]
    for i, cls in enumerate(ashar_classes):
        get_or_create(Schedule, teacher_id=guru1.id, classroom_id=cls.id,
                      subject_id=subj_nahwu.id, day_of_week=(i % 5), prayer_session='Ashar')

    for i, cls in enumerate(magrib_classes):
        get_or_create(Schedule, teacher_id=guru1.id, classroom_id=cls.id,
                      subject_id=subj_quran.id, day_of_week=(i % 5), prayer_session='Magrib')

    db.session.commit()
    print("[READY] Database seeded and ready!")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(debug=True, port=5000)