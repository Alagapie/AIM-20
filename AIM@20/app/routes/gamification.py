from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Achievement, UserProductivity, Task, Goal, PomodoroSession
from datetime import datetime, timedelta
import json

gamification_bp = Blueprint('gamification', __name__)

@gamification_bp.route('/')
@login_required
def index():
    """Display user's achievements and gamification stats"""
    # Get user's achievements
    achievements = Achievement.query.filter_by(user_id=current_user.id)\
        .order_by(Achievement.earned_at.desc()).all()

    # Calculate current streaks and stats
    stats = calculate_gamification_stats(current_user.id)

    # Check for new achievements
    new_achievements = check_for_new_achievements(current_user.id)

    # Get earned achievement types
    earned_types = [ach.achievement_type for ach in achievements]

    # Calculate progress for unearned achievements
    progress_badges = []
    available_badges = [
        {'type': 'first_task', 'title': 'Getting Started', 'description': 'Complete your first task', 'icon': 'fas fa-check-circle', 'target': 1},
        {'type': 'task_master', 'title': 'Task Master', 'description': 'Complete 10 tasks', 'icon': 'fas fa-tasks', 'target': 10},
        {'type': 'streak_master', 'title': 'Streak Master', 'description': '7-day study streak', 'icon': 'fas fa-fire', 'target': 7}
    ]

    for badge in available_badges:
        if badge['type'] not in earned_types:
            progress = calculate_badge_progress(current_user.id, badge['type'])
            badge_with_progress = badge.copy()
            badge_with_progress.update(progress)
            progress_badges.append(badge_with_progress)

    return render_template('gamification/index.html',
                         achievements=achievements,
                         stats=stats,
                         new_achievements=new_achievements,
                         progress_badges=progress_badges)

@gamification_bp.route('/badges')
@login_required
def badges():
    """Display all available badges and progress"""
    all_badges = get_all_available_badges()
    user_badges = Achievement.query.filter_by(user_id=current_user.id).all()
    earned_badge_ids = [badge.achievement_type for badge in user_badges]

    # Calculate stats
    stats = {
        'total_badges_earned': len(user_badges),
        'total_badges': len(all_badges),
        'recent_badges': len([b for b in user_badges if (datetime.utcnow() - b.earned_at).days <= 30])
    }

    return render_template('gamification/badges.html',
                          badges=all_badges,
                          earned_badge_ids=earned_badge_ids,
                          stats=stats)

@gamification_bp.route('/streaks')
@login_required
def streaks():
    """Display current and longest streaks"""
    streak_stats = calculate_detailed_streak_data(current_user.id)
    return render_template('gamification/streaks.html', streak_stats=streak_stats)

@gamification_bp.route('/leaderboard')
@login_required
def leaderboard():
    """Display leaderboard with rankings"""
    # Get leaderboard data for all users
    leaderboard_data = get_leaderboard_data()
    current_user_stats = calculate_gamification_stats(current_user.id)

    # Find current user's rank
    current_user_rank = None
    current_user_rank_change = None
    for i, user_data in enumerate(leaderboard_data):
        if user_data['user_id'] == current_user.id:
            current_user_rank = i + 1
            # Calculate rank change (simplified - would need historical data)
            current_user_rank_change = 0  # Placeholder
            break

    current_user_info = {
        'rank': current_user_rank,
        'rank_change': current_user_rank_change,
        'total_points': current_user_stats['total_points'],
        'level': current_user_stats['level'],
        'current_streak': current_user_stats['current_streak'],
        'completed_tasks': Task.query.filter_by(user_id=current_user.id, completed=True).count(),
        'completed_goals': Goal.query.filter_by(user_id=current_user.id, achieved=True).count(),
        'avg_productivity': calculate_avg_productivity(current_user.id)
    }

    return render_template('gamification/leaderboard.html',
                          leaderboard=leaderboard_data,
                          current_user_stats=current_user_info)

@gamification_bp.route('/api/check-achievements')
@login_required
def check_achievements():
    """API endpoint to check for new achievements"""
    new_achievements = check_for_new_achievements(current_user.id)
    return jsonify({
        'new_achievements': [{'id': ach.id, 'achievement_type': ach.achievement_type,
                             'title': ach.title, 'description': ach.description,
                             'earned_at': ach.earned_at.isoformat() if ach.earned_at else None}
                            for ach in new_achievements],
        'count': len(new_achievements)
    })

