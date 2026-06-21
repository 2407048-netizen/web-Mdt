from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret')
    
    if os.environ.get('VERCEL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/mdt.db'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mdt.db')
        
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app.routes import admin, auth, guru
    
    # PASTIKAN 3 BARIS INI HANYA MUNCUL 1 KALI:
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    app.register_blueprint(auth.auth_bp)  # ← CUMA 1 KALI
    app.register_blueprint(guru.guru_bp, url_prefix='/guru')

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app