from flask import Flask
from app.config import Config
from app.database import db, migrate
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = 'auth.guru_login'
login_manager.login_message = "Harap masuk untuk mengakses halaman ini."

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints here
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.guru import bp as guru_bp
    app.register_blueprint(guru_bp, url_prefix='/guru')

    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {'now': datetime.now()}

    return app

from app.models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