@gamification_bp.route('/api/award-achievement', methods=['POST'])
@login_required
def award_achievement():
    """Manually award an achievement (for testing/admin)"""
    data = request.get_json()
    achievement_type = data.get('type')

    if achievement_type:
        achievement = award_achievement_to_user(current_user.id, achievement_type)
        if achievement:
            return jsonify({'success': True, 'achievement': {'id': achievement.id, 'achievement_type': achievement.achievement_type,
                                                             'title': achievement.title, 'description': achievement.description,
                                                             'earned_at': achievement.earned_at.isoformat() if achievement.earned_at else None}})

    return jsonify({'success': False, 'error': 'Achievement type not found'})

def calculate_gamification_stats(user_id):
    """Calculate overall gamification statistics"""
    # Count achievements
    total_achievements = Achievement.query.filter_by(user_id=user_id).count()

    # Calculate streaks
    streak_data = calculate_streak_data(user_id)

    # Calculate points/scoring system
    productivity_data = UserProductivity.query.filter_by(user_id=user_id).all()
    total_points = sum(p.productivity_score for p in productivity_data)

    # Calculate level based on achievements and activity
    level = calculate_user_level(total_achievements, total_points)

    return {
        'total_achievements': total_achievements,
        'current_streak': streak_data['current_streak'],
        'longest_streak': streak_data['longest_streak'],
        'total_points': total_points,
        'level': level,
        'next_level_points': calculate_next_level_points(level)
    }

def calculate_streak_data(user_id):
    """Calculate streak information"""
    # Get productivity data for streak calculation
    productivity_data = UserProductivity.query.filter_by(user_id=user_id)\
        .order_by(UserProductivity.date.desc()).limit(60).all()

    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    # Calculate current streak (consecutive days with activity)
    today = datetime.utcnow().date()
    for i, p in enumerate(productivity_data):
        expected_date = today - timedelta(days=i)
        if p.date == expected_date and (p.hours_studied > 0 or p.tasks_completed > 0):
            current_streak += 1
        else:
            break

    # Calculate longest streak
    for p in reversed(productivity_data):
        if p.hours_studied > 0 or p.tasks_completed > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 0

    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'streak_history': [{'date': p.date.strftime('%Y-%m-%d'),
                           'active': p.hours_studied > 0 or p.tasks_completed > 0}
                          for p in productivity_data[:30]]
    }

def check_for_new_achievements(user_id):
    """Check if user has earned any new achievements"""
    new_achievements = []

    # Check each achievement type
    achievement_checks = [
        ('first_task', lambda: Task.query.filter_by(user_id=user_id).count() >= 1),
        ('task_master', lambda: Task.query.filter_by(user_id=user_id).count() >= 10),
        ('goal_setter', lambda: Goal.query.filter_by(user_id=user_id).count() >= 1),
        ('goal_achiever', lambda: Goal.query.filter_by(user_id=user_id, achieved=True).count() >= 1),
        ('pomodoro_warrior', lambda: PomodoroSession.query.filter_by(user_id=user_id).count() >= 10),
        ('streak_master', lambda: calculate_streak_data(user_id)['current_streak'] >= 7),
        ('week_warrior', lambda: calculate_weekly_stats(user_id) >= 40),  # 40 hours in a week
        ('early_bird', lambda: check_early_morning_activity(user_id)),
        ('night_owl', lambda: check_late_night_activity(user_id)),
        ('perfectionist', lambda: check_perfect_week(user_id)),
    ]

    existing_achievements = Achievement.query.filter_by(user_id=user_id).all()
    existing_types = [ach.achievement_type for ach in existing_achievements]

    for achievement_type, condition_func in achievement_checks:
        if achievement_type not in existing_types and condition_func():
            achievement = award_achievement_to_user(user_id, achievement_type)
            if achievement:
                new_achievements.append(achievement)

    return new_achievements

def award_achievement_to_user(user_id, achievement_type):
    """Award an achievement to a user"""
    achievement_data = get_achievement_data(achievement_type)
    if not achievement_data:
        return None

    achievement = Achievement(
        user_id=user_id,
        achievement_type=achievement_type,
        title=achievement_data['title'],
        description=achievement_data['description'],
        badge_image=achievement_data.get('badge_image', 'default_badge.png')
    )

    db.session.add(achievement)
    db.session.commit()

    return achievement

