from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app import db
from app.models import UserProductivity, Task, Goal, PomodoroSession
from datetime import datetime, timedelta
import json

insights_bp = Blueprint('insights', __name__)

@insights_bp.route('/')
@login_required
def index():
    """Display productivity insights and analytics"""
    # Get productivity data for the last 30 days
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)

    productivity_data = UserProductivity.query.filter(
        UserProductivity.user_id == current_user.id,
        UserProductivity.date >= start_date,
        UserProductivity.date <= end_date
    ).order_by(UserProductivity.date).all()

    # Calculate current week stats
    week_start = end_date - timedelta(days=7)
    week_data = UserProductivity.query.filter(
        UserProductivity.user_id == current_user.id,
        UserProductivity.date >= week_start,
        UserProductivity.date <= end_date
    ).all()

    # Calculate averages and insights
    insights = calculate_insights(productivity_data, week_data)

    return render_template('insights/index.html',
                         productivity_data=productivity_data,
                         insights=insights)

@insights_bp.route('/api/productivity-data')
@login_required
def api_productivity_data():
    """API endpoint for productivity data (for charts)"""
    days = int(request.args.get('days', 30))
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    data = UserProductivity.query.filter(
        UserProductivity.user_id == current_user.id,
        UserProductivity.date >= start_date,
        UserProductivity.date <= end_date
    ).order_by(UserProductivity.date).all()

    chart_data = {
        'dates': [p.date.strftime('%Y-%m-%d') for p in data],
        'hours_studied': [p.hours_studied for p in data],
        'tasks_completed': [p.tasks_completed for p in data],
        'goals_progressed': [p.goals_progressed for p in data],
        'productivity_score': [p.productivity_score for p in data],
        'burnout_risk': [p.burnout_risk for p in data],
        'focus_score': [p.average_focus_score for p in data]
    }

    return jsonify(chart_data)

@insights_bp.route('/recommendations')
@login_required
def recommendations():
    """Display personalized recommendations"""
    # Get recent productivity data
    recent_data = UserProductivity.query.filter_by(user_id=current_user.id)\
        .order_by(UserProductivity.date.desc()).limit(7).all()

    # Generate recommendations based on data
    recommendations = generate_recommendations(recent_data)

    return render_template('insights/recommendations.html', recommendations=recommendations)

@insights_bp.route('/burnout-prediction')
@login_required
def burnout_prediction():
    """Display burnout risk analysis"""
    # Get recent data for burnout analysis
    recent_data = UserProductivity.query.filter_by(user_id=current_user.id)\
        .order_by(UserProductivity.date.desc()).limit(14).all()

    # Calculate burnout risk trends
    burnout_analysis = analyze_burnout_risk(recent_data)

    return render_template('insights/burnout.html', analysis=burnout_analysis)

@insights_bp.route('/api/update-productivity', methods=['POST'])
@login_required
def update_productivity():
    """Update productivity data for today"""
    data = request.get_json()
    today = datetime.utcnow().date()

    # Get or create today's productivity record
    productivity = UserProductivity.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()

    if not productivity:
        productivity = UserProductivity(user_id=current_user.id, date=today)
        db.session.add(productivity)

    # Update fields if provided
    if 'hours_studied' in data:
        productivity.hours_studied = data['hours_studied']
    if 'tasks_completed' in data:
        productivity.tasks_completed = data['tasks_completed']
    if 'goals_progressed' in data:
        productivity.goals_progressed = data['goals_progressed']
    if 'focus_score' in data:
        productivity.average_focus_score = data['focus_score']

    # Calculate productivity score and burnout risk
    productivity.productivity_score = calculate_productivity_score(productivity)
    productivity.burnout_risk = calculate_burnout_risk(productivity)

    # Generate recommendations
    recommendations = generate_daily_recommendations(productivity)
    productivity.set_recommendations(recommendations)

    db.session.commit()

    return jsonify({'success': True, 'productivity_score': productivity.productivity_score})

def calculate_insights(productivity_data, week_data):
    """Calculate various productivity insights"""
    insights = {}

    if not productivity_data:
        return insights

    # Calculate averages
    total_hours = sum(p.hours_studied for p in productivity_data)
    total_tasks = sum(p.tasks_completed for p in productivity_data)
    total_goals = sum(p.goals_progressed for p in productivity_data)
    avg_productivity = sum(p.productivity_score for p in productivity_data) / len(productivity_data)
    avg_burnout = sum(p.burnout_risk for p in productivity_data) / len(productivity_data)
    avg_focus = sum(p.average_focus_score for p in productivity_data) / len(productivity_data)

    insights['total_hours'] = round(total_hours, 1)
    insights['total_tasks'] = total_tasks
    insights['total_goals'] = total_goals
    insights['avg_productivity'] = round(avg_productivity, 1)
    insights['avg_burnout'] = round(avg_burnout, 1)
    insights['avg_focus'] = round(avg_focus, 1)

    # Weekly comparisons
    if week_data:
        week_hours = sum(p.hours_studied for p in week_data)
        week_tasks = sum(p.tasks_completed for p in week_data)
        insights['week_hours'] = round(week_hours, 1)
        insights['week_tasks'] = week_tasks

        # Calculate trends
        if len(productivity_data) >= 14:
            recent_week = productivity_data[-7:]
            previous_week = productivity_data[-14:-7]

            recent_avg = sum(p.productivity_score for p in recent_week) / len(recent_week)
            previous_avg = sum(p.productivity_score for p in previous_week) / len(previous_week)

            insights['productivity_trend'] = "up" if recent_avg > previous_avg else "down" if recent_avg < previous_avg else "stable"

    # Best performing days
    if productivity_data:
        best_day = max(productivity_data, key=lambda x: x.productivity_score)
        insights['best_day'] = {
            'date': best_day.date.strftime('%A, %B %d'),
            'score': best_day.productivity_score,
            'hours': best_day.hours_studied,
            'tasks': best_day.tasks_completed
        }

    # Current streak analysis
    insights['current_streak'] = calculate_current_streak(productivity_data)

    return insights

