from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Goal, Notification
from app.utils.notifications import check_goal_deadlines, check_goal_achievements, get_user_notifications, mark_notification_read, get_unread_count, check_goal_achievements as check_achievements
from datetime import datetime, timedelta
import json

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

# Goal templates for common academic achievements
GOAL_TEMPLATES = [
    {
        'name': 'Study Hours Target',
        'description': 'Set a target for total study hours in a semester',
        'category': 'study',
        'target_value': 120,
        'unit': 'hours',
        'default_days': 90
    },
    {
        'name': 'GPA Improvement',
        'description': 'Improve your GPA by a specific amount',
        'category': 'grades',
        'target_value': 0.5,
        'unit': 'points',
        'default_days': 120
    },
    {
        'name': 'Exam Score Target',
        'description': 'Achieve a specific score on an upcoming exam',
        'category': 'exam',
        'target_value': 85,
        'unit': 'percentage',
        'default_days': 30
    },
    {
        'name': 'Reading Goal',
        'description': 'Complete reading a specific number of books or chapters',
        'category': 'reading',
        'target_value': 5,
        'unit': 'books',
        'default_days': 60
    },
    {
        'name': 'Assignment Completion',
        'description': 'Complete all assignments for a course with high quality',
        'category': 'assignment',
        'target_value': 100,
        'unit': 'percentage',
        'default_days': 45
    },
    {
        'name': 'Practice Problems',
        'description': 'Solve a target number of practice problems',
        'category': 'practice',
        'target_value': 200,
        'unit': 'problems',
        'default_days': 30
    },
    {
        'name': 'Research Project',
        'description': 'Complete a research project with all milestones',
        'category': 'research',
        'target_value': 100,
        'unit': 'percentage',
        'default_days': 60
    },
    {
        'name': 'Language Learning',
        'description': 'Reach conversational fluency in a new language',
        'category': 'language',
        'target_value': 80,
        'unit': 'proficiency',
        'default_days': 180
    }
]