def get_achievement_data(achievement_type):
    """Get achievement metadata"""
    achievements = {
        'first_task': {
            'title': 'Getting Started',
            'description': 'Completed your first task',
            'badge_image': 'first_task_badge.png'
        },
        'task_master': {
            'title': 'Task Master',
            'description': 'Completed 10 tasks',
            'badge_image': 'task_master_badge.png'
        },
        'goal_setter': {
            'title': 'Goal Oriented',
            'description': 'Set your first study goal',
            'badge_image': 'goal_setter_badge.png'
        },
        'goal_achiever': {
            'title': 'Goal Achiever',
            'description': 'Achieved your first goal',
            'badge_image': 'goal_achiever_badge.png'
        },
        'pomodoro_warrior': {
            'title': 'Pomodoro Warrior',
            'description': 'Completed 10 Pomodoro sessions',
            'badge_image': 'pomodoro_warrior_badge.png'
        },
        'streak_master': {
            'title': 'Streak Master',
            'description': 'Maintained a 7-day study streak',
            'badge_image': 'streak_master_badge.png'
        },
        'week_warrior': {
            'title': 'Week Warrior',
            'description': 'Studied 40+ hours in a week',
            'badge_image': 'week_warrior_badge.png'
        },
        'early_bird': {
            'title': 'Early Bird',
            'description': 'Most active before 9 AM',
            'badge_image': 'early_bird_badge.png'
        },
        'night_owl': {
            'title': 'Night Owl',
            'description': 'Most active after 10 PM',
            'badge_image': 'night_owl_badge.png'
        },
        'perfectionist': {
            'title': 'Perfectionist',
            'description': 'Perfect study week (7 days straight)',
            'badge_image': 'perfectionist_badge.png'
        }
    }

    return achievements.get(achievement_type)

def get_all_available_badges():
    """Get all available badges with metadata"""
    return [
        {
            'type': 'first_task',
            'title': 'Getting Started',
            'description': 'Complete your first task',
            'icon': 'fas fa-check-circle',
            'rarity': 'common',
            'points': 10
        },
        {
            'type': 'task_master',
            'title': 'Task Master',
            'description': 'Complete 10 tasks',
            'icon': 'fas fa-tasks',
            'rarity': 'uncommon',
            'points': 25
        },
        {
            'type': 'goal_achiever',
            'title': 'Goal Achiever',
            'description': 'Achieve your first goal',
            'icon': 'fas fa-bullseye',
            'rarity': 'uncommon',
            'points': 30
        },
        {
            'type': 'streak_master',
            'title': 'Streak Master',
            'description': '7-day study streak',
            'icon': 'fas fa-fire',
            'rarity': 'rare',
            'points': 50
        },
        {
            'type': 'week_warrior',
            'title': 'Week Warrior',
            'description': '40+ hours in a week',
            'icon': 'fas fa-calendar-week',
            'rarity': 'rare',
            'points': 75
        },
        {
            'type': 'perfectionist',
            'title': 'Perfectionist',
            'description': 'Perfect 7-day week',
            'icon': 'fas fa-star',
            'rarity': 'epic',
            'points': 100
        }
    ]

def calculate_badge_progress(user_id, badge_type):
    """Calculate progress towards a badge"""
    if badge_type == 'first_task':
        completed = Task.query.filter_by(user_id=user_id).count()
        return {'current': min(completed, 1), 'target': 1, 'percentage': min(completed * 100, 100)}
    elif badge_type == 'task_master':
        completed = Task.query.filter_by(user_id=user_id).count()
        return {'current': min(completed, 10), 'target': 10, 'percentage': min(completed * 10, 100)}
    elif badge_type == 'goal_achiever':
        achieved = Goal.query.filter_by(user_id=user_id, achieved=True).count()
        return {'current': min(achieved, 1), 'target': 1, 'percentage': min(achieved * 100, 100)}
    elif badge_type == 'streak_master':
        streak = calculate_streak_data(user_id)['current_streak']
        return {'current': min(streak, 7), 'target': 7, 'percentage': min(streak * 100 / 7, 100)}
    elif badge_type == 'week_warrior':
        weekly_hours = calculate_weekly_stats(user_id)
        return {'current': min(weekly_hours, 40), 'target': 40, 'percentage': min(weekly_hours * 100 / 40, 100)}
    elif badge_type == 'perfectionist':
        perfect_days = calculate_perfect_days(user_id)
        return {'current': min(perfect_days, 7), 'target': 7, 'percentage': min(perfect_days * 100 / 7, 100)}

    return {'current': 0, 'target': 1, 'percentage': 0}

def calculate_user_level(total_achievements, total_points):
    """Calculate user level based on achievements and points"""
    # Simple level calculation: level = sqrt(points/10) + achievements
    import math
    level = math.floor(math.sqrt(total_points / 10) + total_achievements / 2) + 1
    return max(level, 1)

def calculate_next_level_points(current_level):
    """Calculate points needed for next level"""
    # Reverse of level calculation
    import math
    return int(((current_level - 1) * 10) ** 2)

def calculate_weekly_stats(user_id):
    """Calculate hours studied in current week"""
    week_start = datetime.utcnow().date() - timedelta(days=7)
    weekly_data = UserProductivity.query.filter(
        UserProductivity.user_id == user_id,
        UserProductivity.date >= week_start
    ).all()
    return sum(p.hours_studied for p in weekly_data)