def calculate_productivity_score(productivity):
    """Calculate productivity score based on various factors"""
    score = 0

    # Hours studied (max 40 points)
    if productivity.hours_studied > 0:
        score += min(productivity.hours_studied * 10, 40)

    # Tasks completed (max 30 points)
    score += min(productivity.tasks_completed * 5, 30)

    # Goals progressed (max 20 points)
    score += min(productivity.goals_progressed * 10, 20)

    # Focus score (max 10 points)
    score += productivity.average_focus_score

    return round(min(score, 100), 1)

def calculate_burnout_risk(productivity):
    """Calculate burnout risk based on recent activity with more nuanced analysis"""
    risk = 10  # Baseline risk - everyone has some level of stress

    # Hours studied factor (0-40 points)
    if productivity.hours_studied > 10:
        risk += 40  # Extremely high study load
    elif productivity.hours_studied > 8:
        risk += 30  # Very high study load
    elif productivity.hours_studied > 6:
        risk += 20  # High study load
    elif productivity.hours_studied > 4:
        risk += 10  # Moderate study load
    elif productivity.hours_studied < 1:
        risk += 15  # Very low activity might indicate avoidance

    # Focus score factor (0-25 points)
    if productivity.average_focus_score < 30:
        risk += 25  # Severely low focus
    elif productivity.average_focus_score < 50:
        risk += 15  # Low focus
    elif productivity.average_focus_score < 70:
        risk += 5   # Below average focus

    # Task completion vs goal progress ratio (0-20 points)
    if productivity.tasks_completed > 0:
        goal_progress_ratio = productivity.goals_progressed / productivity.tasks_completed
        if goal_progress_ratio < 0.1 and productivity.tasks_completed > 5:
            risk += 20  # Many tasks but little meaningful progress
        elif goal_progress_ratio < 0.3 and productivity.tasks_completed > 3:
            risk += 10  # Some progress but could be better

    # Productivity score factor (0-25 points)
    if productivity.productivity_score < 20:
        risk += 25  # Very low productivity
    elif productivity.productivity_score < 40:
        risk += 15  # Low productivity
    elif productivity.productivity_score < 60:
        risk += 5   # Below average productivity

    # Task volume factor (0-15 points)
    if productivity.tasks_completed > 15:
        risk += 15  # Extremely high task volume
    elif productivity.tasks_completed > 10:
        risk += 10  # Very high task volume
    elif productivity.tasks_completed > 7:
        risk += 5   # High task volume

    return round(min(max(risk, 0), 100), 1)

def generate_recommendations(recent_data):
    """Generate personalized recommendations"""
    recommendations = []

    if not recent_data:
        return recommendations

    avg_hours = sum(p.hours_studied for p in recent_data) / len(recent_data)
    avg_tasks = sum(p.tasks_completed for p in recent_data) / len(recent_data)
    avg_focus = sum(p.average_focus_score for p in recent_data) / len(recent_data)

    if avg_hours < 2:
        recommendations.append({
            'type': 'study_time',
            'message': 'Consider increasing your daily study time to build better habits.',
            'action': 'Schedule dedicated study blocks in your calendar.'
        })

    if avg_focus < 60:
        recommendations.append({
            'type': 'focus',
            'message': 'Your focus levels could be improved. Try the Pomodoro technique.',
            'action': 'Use shorter study sessions with regular breaks.'
        })

    if avg_tasks < 3:
        recommendations.append({
            'type': 'productivity',
            'message': 'Try breaking large tasks into smaller, manageable ones.',
            'action': 'Create a daily task list with achievable goals.'
        })

    return recommendations

def generate_daily_recommendations(productivity):
    """Generate daily recommendations based on current data"""
    recommendations = []

    if productivity.hours_studied > 6:
        recommendations.append("You've studied for over 6 hours today. Consider taking a longer break to prevent burnout.")

    if productivity.tasks_completed >= 5:
        recommendations.append("Great job completing multiple tasks! Reward yourself with a short break.")

    if productivity.average_focus_score < 50:
        recommendations.append("Your focus seems low today. Try taking a 10-minute walk or doing some light exercise.")

    if productivity.productivity_score > 80:
        recommendations.append("Excellent productivity today! Keep up the great work.")

    return recommendations

def analyze_burnout_risk(recent_data):
    """Analyze burnout risk over time"""
    if not recent_data:
        return {'risk_level': 'low', 'message': 'Not enough data to analyze burnout risk.'}

    avg_burnout = sum(p.burnout_risk for p in recent_data) / len(recent_data)

    if avg_burnout < 30:
        risk_level = 'low'
        message = 'Your burnout risk is low. Keep maintaining a healthy balance.'
    elif avg_burnout < 60:
        risk_level = 'medium'
        message = 'Moderate burnout risk detected. Consider taking more breaks and ensuring adequate rest.'
    else:
        risk_level = 'high'
        message = 'High burnout risk! Please take immediate steps to reduce stress and workload.'

    return {
        'risk_level': risk_level,
        'average_risk': round(avg_burnout, 1),
        'message': message,
        'data_points': len(recent_data)
    }

def calculate_current_streak(productivity_data):
    """Calculate current study streak"""
    if not productivity_data:
        return 0

    streak = 0
    for p in reversed(productivity_data):
        if p.hours_studied > 0 or p.tasks_completed > 0:
            streak += 1
        else:
            break

    return streak