from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import PomodoroSession, Task, UserSettings, UserProductivity
from datetime import datetime, timedelta
import json

pomodoro_bp = Blueprint('pomodoro', __name__, url_prefix='/pomodoro')

@pomodoro_bp.route('/')
@login_required
def index():
    """Pomodoro Timer main page"""
    # Get user's settings
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        # Create default settings if they don't exist
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    # Get available tasks for selection
    tasks = Task.query.filter_by(user_id=current_user.id, completed=False)\
                     .order_by(Task.priority.desc(), Task.due_date.asc())\
                     .limit(10).all()

    # Get recent sessions for statistics
    recent_sessions = PomodoroSession.query.filter_by(user_id=current_user.id)\
                                          .order_by(PomodoroSession.created_at.desc())\
                                          .limit(10).all()

    # Calculate today's statistics
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = PomodoroSession.query.filter(
        PomodoroSession.user_id == current_user.id,
        PomodoroSession.created_at >= today_start
    ).all()

    today_work_sessions = [s for s in today_sessions if s.session_type == 'work']
    today_break_sessions = [s for s in today_sessions if s.session_type == 'break']

    today_stats = {
        'work_sessions': len(today_work_sessions),
        'break_sessions': len(today_break_sessions),
        'total_work_time': sum(s.duration or 0 for s in today_work_sessions),
        'total_break_time': sum(s.duration or 0 for s in today_break_sessions),
        'completed_sessions': len([s for s in today_work_sessions if s.completed])
    }

    return render_template('pomodoro/index.html',
                          title='Pomodoro Timer',
                          user_settings=user_settings,
                          tasks=tasks,
                          recent_sessions=recent_sessions,
                          today_stats=today_stats)

@pomodoro_bp.route('/start-session', methods=['POST'])
@login_required
def start_session():
    """Start a new Pomodoro session"""
    data = request.get_json()
    session_type = data.get('session_type', 'work')
    task_id = data.get('task_id')
    duration = data.get('duration')

    # Get user settings for default durations
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()

    if not duration:
        if session_type == 'work':
            duration = user_settings.pomodoro_work_duration if user_settings else 25
        else:
            # Check if it's a long break
            recent_work_sessions = PomodoroSession.query.filter_by(
                user_id=current_user.id,
                session_type='work'
            ).order_by(PomodoroSession.created_at.desc()).limit(4).all()

            completed_sessions = len([s for s in recent_work_sessions if s.completed])
            sessions_until_long = user_settings.sessions_until_long_break if user_settings else 4

            if completed_sessions > 0 and completed_sessions % sessions_until_long == 0:
                duration = user_settings.long_break_duration if user_settings else 15
            else:
                duration = user_settings.pomodoro_break_duration if user_settings else 5

    # Create new session
    session = PomodoroSession(
        user_id=current_user.id,
        task_id=task_id,
        session_type=session_type,
        start_time=datetime.utcnow(),
        duration=duration
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        'success': True,
        'session_id': session.id,
        'duration': duration,
        'session_type': session_type,
        'start_time': session.start_time.isoformat()
    })

@pomodoro_bp.route('/complete-session/<int:session_id>', methods=['POST'])
@login_required
def complete_session(session_id):
    """Mark a session as completed"""
    session = PomodoroSession.query.filter_by(
        id=session_id,
        user_id=current_user.id
    ).first_or_404()

    if session.end_time:
        return jsonify({'error': 'Session already completed'}), 400

    end_time = datetime.utcnow()
    actual_duration = int((end_time - session.start_time).total_seconds() / 60)

    session.end_time = end_time
    session.duration = actual_duration
    session.completed = True

    # Update productivity data if it's a work session
    if session.session_type == 'work' and session.duration:
        _update_productivity_data(session)

    db.session.commit()

    return jsonify({
        'success': True,
        'actual_duration': actual_duration,
        'session_type': session.session_type
    })

@pomodoro_bp.route('/interrupt-session/<int:session_id>', methods=['POST'])
@login_required
def interrupt_session(session_id):
    """Mark a session as interrupted"""
    session = PomodoroSession.query.filter_by(
        id=session_id,
        user_id=current_user.id
    ).first_or_404()

    if session.end_time:
        return jsonify({'error': 'Session already ended'}), 400

    end_time = datetime.utcnow()
    actual_duration = int((end_time - session.start_time).total_seconds() / 60)

    session.end_time = end_time
    session.duration = actual_duration
    session.interrupted = True

    db.session.commit()

    return jsonify({
        'success': True,
        'actual_duration': actual_duration,
        'interrupted': True
    })

