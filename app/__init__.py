from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Definisikan db dan login_manager di level global (agar bisa di-import di models.py)
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    # Buat App Instance
    app = Flask(__name__)
    
    # Konfigurasi
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci-rahasia-default')
    
    # FIX: Gunakan /tmp folder untuk Vercel (read-only file system)
    if os.environ.get('VERCEL'):
        # Vercel hanya bisa tulis di /tmp
        db_path = 'sqlite:////tmp/mdt.db'
    else:
        # Lokal tetap pakai instance folder
        db_path = os.environ.get('DATABASE_URL', 'sqlite:///mdt.db')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Hubungkan extension ke app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # User Loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# GANTI BARIS 40 MENJADI:
# GANTI BARIS 40 MENJADI:
from app.routes import admin, auth, guru

# GANTI BARIS 43-45 MENJADI:
app.register_blueprint(admin.admin_bp, url_prefix='/admin')
app.register_blueprint(auth.auth_bp)
app.register_blueprint(guru.guru_bp, url_prefix='/guru')

    return app