from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Schedule, ScheduleTask
from app.ai.schedule_generator import SmartScheduleGenerator
from datetime import datetime, date
from typing import Dict

schedules_bp = Blueprint('schedules', __name__, url_prefix='/schedules')

@schedules_bp.route('/')
@login_required
def index():
    """Schedule manager main page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get schedules for user, ordered by date desc
    schedules = Schedule.query.filter_by(user_id=current_user.id)\
                             .order_by(Schedule.date.desc())\
                             .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('schedules/index.html',
                          title='Smart Schedules',
                          schedules=schedules)

@schedules_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    """Generate AI-powered schedule"""
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        schedule_type = request.form.get('schedule_type', 'daily')
        days = int(request.form.get('days', 1))

        if schedule_type == 'multi-day':
            if not date_str:
                start_date = date.today()
            else:
                try:
                    start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format.', 'error')
                    return redirect(url_for('schedules.generate'))

            # Generate multi-day schedule
            generator = SmartScheduleGenerator(current_user.id)
            try:
                schedules = generator.generate_multi_day_schedule(start_date, days)
                if schedules:
                    flash(f'AI-powered {days}-day schedule generated starting {start_date}!', 'success')
                    return redirect(url_for('schedules.view', schedule_id=schedules[0].id))
                else:
                    flash('No tasks available to schedule.', 'info')
                    return redirect(url_for('schedules.generate'))
            except Exception as e:
                flash('An error occurred while generating the multi-day schedule.', 'error')
                return redirect(url_for('schedules.generate'))

        else:  # Daily schedule
            if not date_str:
                target_date = date.today()
            else:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format.', 'error')
                    return redirect(url_for('schedules.generate'))

            # Check if schedule already exists for this date
            existing_schedule = Schedule.query.filter_by(
                user_id=current_user.id,
                date=target_date
            ).first()

            if existing_schedule:
                flash(f'Schedule already exists for {target_date}. You can view it or regenerate if needed.', 'info')
                return redirect(url_for('schedules.view', schedule_id=existing_schedule.id))

            # Generate new schedule
            generator = SmartScheduleGenerator(current_user.id)
            try:
                schedule = generator.generate_schedule(target_date)
                flash(f'AI-powered schedule generated for {target_date}!', 'success')
                return redirect(url_for('schedules.view', schedule_id=schedule.id))
            except Exception as e:
                flash('An error occurred while generating the schedule.', 'error')
                return redirect(url_for('schedules.generate'))

    # GET request - show form
    today = date.today()

    # Get real user statistics
    from app.models import Task, UserProductivity
    from sqlalchemy import func

    # Count pending tasks for current user
    pending_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=False).count()

    # Get productivity data
    productivity_data = UserProductivity.query.filter_by(user_id=current_user.id)\
                                             .order_by(UserProductivity.date.desc())\
                                             .limit(7).all()  # Last 7 days

    avg_productivity = 0
    if productivity_data:
        avg_productivity = sum(d.productivity_score for d in productivity_data) / len(productivity_data)

    # Get recent schedules (convert to dict for JSON serialization)
    recent_schedules_db = Schedule.query.filter_by(user_id=current_user.id)\
                                       .order_by(Schedule.created_at.desc())\
                                       .limit(3).all()

    recent_schedules = []
    for schedule in recent_schedules_db:
        recent_schedules.append({
            'id': schedule.id,
            'date': schedule.date.isoformat(),
            'total_study_time': schedule.total_study_time,
            'generated_by_ai': schedule.generated_by_ai,
            'created_at': schedule.created_at.isoformat() if schedule.created_at else None
        })

    return render_template('schedules/generate.html',
                           title='Generate Smart Schedule',
                           today=today,
                           pending_tasks_count=pending_tasks_count,
                           avg_productivity=round(avg_productivity),
                           recent_schedules=recent_schedules)

@schedules_bp.route('/<int:schedule_id>')
@login_required
def view(schedule_id):
    """View schedule details"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()

    # Get scheduled tasks with task details
    scheduled_tasks = db.session.query(ScheduleTask)\
                              .filter_by(schedule_id=schedule_id)\
                              .join(ScheduleTask.task)\
                              .order_by(ScheduleTask.scheduled_time)\
                              .all()

    # Get productivity insights (with fallback)
    try:
        generator = SmartScheduleGenerator(current_user.id)
        insights = generator.get_productivity_insights()
    except Exception as e:
        print(f"Could not generate productivity insights: {e}")
        insights = {
            "average_productivity_score": 0,
            "insights": "Productivity insights unavailable at the moment.",
            "recommendations": []
        }

    return render_template('schedules/view.html',
                          title=f'Schedule for {schedule.date}',
                          schedule=schedule,
                          scheduled_tasks=scheduled_tasks,
                          insights=insights)