@goals_bp.route('/')
@login_required
def index():
    """Goals manager main page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Check for new notifications
    check_goal_deadlines()
    check_goal_achievements(current_user.id)

    # Filter options
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')

    # Build query
    query = Goal.query.filter_by(user_id=current_user.id)

    if status_filter == 'active':
        query = query.filter_by(achieved=False)
    elif status_filter == 'achieved':
        query = query.filter_by(achieved=True)

    if category_filter != 'all':
        query = query.filter_by(category=category_filter)

    # Order by creation date (newest first)
    goals = query.order_by(Goal.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get unique categories for filters
    categories = db.session.query(Goal.category).filter(
        Goal.user_id == current_user.id,
        Goal.category.isnot(None)
    ).distinct().all()

    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('goals/index.html',
                          title='Study Goals',
                          goals=goals,
                          status_filter=status_filter,
                          category_filter=category_filter,
                          categories=categories,
                          unread_notifications=get_unread_count(current_user.id))

@goals_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new goal"""
    # Check if a template was selected
    template_name = request.args.get('template')
    selected_template = None
    if template_name:
        selected_template = next((t for t in GOAL_TEMPLATES if t['name'] == template_name), None)
        # If template is selected and no POST request, pre-calculate target date
        if selected_template and not request.method == 'POST':
            # Calculate target date based on template's default days
            target_date = datetime.utcnow() + timedelta(days=selected_template['default_days'])
            selected_template = dict(selected_template)  # Make a copy
            selected_template['calculated_target_date'] = target_date.strftime('%Y-%m-%d')

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or None
        target_value = request.form.get('target_value', type=float)
        unit = request.form.get('unit', 'hours').strip()
        target_date_str = request.form.get('target_date', '').strip()
        use_template = request.form.get('use_template') == 'true'

        if not title:
            flash('Goal title is required.', 'error')
            return redirect(url_for('goals.create'))

        if not target_value or target_value <= 0:
            flash('Target value must be a positive number.', 'error')
            return redirect(url_for('goals.create'))

        # Parse target date if provided
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid target date format.', 'error')
                return redirect(url_for('goals.create'))

        # Handle milestones
        milestones_data = request.form.get('milestones', '[]')
        try:
            milestones = json.loads(milestones_data) if milestones_data else []
        except json.JSONDecodeError:
            milestones = []

        new_goal = Goal(
            user_id=current_user.id,
            title=title,
            description=description,
            category=category,
            target_value=target_value,
            unit=unit,
            target_date=target_date
        )

        if milestones:
            new_goal.set_milestones(milestones)

        try:
            db.session.add(new_goal)
            db.session.commit()
            flash('Goal created successfully!', 'success')
            return redirect(url_for('goals.index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the goal.', 'error')
            return redirect(url_for('goals.create'))

    return render_template('goals/create.html',
                          title='Create Goal',
                          templates=GOAL_TEMPLATES,
                          selected_template=selected_template,
                          request=request)

@goals_bp.route('/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(goal_id):
    """Edit existing goal"""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or None
        target_value = request.form.get('target_value', type=float)
        current_value = request.form.get('current_value', type=float, default=0)
        unit = request.form.get('unit', goal.unit).strip()
        target_date_str = request.form.get('target_date', '').strip()

        if not title:
            flash('Goal title is required.', 'error')
            return redirect(url_for('goals.edit', goal_id=goal_id))

        if not target_value or target_value <= 0:
            flash('Target value must be a positive number.', 'error')
            return redirect(url_for('goals.edit', goal_id=goal_id))

        # Parse target date if provided
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid target date format.', 'error')
                return redirect(url_for('goals.edit', goal_id=goal_id))

        # Handle milestones
        milestones_data = request.form.get('milestones', '[]')
        try:
            milestones = json.loads(milestones_data) if milestones_data else []
        except json.JSONDecodeError:
            milestones = []

        # Update goal
        goal.title = title
        goal.description = description
        goal.category = category
        goal.target_value = target_value
        goal.current_value = current_value
        goal.unit = unit
        goal.target_date = target_date

        if milestones:
            goal.set_milestones(milestones)

        try:
            db.session.commit()
            flash('Goal updated successfully!', 'success')
            return redirect(url_for('goals.index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the goal.', 'error')
            return redirect(url_for('goals.edit', goal_id=goal_id))

    return render_template('goals/edit.html', title='Edit Goal', goal=goal)

@goals_bp.route('/<int:goal_id>/progress', methods=['POST'])
@login_required
def update_progress(goal_id):
    """Update goal progress"""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    progress_value = request.form.get('progress_value', type=float)
    if progress_value is not None:
        goal.current_value = progress_value

        # Check if goal is achieved
        if progress_value >= goal.target_value and not goal.achieved:
            goal.achieved = True
            goal.achieved_at = datetime.utcnow()
            flash(f'Congratulations! Goal "{goal.title}" achieved!', 'success')
        elif progress_value < goal.target_value and goal.achieved:
            goal.achieved = False
            goal.achieved_at = None

        try:
            db.session.commit()
            flash('Progress updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating progress.', 'error')
    else:
        flash('Invalid progress value.', 'error')

    return redirect(url_for('goals.index'))

@goals_bp.route('/<int:goal_id>/achieve', methods=['POST'])
@login_required
def achieve(goal_id):
    """Mark goal as achieved"""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    if not goal.achieved:
        goal.achieved = True
        goal.achieved_at = datetime.utcnow()
        goal.current_value = goal.target_value

        try:
            db.session.commit()
            flash(f'Goal "{goal.title}" marked as achieved!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the goal.', 'error')
    else:
        flash('Goal is already achieved.', 'info')

    return redirect(url_for('goals.index'))

@goals_bp.route('/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete(goal_id):
    """Delete goal"""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(goal)
        db.session.commit()
        flash(f'Goal "{goal.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the goal.', 'error')

    return redirect(url_for('goals.index'))

@goals_bp.route('/<int:goal_id>')
@login_required
def view(goal_id):
    """View goal details"""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    return render_template('goals/view.html', title=goal.title, goal=goal, datetime=datetime)

@goals_bp.route('/analytics')
@login_required
def analytics():
    """Goal analytics dashboard"""
    from app.models import GoalProgressHistory
    import json
    from datetime import datetime, timedelta

    # Get all user's goals
    goals = Goal.query.filter_by(user_id=current_user.id).all()

    # Calculate analytics data
    analytics_data = {
        'total_goals': len(goals),
        'active_goals': len([g for g in goals if not g.achieved]),
        'achieved_goals': len([g for g in goals if g.achieved]),
        'completion_rate': (len([g for g in goals if g.achieved]) / len(goals) * 100) if goals else 0,
        'avg_progress': sum(g.current_value / g.target_value * 100 for g in goals if g.target_value > 0) / len(goals) if goals else 0
    }

    # Get progress history for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    progress_history = GoalProgressHistory.query.join(Goal).filter(
        Goal.user_id == current_user.id,
        GoalProgressHistory.recorded_at >= thirty_days_ago
    ).order_by(GoalProgressHistory.recorded_at).all()

    # Prepare chart data
    chart_data = []
    goal_progress_over_time = {}

    for entry in progress_history:
        goal_title = entry.goal.title
        if goal_title not in goal_progress_over_time:
            goal_progress_over_time[goal_title] = []
        goal_progress_over_time[goal_title].append({
            'date': entry.recorded_at.strftime('%Y-%m-%d'),
            'progress': entry.progress_value,
            'change': entry.change_amount
        })

    # Convert to chart format
    for goal_name, data in goal_progress_over_time.items():
        chart_data.append({
            'name': goal_name,
            'data': data
        })

    # Get goals by category
    categories = {}
    for goal in goals:
        cat = goal.category or 'Uncategorized'
        if cat not in categories:
            categories[cat] = {'total': 0, 'achieved': 0}
        categories[cat]['total'] += 1
        if goal.achieved:
            categories[cat]['achieved'] += 1

    category_data = [{'category': cat, 'achieved': data['achieved'], 'total': data['total']}
                    for cat, data in categories.items()]

    return render_template('goals/analytics.html',
                          title='Goal Analytics',
                          analytics_data=analytics_data,
                          chart_data=json.dumps(chart_data),
                          category_data=json.dumps(category_data),
                          goals=goals)

# Notification routes
@goals_bp.route('/notifications')
@login_required
def notifications():
    """View user notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Check for new notifications
    check_goal_deadlines()
    check_goal_achievements(current_user.id)

    notifications_list = get_user_notifications(current_user.id, limit=per_page * page)

    return render_template('goals/notifications.html',
                          title='Notifications',
                          notifications=notifications_list,
                          unread_count=get_unread_count(current_user.id))

@goals_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    if mark_notification_read(notification_id, current_user.id):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@goals_bp.route('/notifications/unread-count')
@login_required
def get_unread_notification_count():
    """Get count of unread notifications"""
    return jsonify({'count': get_unread_count(current_user.id)})