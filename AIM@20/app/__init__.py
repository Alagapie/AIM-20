from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
import os

from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bootstrap = Bootstrap()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV') or 'development'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.tasks import tasks_bp
    app.register_blueprint(tasks_bp)

    from app.routes.goals import goals_bp
    app.register_blueprint(goals_bp)

    from app.routes.ai_tutor import ai_tutor_bp
    app.register_blueprint(ai_tutor_bp)

    from app.routes.schedules import schedules_bp
    app.register_blueprint(schedules_bp)

    from app.routes.pomodoro import pomodoro_bp
    app.register_blueprint(pomodoro_bp)

    from app.routes.quotes import quotes_bp
    app.register_blueprint(quotes_bp, url_prefix='/quotes')

    from app.routes.settings import settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from app.routes.insights import insights_bp
    app.register_blueprint(insights_bp, url_prefix='/insights')

    from app.routes.gamification import gamification_bp
    app.register_blueprint(gamification_bp, url_prefix='/gamification')

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Import models so SQLAlchemy knows about them
    from app import models

    # Register context processor for navigation data
    @app.context_processor
    def inject_navigation_data():
        from flask_login import current_user
        from app.models import Task, Goal

        if current_user.is_authenticated:
            # Get pending tasks count
            pending_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=False).count()

            # Get active goals count
            active_goals_count = Goal.query.filter_by(user_id=current_user.id, achieved=False).count()

            return {
                'pending_tasks_count': pending_tasks_count,
                'active_goals_count': active_goals_count
            }

        return {
            'pending_tasks_count': 0,
            'active_goals_count': 0
        }

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))