def check_early_morning_activity(user_id):
    """Check if user is most active in early morning"""
    # This would need time-of-day tracking in pomodoro sessions
    # For now, return False
    return False

def check_late_night_activity(user_id):
    """Check if user is most active late at night"""
    # This would need time-of-day tracking in pomodoro sessions
    # For now, return False
    return False

def check_perfect_week(user_id):
    """Check if user had a perfect week (7 consecutive days)"""
    streak = calculate_streak_data(user_id)['current_streak']
    return streak >= 7

def calculate_perfect_days(user_id):
    """Count consecutive perfect days"""
    # Simplified version - counts current streak
    return calculate_streak_data(user_id)['current_streak']

def get_leaderboard_data(limit=50):
    """Get leaderboard data for all users"""
    from app.models import User

    # Get all users with their stats
    users = User.query.all()
    leaderboard = []

    for user in users:
        stats = calculate_gamification_stats(user.id)
        streak_data = calculate_streak_data(user.id)

        user_data = {
            'user_id': user.id,
            'username': user.username,
            'total_points': stats['total_points'],
            'level': stats['level'],
            'current_streak': stats['current_streak'],
            'longest_streak': stats['longest_streak'],
            'completed_tasks': Task.query.filter_by(user_id=user.id, completed=True).count(),
            'completed_goals': Goal.query.filter_by(user_id=user.id, achieved=True).count(),
            'avg_productivity': calculate_avg_productivity(user.id),
            'total_achievements': stats['total_achievements']
        }
        leaderboard.append(user_data)

    # Sort by total points (descending)
    leaderboard.sort(key=lambda x: x['total_points'], reverse=True)

    return leaderboard[:limit]

def calculate_avg_productivity(user_id):
    """Calculate average productivity score for user"""
    productivity_data = UserProductivity.query.filter_by(user_id=user_id).all()
    if not productivity_data:
        return 0

    total_score = sum(p.productivity_score for p in productivity_data)
    return total_score / len(productivity_data) if len(productivity_data) > 0 else 0

def calculate_detailed_streak_data(user_id):
    """Calculate detailed streak information for display"""
    # Get productivity data for streak calculation
    productivity_data = UserProductivity.query.filter_by(user_id=user_id)\
        .order_by(UserProductivity.date.desc()).limit(60).all()

    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    total_days = 0
    last_activity = None

    # Calculate current streak (consecutive days with activity)
    today = datetime.utcnow().date()
    for i, p in enumerate(productivity_data):
        expected_date = today - timedelta(days=i)
        if p.date == expected_date and (p.hours_studied > 0 or p.tasks_completed > 0):
            current_streak += 1
            total_days += 1
            if last_activity is None:
                last_activity = p.date
        else:
            break

    # Calculate longest streak
    for p in reversed(productivity_data):
        if p.hours_studied > 0 or p.tasks_completed > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
            total_days += 1
        else:
            temp_streak = 0

    # Calculate streak history (past streaks)
    streak_history = []
    current_streak_start = None
    current_streak_length = 0

    # Sort productivity data by date ascending for history calculation
    sorted_data = sorted(productivity_data, key=lambda x: x.date)

    for p in sorted_data:
        if p.hours_studied > 0 or p.tasks_completed > 0:
            if current_streak_start is None:
                current_streak_start = p.date
            current_streak_length += 1
        else:
            if current_streak_start and current_streak_length > 0:
                streak_history.append({
                    'start_date': current_streak_start,
                    'end_date': current_streak_start + timedelta(days=current_streak_length - 1),
                    'length': current_streak_length
                })
            current_streak_start = None
            current_streak_length = 0

    # Add the last streak if it ended with activity
    if current_streak_start and current_streak_length > 0:
        streak_history.append({
            'start_date': current_streak_start,
            'end_date': current_streak_start + timedelta(days=current_streak_length - 1),
            'length': current_streak_length
        })

    # Calculate calendar days (last 30 days)
    calendar_days = []
    for i in range(29, -1, -1):
        check_date = today - timedelta(days=i)
        day_data = UserProductivity.query.filter_by(
            user_id=user_id,
            date=check_date
        ).first()

        calendar_days.append({
            'date': check_date,
            'active': day_data and (day_data.hours_studied > 0 or day_data.tasks_completed > 0),
            'is_today': check_date == today
        })

    # Calculate average streak length
    total_streak_days = sum(streak['length'] for streak in streak_history)
    avg_streak_length = total_streak_days / len(streak_history) if streak_history else 0

    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_days': total_days,
        'last_activity': last_activity,
        'streak_history': sorted(streak_history, key=lambda x: x['length'], reverse=True)[:10],
        'calendar_days': calendar_days,
        'avg_streak_length': avg_streak_length
    }