@pomodoro_bp.route('/current-session')
@login_required
def get_current_session():
    """Get the current active session"""
    # Find the most recent session without end_time
    current_session = PomodoroSession.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).order_by(PomodoroSession.start_time.desc()).first()

    if current_session:
        elapsed_seconds = int((datetime.utcnow() - current_session.start_time).total_seconds())
        return jsonify({
            'active': True,
            'session_id': current_session.id,
            'session_type': current_session.session_type,
            'start_time': current_session.start_time.isoformat(),
            'duration': current_session.duration,
            'elapsed_seconds': elapsed_seconds,
            'task_id': current_session.task_id
        })
    else:
        return jsonify({'active': False})

@pomodoro_bp.route('/statistics')
@login_required
def statistics():
    """Pomodoro statistics page"""
    # Get sessions from the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    sessions = PomodoroSession.query.filter(
        PomodoroSession.user_id == current_user.id,
        PomodoroSession.created_at >= thirty_days_ago
    ).order_by(PomodoroSession.created_at.desc()).all()

    # Calculate statistics
    work_sessions = [s for s in sessions if s.session_type == 'work']
    break_sessions = [s for s in sessions if s.session_type == 'break']

    stats = {
        'total_sessions': len(sessions),
        'work_sessions': len(work_sessions),
        'break_sessions': len(break_sessions),
        'completed_sessions': len([s for s in work_sessions if s.completed]),
        'interrupted_sessions': len([s for s in work_sessions if s.interrupted]),
        'total_work_time': sum(s.duration or 0 for s in work_sessions),
        'total_break_time': sum(s.duration or 0 for s in break_sessions),
        'avg_session_duration': sum(s.duration or 0 for s in work_sessions) / len(work_sessions) if work_sessions else 0,
        'completion_rate': len([s for s in work_sessions if s.completed]) / len(work_sessions) * 100 if work_sessions else 0
    }

    # Daily breakdown for the last 7 days
    daily_stats = []
    for i in range(7):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        day_sessions = [s for s in sessions if day_start <= s.created_at <= day_end]
        day_work_sessions = [s for s in day_sessions if s.session_type == 'work']

        daily_stats.append({
            'date': day.strftime('%Y-%m-%d'),
            'day_name': day.strftime('%A'),
            'sessions': len(day_sessions),
            'work_sessions': len(day_work_sessions),
            'completed': len([s for s in day_work_sessions if s.completed]),
            'work_time': sum(s.duration or 0 for s in day_work_sessions)
        })

    return render_template('pomodoro/statistics.html',
                          title='Pomodoro Statistics',
                          stats=stats,
                          daily_stats=daily_stats,
                          sessions=sessions[:50])  # Last 50 sessions

def _update_productivity_data(session):
    """Update user's productivity data based on completed session"""
    today = datetime.utcnow().date()

    productivity = UserProductivity.query.filter_by(
        user_id=session.user_id,
        date=today
    ).first()

    if not productivity:
        productivity = UserProductivity(
            user_id=session.user_id,
            date=today
        )
        db.session.add(productivity)

    # Update productivity metrics
    productivity.hours_studied = (productivity.hours_studied or 0) + (session.duration / 60.0)
    productivity.tasks_completed = (productivity.tasks_completed or 0) + (1 if session.task_id else 0)

    # Simple productivity scoring (can be enhanced with AI)
    base_score = 70  # Base productivity score
    completion_bonus = 10 if session.completed else 0
    focus_bonus = 5 if session.duration and session.duration >= 20 else 0  # Longer focused sessions

    productivity.productivity_score = min(100, base_score + completion_bonus + focus_bonus)

    # Calculate burnout risk (simple heuristic)
    recent_sessions = PomodoroSession.query.filter(
        PomodoroSession.user_id == session.user_id,
        PomodoroSession.created_at >= datetime.utcnow() - timedelta(days=7)
    ).all()

    weekly_hours = sum(s.duration or 0 for s in recent_sessions if s.session_type == 'work') / 60.0
    burnout_risk = min(100, weekly_hours * 2)  # Simple burnout calculation
    productivity.burnout_risk = burnout_risk

    db.session.commit()