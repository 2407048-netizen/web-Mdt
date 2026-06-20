from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# 1. DEFINISIKAN 'app' DI PALING ATAS (WAJIB)
app = Flask(__name__)

# 2. Konfigurasi Dasar
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci-rahasia-default')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mdt.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Inisialisasi Extension
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# 4. IMPORT ROUTES DI BAGIAN PALING BAWAH (Hindari Circular Import)
# Ganti nama blueprint sesuai file routes Anda
from app.routes import dashboard, auth, absensi 

# 5. Register Blueprint
app.register_blueprint(dashboard.dashboard_bp, url_prefix='/admin')
app.register_blueprint(auth.auth_bp)
app.register_blueprint(absensi.absensi_bp)