@schedules_bp.route('/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete(schedule_id):
    """Delete schedule"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()

    try:
        # Log what we're deleting
        schedule_tasks_count = len(schedule.tasks)
        print(f"Deleting schedule {schedule.id} with {schedule_tasks_count} tasks")

        db.session.delete(schedule)  # Cascade will delete schedule_tasks and breaks
        db.session.commit()
        flash(f'Schedule for {schedule.date} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Schedule deletion error: {str(e)}")
        flash(f'An error occurred while deleting the schedule: {str(e)}', 'error')

    return redirect(url_for('schedules.index'))

@schedules_bp.route('/<int:schedule_id>/performance')
@login_required
def performance(schedule_id):
    """View schedule performance analytics"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()

    # Calculate performance metrics
    performance_data = calculate_schedule_performance(schedule)

    return render_template('schedules/performance.html',
                         title=f'Performance - {schedule.date}',
                         schedule=schedule,
                         performance=performance_data)

@schedules_bp.route('/<int:schedule_id>/task/<int:task_id>/complete', methods=['POST'])
@login_required
def mark_task_complete(schedule_id, task_id):
    """Mark a scheduled task as completed"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    # Check if task is actually scheduled for this schedule
    schedule_task = ScheduleTask.query.filter_by(
        schedule_id=schedule_id,
        task_id=task_id
    ).first_or_404()

    try:
        # Mark task as completed
        task.completed = True
        task.completed_at = datetime.utcnow()

        # Record actual duration if provided
        actual_duration = request.form.get('actual_duration', type=int)
        if actual_duration:
            task.actual_duration = actual_duration

        db.session.commit()

        # Update productivity data
        update_productivity_data(current_user.id, task.actual_duration or task.estimated_duration or 25)

        flash(f'Task "{task.title}" marked as completed!', 'success')

        # Check if all tasks in schedule are complete
        remaining_tasks = ScheduleTask.query.join(Task).filter(
            ScheduleTask.schedule_id == schedule_id,
            Task.completed == False
        ).count()

        if remaining_tasks == 0:
            flash('🎉 Congratulations! All tasks in this schedule are complete!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating task: {str(e)}', 'error')

    return redirect(url_for('schedules.view', schedule_id=schedule_id))

@schedules_bp.route('/<int:schedule_id>/duplicate', methods=['POST'])
@login_required
def duplicate_schedule(schedule_id):
    """Duplicate a schedule"""
    original_schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()

    try:
        # Create new schedule with same date + 1 day
        new_date = original_schedule.date + datetime.timedelta(days=1)

        # Check if schedule already exists for new date
        existing = Schedule.query.filter_by(user_id=current_user.id, date=new_date).first()
        if existing:
            flash('A schedule already exists for the next day. Choose a different date.', 'warning')
            return redirect(url_for('schedules.view', schedule_id=schedule_id))

        # Create duplicate schedule
        new_schedule = Schedule(
            user_id=current_user.id,
            date=new_date,
            generated_by_ai=original_schedule.generated_by_ai,
            total_study_time=original_schedule.total_study_time
        )
        db.session.add(new_schedule)
        db.session.flush()

        # Duplicate all schedule tasks
        for original_task in original_schedule.tasks:
            new_task = ScheduleTask(
                schedule_id=new_schedule.id,
                task_id=original_task.task_id,
                scheduled_time=original_task.scheduled_time.replace(day=new_date.day),
                duration=original_task.duration
            )
            db.session.add(new_task)

        db.session.commit()
        flash(f'Schedule duplicated successfully for {new_date.strftime("%B %d, %Y")}!', 'success')
        return redirect(url_for('schedules.view', schedule_id=new_schedule.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error duplicating schedule: {str(e)}', 'error')
        return redirect(url_for('schedules.view', schedule_id=schedule_id))

@schedules_bp.route('/<int:schedule_id>/export')
@login_required
def export_schedule(schedule_id):
    """Export schedule as JSON"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()

    # Prepare export data
    export_data = {
        'schedule': {
            'date': schedule.date.strftime('%Y-%m-%d'),
            'total_study_time': schedule.total_study_time,
            'generated_by_ai': schedule.generated_by_ai,
            'created_at': schedule.created_at.strftime('%Y-%m-%d %H:%M:%S')
        },
        'tasks': []
    }

    for schedule_task in schedule.tasks:
        task_data = {
            'title': schedule_task.task.title,
            'description': schedule_task.task.description,
            'category': schedule_task.task.category,
            'priority': schedule_task.task.priority,
            'due_date': schedule_task.task.due_date.strftime('%Y-%m-%d') if schedule_task.task.due_date else None,
            'estimated_duration': schedule_task.task.estimated_duration,
            'scheduled_time': schedule_task.scheduled_time.strftime('%H:%M'),
            'duration': schedule_task.duration
        }
        export_data['tasks'].append(task_data)

    # Return JSON response that triggers download
    from flask import Response
    import json

    filename = f"schedule_{schedule.date.strftime('%Y%m%d')}.json"
    response = Response(
        json.dumps(export_data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

    return response

# ===== PERFORMANCE TRACKING FUNCTIONS =====

def calculate_schedule_performance(schedule: Schedule) -> Dict:
    """
    Calculate comprehensive performance metrics for a schedule.
    """
    total_tasks = len(schedule.tasks)
    completed_tasks = sum(1 for st in schedule.tasks if st.task.completed)

    # Calculate completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Calculate adherence (tasks completed on scheduled day)
    scheduled_date = schedule.date
    on_time_completions = sum(1 for st in schedule.tasks
                            if st.task.completed and st.task.completed_at
                            and st.task.completed_at.date() == scheduled_date)

    adherence_rate = (on_time_completions / total_tasks * 100) if total_tasks > 0 else 0

    # Calculate efficiency (actual vs estimated time)
    total_estimated = sum(st.task.estimated_duration or 25 for st in schedule.tasks)
    total_actual = sum(st.task.actual_duration or st.task.estimated_duration or 25
                      for st in schedule.tasks if st.task.completed)

    efficiency_ratio = (total_actual / total_estimated) if total_estimated > 0 else 1.0

    # Generate insights
    insights = []
    if completion_rate >= 80:
        insights.append("Excellent completion rate! Keep up the great work.")
    elif completion_rate >= 60:
        insights.append("Good progress. Consider breaking larger tasks into smaller ones.")
    else:
        insights.append("Focus on completing high-priority tasks first.")

    if adherence_rate >= 80:
        insights.append("Strong schedule adherence. Your planning is effective.")
    else:
        insights.append("Consider adjusting your schedule to be more realistic.")

    if efficiency_ratio < 0.8:
        insights.append("Tasks are taking less time than estimated. Good time management!")
    elif efficiency_ratio > 1.2:
        insights.append("Tasks are taking longer than planned. Consider adding buffer time.")

    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round(completion_rate, 1),
        'adherence_rate': round(adherence_rate, 1),
        'efficiency_ratio': round(efficiency_ratio, 2),
        'total_estimated_time': total_estimated,
        'total_actual_time': total_actual,
        'insights': insights,
        'performance_score': round((completion_rate + adherence_rate) / 2, 1)
    }

def update_productivity_data(user_id: int, study_duration: int):
    """
    Update user's productivity data after completing a scheduled task.
    This complements the pomodoro productivity tracking.
    """
    from app.models import UserProductivity

    today = datetime.utcnow().date()

    # Get or create productivity record for today
    productivity = UserProductivity.query.filter_by(
        user_id=user_id,
        date=today
    ).first()

    if not productivity:
        productivity = UserProductivity(
            user_id=user_id,
            date=today,
            hours_studied=0,
            tasks_completed=0,
            goals_progressed=0,
            average_focus_score=0,
            burnout_risk=0,
            productivity_score=0
        )
        db.session.add(productivity)

    # Update stats (be careful not to double-count with pomodoro sessions)
    # Only increment if this is direct task completion, not from pomodoro
    productivity.hours_studied += study_duration / 60.0  # Convert to hours
    productivity.tasks_completed += 1

    # Enhanced productivity scoring that considers both scheduled tasks and pomodoro sessions
    base_score = 75  # Higher base score for scheduled task completion
    completion_bonus = min(productivity.tasks_completed * 3, 15)  # Tasks are worth more when scheduled
    time_bonus = min(productivity.hours_studied * 3, 10)  # Scheduled study time is more valuable

    productivity.productivity_score = min(base_score + completion_bonus + time_bonus, 100)

    # Calculate burnout risk (consider scheduled study time)
    if productivity.hours_studied > 7:  # Higher threshold for scheduled study
        productivity.burnout_risk = min((productivity.hours_studied - 7) * 8 + 15, 85)
    else:
        productivity.burnout_risk = max(5, productivity.hours_studied * 3)  # Lower base risk for scheduled study

    db.session.commit()