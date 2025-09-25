from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import UserSettings

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Display and update user settings"""
    # Get or create user settings
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    if request.method == 'POST':
        # Update settings from form data
        user_settings.pomodoro_work_duration = int(request.form.get('pomodoro_work_duration', 25))
        user_settings.pomodoro_break_duration = int(request.form.get('pomodoro_break_duration', 5))
        user_settings.long_break_duration = int(request.form.get('long_break_duration', 15))
        user_settings.sessions_until_long_break = int(request.form.get('sessions_until_long_break', 4))

        user_settings.notifications_enabled = 'notifications_enabled' in request.form
        user_settings.goal_deadline_reminders = 'goal_deadline_reminders' in request.form
        user_settings.goal_achievement_notifications = 'goal_achievement_notifications' in request.form
        user_settings.reminder_days_before = int(request.form.get('reminder_days_before', 3))

        user_settings.tts_enabled = 'tts_enabled' in request.form
        user_settings.stt_enabled = 'stt_enabled' in request.form
        user_settings.language = request.form.get('language', 'en')
        user_settings.timezone = request.form.get('timezone', 'Africa/Lagos')

        # Preferred study times (JSON)
        preferred_times = []
        times_data = request.form.getlist('preferred_times[]')
        for time_str in times_data:
            if time_str.strip():
                preferred_times.append(time_str.strip())
        user_settings.set_preferred_times(preferred_times)

        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings/index.html', user_settings=user_settings)

@settings_bp.route('/api/update', methods=['POST'])
@login_required
def api_update():
    """API endpoint to update individual settings via AJAX"""
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'})

    # Update individual settings
    for key, value in data.items():
        if hasattr(user_settings, key):
            if key in ['notifications_enabled', 'goal_deadline_reminders', 'goal_achievement_notifications', 'tts_enabled', 'stt_enabled']:
                setattr(user_settings, key, bool(value))
            elif key in ['pomodoro_work_duration', 'pomodoro_break_duration', 'long_break_duration', 'sessions_until_long_break', 'reminder_days_before']:
                setattr(user_settings, key, int(value))
            elif key == 'preferred_times':
                if isinstance(value, list):
                    user_settings.set_preferred_times(value)
            else:
                setattr(user_settings, key, value)

    db.session.commit()
    return jsonify({'success': True})

@settings_bp.route('/reset', methods=['POST'])
@login_required
def reset():
    """Reset settings to defaults"""
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if user_settings:
        # Reset to defaults
        user_settings.pomodoro_work_duration = 25
        user_settings.pomodoro_break_duration = 5
        user_settings.long_break_duration = 15
        user_settings.sessions_until_long_break = 4
        user_settings.preferred_study_times = None
        user_settings.notifications_enabled = True
        user_settings.goal_deadline_reminders = True
        user_settings.goal_achievement_notifications = True
        user_settings.reminder_days_before = 3
        user_settings.tts_enabled = False
        user_settings.stt_enabled = False
        user_settings.language = 'en'
        user_settings.timezone = 'Africa/Lagos'

        db.session.commit()
        flash('Settings reset to defaults!', 'info')
    else:
        flash('No settings found to reset.', 'warning')

    return redirect(url_for('settings.index'))