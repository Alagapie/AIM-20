from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Task
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@tasks_bp.route('/')
@login_required
def index():
    """Task manager main page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Filter options
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    priority_filter = request.args.get('priority', 'all')

    # Build query
    query = Task.query.filter_by(user_id=current_user.id)

    if status_filter == 'pending':
        query = query.filter_by(completed=False)
    elif status_filter == 'completed':
        query = query.filter_by(completed=True)

    if category_filter != 'all':
        query = query.filter_by(category=category_filter)

    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)

    # Order by custom order, then by creation date (newest first) and priority
    tasks = query.order_by(Task.order.asc(), Task.priority.desc(), Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get unique categories and priorities for filters
    categories = db.session.query(Task.category).filter(
        Task.user_id == current_user.id,
        Task.category.isnot(None)
    ).distinct().all()

    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('tasks/index.html',
                         title='Task Manager',
                         tasks=tasks,
                         status_filter=status_filter,
                         category_filter=category_filter,
                         priority_filter=priority_filter,
                         categories=categories)

@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new task"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or None
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date', '').strip()
        estimated_duration = request.form.get('estimated_duration', type=int)
        goal_id = request.form.get('goal_id', type=int)

        if not title:
            flash('Task title is required.', 'error')
            return redirect(url_for('tasks.create'))

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid due date format.', 'error')
                return redirect(url_for('tasks.create'))

        # Validate goal_id if provided
        goal = None
        if goal_id:
            from app.models import Goal
            goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
            if not goal:
                flash('Invalid goal selected.', 'error')
                return redirect(url_for('tasks.create'))

        new_task = Task(
            user_id=current_user.id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            due_date=due_date,
            estimated_duration=estimated_duration,
            goal_id=goal_id if goal else None
        )

        try:
            db.session.add(new_task)
            db.session.commit()
            flash('Task created successfully!', 'success')
            return redirect(url_for('tasks.index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the task.', 'error')
            return redirect(url_for('tasks.create'))

    # Get user's active goals for the dropdown
    from app.models import Goal
    goals = Goal.query.filter_by(user_id=current_user.id, achieved=False).order_by(Goal.title).all()

    return render_template('tasks/create.html', title='Create Task', goals=goals)

@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    """Edit existing task"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or None
        priority = request.form.get('priority', task.priority)
        due_date_str = request.form.get('due_date', '').strip()
        estimated_duration = request.form.get('estimated_duration', type=int)
        goal_id = request.form.get('goal_id', type=int)

        if not title:
            flash('Task title is required.', 'error')
            return redirect(url_for('tasks.edit', task_id=task_id))

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid due date format.', 'error')
                return redirect(url_for('tasks.edit', task_id=task_id))

        # Validate goal_id if provided
        goal = None
        if goal_id:
            from app.models import Goal
            goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
            if not goal:
                flash('Invalid goal selected.', 'error')
                return redirect(url_for('tasks.edit', task_id=task_id))

        # Update task
        task.title = title
        task.description = description
        task.category = category
        task.priority = priority
        task.due_date = due_date
        task.estimated_duration = estimated_duration
        task.goal_id = goal_id if goal else None

        try:
            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('tasks.index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the task.', 'error')
            return redirect(url_for('tasks.edit', task_id=task_id))

    # Get user's active goals for the dropdown
    from app.models import Goal
    goals = Goal.query.filter_by(user_id=current_user.id, achieved=False).order_by(Goal.title).all()

    return render_template('tasks/edit.html', title='Edit Task', task=task, goals=goals)

@tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete(task_id):
    """Mark task as completed"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    if not task.completed:
        task.completed = True
        task.completed_at = datetime.utcnow()

        # Smart progress tracking: Update associated goal progress
        if task.goal_id:
            from app.models import Goal, GoalProgressHistory
            goal = Goal.query.filter_by(id=task.goal_id, user_id=current_user.id).first()
            if goal and not goal.achieved:
                # Add task duration to goal progress (prefer actual_duration, fallback to estimated_duration)
                duration_to_add = task.actual_duration or task.estimated_duration or 0
                if duration_to_add > 0 and goal.unit.lower() in ['hours', 'hour', 'hrs', 'hr', 'minutes', 'minute', 'mins', 'min']:
                    # Convert minutes to hours if goal unit is hours
                    if goal.unit.lower() in ['hours', 'hour', 'hrs', 'hr']:
                        duration_to_add = duration_to_add / 60.0

                    old_value = goal.current_value
                    goal.current_value += duration_to_add

                    # Record progress history
                    progress_entry = GoalProgressHistory(
                        goal_id=goal.id,
                        progress_value=goal.current_value,
                        change_amount=duration_to_add,
                        change_reason='task_completed'
                    )
                    db.session.add(progress_entry)

                    # Check if goal is now achieved
                    if goal.current_value >= goal.target_value:
                        goal.achieved = True
                        goal.achieved_at = datetime.utcnow()

        try:
            db.session.commit()
            flash(f'Task "{task.title}" marked as completed!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the task.', 'error')
    else:
        flash('Task is already completed.', 'info')

    return redirect(url_for('tasks.index'))

@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id):
    """Delete task"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(task)
        db.session.commit()
        flash(f'Task "{task.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the task.', 'error')

    return redirect(url_for('tasks.index'))

@tasks_bp.route('/<int:task_id>')
@login_required
def view(task_id):
    """View task details"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return render_template('tasks/view.html', title=task.title, task=task)

@tasks_bp.route('/reorder', methods=['POST'])
@login_required
def reorder():
    """Reorder tasks via drag & drop"""
    data = request.get_json()

    if not data or 'task_order' not in data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400

    task_order = data['task_order']

    try:
        # Update the order for each task
        for index, task_id in enumerate(task_order):
            task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
            if task:
                task.order = index

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500