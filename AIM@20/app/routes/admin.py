from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (User, Task, Goal, Achievement, UserProductivity, PomodoroSession,
                       Schedule, ScheduleTask, ScheduleBreak, AIChat, Quiz, QuizQuestion,
                       QuizAttempt, QuizAnswer, UserSettings, EnergyPattern, Notification,
                       GoalProgressHistory, Milestone)
from functools import wraps
import json
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with system overview"""
    # Get system statistics
    total_users = User.query.count()
    total_tasks = Task.query.count()
    total_goals = Goal.query.count()
    total_sessions = PomodoroSession.query.count()

    # Get recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(10).all()

    # Get user activity stats
    active_users_today = UserProductivity.query.filter(
        UserProductivity.date == datetime.utcnow().date()
    ).distinct(UserProductivity.user_id).count()

    # System health check
    db_status = "Healthy"
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception as e:
        db_status = f"Error: {str(e)}"

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_tasks=total_tasks,
                         total_goals=total_goals,
                         total_sessions=total_sessions,
                         recent_users=recent_users,
                         recent_tasks=recent_tasks,
                         active_users_today=active_users_today,
                         db_status=db_status)

@admin_bp.route('/users')
@admin_required
def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    search = request.args.get('search', '')
    if search:
        users_query = User.query.filter(
            (User.username.contains(search)) |
            (User.email.contains(search))
        )
    else:
        users_query = User.query

    users_pagination = users_query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/users.html',
                         users=users_pagination.items,
                         pagination=users_pagination,
                         search=search)

@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """View detailed user information"""
    user = User.query.get_or_404(user_id)

    # Get user's statistics
    user_tasks = Task.query.filter_by(user_id=user_id).all()
    user_goals = Goal.query.filter_by(user_id=user_id).all()
    user_achievements = Achievement.query.filter_by(user_id=user_id).all()
    user_sessions = PomodoroSession.query.filter_by(user_id=user_id).all()
    user_productivity = UserProductivity.query.filter_by(user_id=user_id).all()

    # Calculate stats
    completed_tasks = len([t for t in user_tasks if t.completed])
    completed_goals = len([g for g in user_goals if g.achieved])
    total_study_time = sum(p.hours_studied for p in user_productivity)

    stats = {
        'total_tasks': len(user_tasks),
        'completed_tasks': completed_tasks,
        'total_goals': len(user_goals),
        'completed_goals': completed_goals,
        'total_achievements': len(user_achievements),
        'total_sessions': len(user_sessions),
        'total_study_hours': total_study_time,
        'avg_productivity': sum(p.productivity_score for p in user_productivity) / len(user_productivity) if user_productivity else 0
    }

    return render_template('admin/user_detail.html',
                         user=user,
                         tasks=user_tasks[-10:],  # Last 10 tasks
                         goals=user_goals[-5:],   # Last 5 goals
                         achievements=user_achievements[-10:],  # Last 10 achievements
                         sessions=user_sessions[-10:],  # Last 10 sessions
                         stats=stats)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user and all their data"""
    user = User.query.get_or_404(user_id)

    if user.username == 'admin':
        flash('Cannot delete admin user.', 'error')
        return redirect(url_for('admin.users'))

    try:
        # Delete user's data in correct order (respecting foreign keys)

        # Delete complex relationships first
        # Delete quiz-related data
        QuizAnswer.query.filter(
            QuizAnswer.attempt_id.in_(
                db.session.query(QuizAttempt.id).filter_by(user_id=user_id)
            )
        ).delete(synchronize_session=False)

        QuizAttempt.query.filter_by(user_id=user_id).delete()
        QuizQuestion.query.filter(
            QuizQuestion.quiz_id.in_(
                db.session.query(Quiz.id).filter_by(user_id=user_id)
            )
        ).delete(synchronize_session=False)
        Quiz.query.filter_by(user_id=user_id).delete()

        # Delete AI chat history
        AIChat.query.filter_by(user_id=user_id).delete()

        # Delete schedule-related data (must be before tasks)
        ScheduleBreak.query.filter(
            ScheduleBreak.schedule_task_id.in_(
                db.session.query(ScheduleTask.id).filter(
                    ScheduleTask.schedule_id.in_(
                        db.session.query(Schedule.id).filter_by(user_id=user_id)
                    )
                )
            )
        ).delete(synchronize_session=False)

        ScheduleTask.query.filter(
            ScheduleTask.schedule_id.in_(
                db.session.query(Schedule.id).filter_by(user_id=user_id)
            )
        ).delete(synchronize_session=False)

        Schedule.query.filter_by(user_id=user_id).delete()

        # Delete energy patterns
        EnergyPattern.query.filter_by(user_id=user_id).delete()

        # Delete notifications
        Notification.query.filter_by(user_id=user_id).delete()

        # Delete goals and related data
        GoalProgressHistory.query.filter(
            GoalProgressHistory.goal_id.in_(
                db.session.query(Goal.id).filter_by(user_id=user_id)
            )
        ).delete(synchronize_session=False)

        Milestone.query.filter(
            Milestone.goal_id.in_(
                db.session.query(Goal.id).filter_by(user_id=user_id)
            )
        ).delete(synchronize_session=False)

        Goal.query.filter_by(user_id=user_id).delete()

        # Delete tasks and related data
        PomodoroSession.query.filter_by(user_id=user_id).delete()
        Achievement.query.filter_by(user_id=user_id).delete()
        UserProductivity.query.filter_by(user_id=user_id).delete()
        Task.query.filter_by(user_id=user_id).delete()

        # Delete user settings
        UserSettings.query.filter_by(user_id=user_id).delete()

        # Finally delete the user
        db.session.delete(user)
        db.session.commit()

        flash(f'User {user.username} and all associated data deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    """Toggle user's admin status"""
    user = User.query.get_or_404(user_id)

    # Prevent self-demotion
    if user.id == current_user.id:
        flash('You cannot modify your own admin status.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = "granted" if user.is_admin else "revoked"
    flash(f'Admin privileges {status} for user {user.username}.', 'success')

    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/system')
@admin_required
def system_info():
    """System information and maintenance"""
    # Database information
    db_stats = {
        'total_users': User.query.count(),
        'total_tasks': Task.query.count(),
        'total_goals': Goal.query.count(),
        'total_sessions': PomodoroSession.query.count(),
        'total_achievements': Achievement.query.count(),
        'total_productivity_records': UserProductivity.query.count()
    }

    # Get database size (approximate)
    try:
        result = db.session.execute(db.text("SELECT SUM(pg_total_relation_size(relname::regclass)) FROM pg_stat_user_tables"))
        db_size_bytes = result.scalar()
        db_stats['db_size'] = f"{db_size_bytes / (1024*1024):.2f} MB" if db_size_bytes else "Unknown"
    except:
        db_stats['db_size'] = "Cannot determine (SQLite)"

    return render_template('admin/system.html', db_stats=db_stats)

@admin_bp.route('/maintenance/cleanup', methods=['POST'])
@admin_required
def cleanup_data():
    """Clean up old/invalid data"""
    try:
        # Remove old productivity records (older than 1 year)
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        old_records = UserProductivity.query.filter(
            UserProductivity.date < cutoff_date
        ).delete()

        # Remove completed tasks older than 6 months
        task_cutoff = datetime.utcnow() - timedelta(days=180)
        old_tasks = Task.query.filter(
            Task.completed == True,
            Task.updated_at < task_cutoff
        ).delete()

        db.session.commit()

        flash(f'Cleanup completed: {old_records} old productivity records and {old_tasks} old completed tasks removed.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Cleanup failed: {str(e)}', 'error')

    return redirect(url_for('admin.system_info'))

@admin_bp.route('/backup')
@admin_required
def backup():
    """Database backup functionality"""
    # This would implement database backup in a production environment
    flash('Database backup functionality not implemented yet.', 'warning')
    return redirect(url_for('admin.system_info'))

@admin_bp.route('/api/users/stats')
@admin_required
def user_stats_api():
    """API endpoint for user statistics"""
    # Get user registration stats over time
    user_stats = db.session.execute(db.text("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM user
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    """)).fetchall()

    # Get task completion stats
    task_stats = db.session.execute(db.text("""
        SELECT DATE(updated_at) as date, COUNT(*) as count
        FROM task
        WHERE completed = 1
        GROUP BY DATE(updated_at)
        ORDER BY date DESC
        LIMIT 30
    """)).fetchall()

    return jsonify({
        'user_registrations': [{'date': str(stat[0]), 'count': stat[1]} for stat in user_stats],
        'task_completions': [{'date': str(stat[0]), 'count': stat[1]} for stat in task_stats]
    })