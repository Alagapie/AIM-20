from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - redirects to dashboard if logged in, otherwise shows landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', title='AIM@20 - AI Study Productivity')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing productivity overview"""
    from app.models import Task, Goal, PomodoroSession, Achievement

    # Get user's recent tasks (pending ones)
    recent_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).limit(5).all()

    # Get user's active goals
    active_goals = Goal.query.filter_by(user_id=current_user.id, achieved=False).limit(3).all()

    # Calculate productivity stats for today
    today = datetime.utcnow().date()
    today_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.created_at >= today
    ).count()

    completed_today = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed == True,
        Task.completed_at >= today
    ).count()

    # Get recent Pomodoro sessions (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = PomodoroSession.query.filter(
        PomodoroSession.user_id == current_user.id,
        PomodoroSession.created_at >= week_ago
    ).limit(10).all()

    total_study_time = sum(session.duration for session in recent_sessions if session.session_type == 'work')

    # Get recent achievements
    recent_achievements = Achievement.query.filter_by(user_id=current_user.id).order_by(
        Achievement.earned_at.desc()
    ).limit(3).all()

    # Navigation data for badges
    pending_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    active_goals_count = Goal.query.filter_by(user_id=current_user.id, achieved=False).count()

    return render_template('dashboard.html',
                         title='Dashboard',
                         recent_tasks=recent_tasks,
                         active_goals=active_goals,
                         today_tasks=today_tasks,
                         completed_today=completed_today,
                         total_study_time=total_study_time,
                         recent_sessions=recent_sessions,
                         recent_achievements=recent_achievements,
                         pending_tasks_count=pending_tasks_count,
                         active_goals_count=active_goals_count,
                         user_timezone=current_user.user_settings.timezone if current_user.user_settings else 'Africa/Lagos')

@main_bp.route('/search')
@login_required
def search():
    """Global search across tasks, goals, and other content"""
    query = request.args.get('q', '').strip()

    if not query:
        return render_template('search.html', title='Search', query='', results=None)

    # Search in tasks
    from app.models import Task, Goal
    task_results = Task.query.filter(
        Task.user_id == current_user.id,
        db.or_(
            Task.title.contains(query),
            Task.description.contains(query),
            Task.category.contains(query)
        )
    ).limit(10).all()

    # Search in goals
    goal_results = Goal.query.filter(
        Goal.user_id == current_user.id,
        db.or_(
            Goal.title.contains(query),
            Goal.description.contains(query),
            Goal.category.contains(query)
        )
    ).limit(10).all()

    results = {
        'tasks': task_results,
        'goals': goal_results,
        'total': len(task_results) + len(goal_results)
    }

    return render_template('search.html', title='Search Results', query=query, results=results)

@main_bp.route('/about')
def about():
    """About page with project information"""
    return render_template('about.html', title='About AIM20/VISION20')

@main_bp.route('/features')
def features():
    """Features page highlighting all app capabilities"""
    return render_template('features.html', title='Features')

# Error handlers
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500