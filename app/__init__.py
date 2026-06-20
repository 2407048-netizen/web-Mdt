from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# 1. Definisikan db dan login_manager di level global (agar bisa di-import di models.py)
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    # 2. Buat App Instance
    app = Flask(__name__)
    
    # 3. Konfigurasi
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci-rahasia-default')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mdt.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 4. Hubungkan extension ke app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # 5. User Loader (PENTING: Pastikan ada di sini atau di auth.py)
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 6. Import Routes DI DALAM FUNGSI (Menghindari Circular Import)
    from app.routes import dashboard, auth, absensi
    
    # 7. Register Blueprints
    app.register_blueprint(dashboard.dashboard_bp, url_prefix='/admin')
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(absensi.absensi_bp)

    return app