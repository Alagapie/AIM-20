from app import db
from app.models import Goal, Task, Notification, UserSettings, Achievement
from datetime import datetime, timedelta
import json

def check_goal_deadlines():
    """Check for upcoming goal deadlines and create notifications"""
    # Get all active goals with target dates
    goals_with_deadlines = Goal.query.filter(
        Goal.achieved == False,
        Goal.target_date.isnot(None)
    ).all()

    current_time = datetime.utcnow()

    for goal in goals_with_deadlines:
        # Get user settings
        user_settings = UserSettings.query.filter_by(user_id=goal.user_id).first()
        if not user_settings or not user_settings.goal_deadline_reminders:
            continue

        days_before = user_settings.reminder_days_before
        reminder_date = goal.target_date - timedelta(days=days_before)

        # Check if we're within the reminder window (reminder_date to deadline)
        if current_time >= reminder_date and current_time <= goal.target_date:
            # Check if notification already exists for this goal and time period
            existing_notification = Notification.query.filter_by(
                user_id=goal.user_id,
                notification_type='goal_deadline',
                related_id=goal.id,
                created_at=current_time.date()  # One notification per day
            ).first()

            if not existing_notification:
                days_remaining = (goal.target_date.date() - current_time.date()).days

                if days_remaining > 0:
                    title = f"Goal Deadline Approaching: {goal.title}"
                    message = f"Your goal '{goal.title}' is due in {days_remaining} day{'s' if days_remaining != 1 else ''}. Current progress: {goal.current_value}/{goal.target_value} {goal.unit}."
                else:
                    title = f"Goal Overdue: {goal.title}"
                    message = f"Your goal '{goal.title}' is overdue. Current progress: {goal.current_value}/{goal.target_value} {goal.unit}."

                notification = Notification(
                    user_id=goal.user_id,
                    title=title,
                    message=message,
                    notification_type='goal_deadline',
                    related_id=goal.id
                )
                db.session.add(notification)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error creating goal deadline notifications: {e}")

def check_goal_achievements():
    """Check for newly achieved goals and create notifications"""
    # Get recently achieved goals (within last hour to avoid duplicate notifications)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    recent_achievements = Goal.query.filter(
        Goal.achieved == True,
        Goal.achieved_at >= one_hour_ago
    ).all()

    for goal in recent_achievements:
        # Get user settings
        user_settings = UserSettings.query.filter_by(user_id=goal.user_id).first()
        if not user_settings or not user_settings.goal_achievement_notifications:
            continue

        # Check if achievement notification already exists
        existing_notification = Notification.query.filter_by(
            user_id=goal.user_id,
            notification_type='goal_achievement',
            related_id=goal.id
        ).first()

        if not existing_notification:
            title = f"🎉 Goal Achieved: {goal.title}"
            message = f"Congratulations! You have successfully achieved your goal '{goal.title}' with {goal.current_value} {goal.unit}."

            notification = Notification(
                user_id=goal.user_id,
                title=title,
                message=message,
                notification_type='goal_achievement',
                related_id=goal.id
            )
            db.session.add(notification)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error creating goal achievement notifications: {e}")

def get_user_notifications(user_id, limit=20, unread_only=False):
    """Get notifications for a user"""
    query = Notification.query.filter_by(user_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def mark_notification_read(notification_id, user_id):
    """Mark a notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()

    if notification:
        notification.is_read = True
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error marking notification as read: {e}")
            return False

    return False

def get_unread_count(user_id):
    """Get count of unread notifications for a user"""
    return Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()

def check_goal_achievements(user_id):
    """Check for goal-related achievements and award badges"""
    # Get user's goal statistics
    goals = Goal.query.filter_by(user_id=user_id).all()
    achieved_goals = [g for g in goals if g.achieved]
    total_goals = len(goals)
    achieved_count = len(achieved_goals)

    # Achievement definitions
    achievements = [
        {
            'type': 'first_goal_achieved',
            'title': 'First Victory',
            'description': 'Achieved your first goal!',
            'condition': lambda: achieved_count >= 1,
            'badge': '🏆'
        },
        {
            'type': 'goal_streak_3',
            'title': 'Triple Winner',
            'description': 'Achieved 3 goals in a row',
            'condition': lambda: check_goal_streak(user_id, 3),
            'badge': '🔥'
        },
        {
            'type': 'goal_streak_5',
            'title': 'High Achiever',
            'description': 'Achieved 5 goals in a row',
            'condition': lambda: check_goal_streak(user_id, 5),
            'badge': '⭐'
        },
        {
            'type': 'goal_master_10',
            'title': 'Goal Master',
            'description': 'Achieved 10 goals total',
            'condition': lambda: achieved_count >= 10,
            'badge': '👑'
        },
        {
            'type': 'goal_perfectionist',
            'title': 'Perfectionist',
            'description': 'Achieved a goal with 100% completion',
            'condition': lambda: any(g.current_value == g.target_value for g in achieved_goals),
            'badge': '💎'
        }
    ]

    for achievement in achievements:
        # Check if user already has this achievement
        existing = Achievement.query.filter_by(
            user_id=user_id,
            achievement_type=achievement['type']
        ).first()

        if not existing and achievement['condition']():
            # Award the achievement
            new_achievement = Achievement(
                user_id=user_id,
                achievement_type=achievement['type'],
                title=achievement['title'],
                description=achievement['description'],
                badge_image=achievement['badge']
            )
            db.session.add(new_achievement)

            # Create notification
            notification = Notification(
                user_id=user_id,
                title=f"🏆 Achievement Unlocked: {achievement['title']}",
                message=achievement['description'],
                notification_type='achievement',
                related_id=new_achievement.id
            )
            db.session.add(notification)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error awarding achievements: {e}")

def check_goal_streak(user_id, streak_length):
    """Check if user has achieved goals in a streak of specified length"""
    # Get recently achieved goals, ordered by achievement date
    achieved_goals = Goal.query.filter_by(
        user_id=user_id,
        achieved=True
    ).order_by(Goal.achieved_at.desc()).limit(streak_length * 2).all()

    if len(achieved_goals) < streak_length:
        return False

    # Check if the most recent goals form a streak
    # For simplicity, check if they were achieved within a reasonable timeframe
    streak_goals = achieved_goals[:streak_length]

    # Sort by achievement date (oldest first for streak check)
    streak_goals.sort(key=lambda x: x.achieved_at)

    # Check if goals were achieved consecutively (allowing some flexibility)
    for i in range(1, len(streak_goals)):
        prev_date = streak_goals[i-1].achieved_at.date()
        curr_date = streak_goals[i].achieved_at.date()

        # Allow up to 7 days gap between achievements for streak
        if (curr_date - prev_date).days > 7:
            return False

    return True

def get_user_achievements(user_id):
    """Get all achievements for a user"""
    return Achievement.query.filter_by(user_id=user_id).order_by(Achievement.earned_at.desc()).all()