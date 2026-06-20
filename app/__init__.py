from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# 1. INI HARUS ADA DI PALING ATAS
app = Flask(__name__) 

# Konfigurasi
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rahasia')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mdt.db')

# Inisialisasi Extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# 2. IMPORT MODEL & ROUTES (Di Bagian Bawah)
# Hapus komentar di bawah ini sesuai nama file Anda
from app import models 
# from app.routes import dashboard, auth, absensi 
# dst...