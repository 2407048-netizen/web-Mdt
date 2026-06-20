# MDT Miftahul Hidayah - Struktur Proyek (Manual Scaffold)

Dikarenakan PHP/Composer tidak terdeteksi pada *environment* saat ini, sistem ini dibuat dalam bentuk draf *scaffolding*.
File-file utama (Database Migrations dan Aturan Validasi) telah diletakkan pada folder yang semestinya:

- `database/migrations/2024_01_01_000000_create_mdt_core_tables.php` (Skema Database Lengkap)
- `app/Rules/ValidPrayerSessionDay.php` (Logika Validasi Jadwal)

## Langkah Selanjutnya (Jika PHP & Composer sudah tersedia):

1. **Inisialisasi Proyek**:
   Pindahkan/salin folder `database` dan `app` dari direktori ini ke dalam proyek Laravel baru Anda.
   ```bash
   composer create-project laravel/laravel mdt-app
   ```

2. **Instalasi Dependensi Utama**:
   ```bash
   composer require filament/filament:"^3.2" -W
   composer require spatie/laravel-permission
   composer require spatie/laravel-activitylog
   php artisan filament:install --panels
   ```

3. **Struktur Panel Filament (Rekomendasi Arsitektur)**:
   Gunakan command artisan berikut untuk membuat *Clusters* dan *Resources* agar sesuai dengan rancangan:

   *Panel Admin (Finansial & Master Data)*
   ```bash
   php artisan filament:cluster AcademicMaster
   php artisan filament:cluster Finance
   php artisan filament:cluster Inventory

   php artisan filament:resource Teacher --cluster=AcademicMaster
   php artisan filament:resource Student --cluster=AcademicMaster
   php artisan filament:resource SppPayment --cluster=Finance
   php artisan filament:resource Expense --cluster=Finance
   php artisan filament:resource Item --cluster=Inventory
   ```

   *Panel Guru (Akademik & Presensi)*
   Anda dapat membuat panel Filament baru khusus guru:
   ```bash
   php artisan filament:panel teacher
   ```
   Lalu buat resources yang terikat ke panel tersebut:
   ```bash
   php artisan filament:resource Attendance --panel=teacher
   php artisan filament:resource TahfidzProgress --panel=teacher
   php artisan filament:resource TeacherJournal --panel=teacher
   ```

4. **Kebijakan Akses (Policies)**:
   Pastikan Anda men-generate *Policies* untuk membatasi akses guru hanya ke data miliknya:
   ```bash
   php artisan make:policy AttendancePolicy --model=Attendance
   ```
