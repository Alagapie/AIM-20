from flask_login import UserMixin
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

# Import db at the end to avoid circular imports
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='user', lazy=True, cascade='all, delete-orphan')
    pomodoro_sessions = db.relationship('PomodoroSession', backref='user', lazy=True, cascade='all, delete-orphan')
    achievements = db.relationship('Achievement', backref='user', lazy=True, cascade='all, delete-orphan')
    user_settings = db.relationship('UserSettings', backref='user', lazy=True, cascade='all, delete-orphan', uselist=False)
    productivity_data = db.relationship('UserProductivity', backref='user', lazy=True, cascade='all, delete-orphan')
    ai_chats = db.relationship('AIChat', backref='user', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='user', lazy=True, cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., 'study', 'assignment', 'review'
    priority = db.Column(db.String(10), default='medium')  # 'low', 'medium', 'high'
    due_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    order = db.Column(db.Integer, default=0)  # For drag & drop ordering
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)  # Link to goal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    goal = db.relationship('Goal', backref=db.backref('tasks', lazy=True, cascade='all, delete-orphan'))
    # Many-to-many with Schedule - cascade delete
    schedule_tasks = db.relationship('ScheduleTask', back_populates='task', cascade='all, delete-orphan')
    # Pomodoro sessions relationship
    pomodoro_sessions = db.relationship('PomodoroSession', backref='task', lazy=True, cascade='all, delete-orphan')

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., 'subject', 'exam', 'skill'
    target_value = db.Column(db.Float)  # e.g., grade, hours, completion %
    current_value = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))  # e.g., 'hours', 'grade', 'percentage'
    target_date = db.Column(db.DateTime)
    achieved = db.Column(db.Boolean, default=False)
    achieved_at = db.Column(db.DateTime)
    milestones = db.Column(db.Text)  # JSON string of milestones
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_milestones(self):
        return json.loads(self.milestones) if self.milestones else []

    def set_milestones(self, milestones):
        self.milestones = json.dumps(milestones)

    # Relationship to progress history
    progress_history = db.relationship('GoalProgressHistory', backref='goal', lazy=True, cascade='all, delete-orphan')
    # Relationship to milestones
    milestones = db.relationship('Milestone', backref='goal', lazy=True, cascade='all, delete-orphan', order_by='Milestone.order')

class GoalProgressHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    progress_value = db.Column(db.Float, nullable=False)
    change_amount = db.Column(db.Float, nullable=False)  # How much progress was added
    change_reason = db.Column(db.String(100))  # e.g., 'task_completed', 'manual_update', 'milestone_achieved'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GoalProgressHistory goal_id={self.goal_id} progress_value={self.progress_value}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'goal_deadline', 'goal_achievement', 'task_reminder', etc.
    related_id = db.Column(db.Integer)  # ID of related object (goal_id, task_id, etc.)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification user_id={self.user_id} type={self.notification_type} read={self.is_read}>'

class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_value = db.Column(db.Float, nullable=False)  # Target value for this milestone
    current_value = db.Column(db.Float, default=0)  # Current progress
    unit = db.Column(db.String(20))  # Unit of measurement (inherited from goal or custom)
    order = db.Column(db.Integer, default=0)  # Order of milestones
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Milestone goal_id={self.goal_id} title={self.title} completed={self.completed}>'

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    generated_by_ai = db.Column(db.Boolean, default=False)
    total_study_time = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Many-to-many with Task - cascade delete
    tasks = db.relationship('ScheduleTask', back_populates='schedule', cascade='all, delete-orphan')

class ScheduleTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes

    schedule = db.relationship('Schedule', back_populates='tasks')
    task = db.relationship('Task', back_populates='schedule_tasks')
    # Schedule breaks relationship
    breaks = db.relationship('ScheduleBreak', backref='schedule_task_ref', lazy=True, cascade='all, delete-orphan')

class PomodoroSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    session_type = db.Column(db.String(10), nullable=False)  # 'work' or 'break'
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # in minutes
    completed = db.Column(db.Boolean, default=False)
    interrupted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    category = db.Column(db.String(50))  # e.g., 'motivation', 'focus', 'success'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_type = db.Column(db.String(50), nullable=False)  # e.g., 'first_task', 'study_streak'
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    badge_image = db.Column(db.String(100))  # path to badge image

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pomodoro_work_duration = db.Column(db.Integer, default=25)  # minutes
    pomodoro_break_duration = db.Column(db.Integer, default=5)  # minutes
    long_break_duration = db.Column(db.Integer, default=15)  # minutes
    sessions_until_long_break = db.Column(db.Integer, default=4)
    preferred_study_times = db.Column(db.String(100))  # JSON: ['09:00', '14:00']
    notifications_enabled = db.Column(db.Boolean, default=True)
    goal_deadline_reminders = db.Column(db.Boolean, default=True)
    goal_achievement_notifications = db.Column(db.Boolean, default=True)
    reminder_days_before = db.Column(db.Integer, default=3)  # Days before deadline to send reminder
    tts_enabled = db.Column(db.Boolean, default=False)
    stt_enabled = db.Column(db.Boolean, default=False)
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50), default='Africa/Lagos')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_preferred_times(self):
        return json.loads(self.preferred_study_times) if self.preferred_study_times else []

    def set_preferred_times(self, times):
        self.preferred_study_times = json.dumps(times)

class UserProductivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_studied = db.Column(db.Float, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    goals_progressed = db.Column(db.Integer, default=0)
    average_focus_score = db.Column(db.Float, default=0)  # 0-100
    burnout_risk = db.Column(db.Float, default=0)  # 0-100
    productivity_score = db.Column(db.Float, default=0)  # 0-100
    recommendations = db.Column(db.Text)  # JSON string of suggestions

    def get_recommendations(self):
        return json.loads(self.recommendations) if self.recommendations else []

    def set_recommendations(self, recs):
        self.recommendations = json.dumps(recs)

class AIChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20))  # 'summary', 'quiz', 'question', 'general'
    context = db.Column(db.Text)  # additional context like subject, topic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    difficulty = db.Column(db.String(20), default='intermediate')  # 'beginner', 'intermediate', 'advanced'
    question_count = db.Column(db.Integer, default=10)
    time_limit = db.Column(db.Integer)  # minutes, None for no limit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_from = db.Column(db.String(50))  # 'chat', 'document', 'topic', 'custom'
    source_id = db.Column(db.Integer)  # ID of source (chat_id, document_id, etc.)
    max_score = db.Column(db.Integer, default=0)  # Total possible points

    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade='all, delete-orphan')

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice', 'true_false', 'short_answer', 'fill_blank', 'essay'
    options = db.Column(db.JSON)  # For multiple choice: ['A) option1', 'B) option2', ...]
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)  # AI-generated explanation for correct answer
    points = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer)  # Question order in quiz

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    score = db.Column(db.Integer, default=0)  # Total points earned
    max_score = db.Column(db.Integer, default=0)  # Total possible points
    percentage = db.Column(db.Float, default=0.0)  # Score percentage
    time_taken = db.Column(db.Integer)  # seconds
    completed = db.Column(db.Boolean, default=False)

    answers = db.relationship('QuizAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')

class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    user_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    time_taken = db.Column(db.Integer)  # seconds for this question
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

# Advanced Scheduling Models
class MultiDaySchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    child_schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent_schedule = db.relationship('Schedule', foreign_keys=[parent_schedule_id])
    child_schedule = db.relationship('Schedule', foreign_keys=[child_schedule_id])

class ScheduleConflict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    conflict_type = db.Column(db.String(50), nullable=False)  # 'calendar', 'energy', 'goal', 'time'
    conflict_details = db.Column(db.Text, nullable=False)  # JSON details of the conflict
    resolution_applied = db.Column(db.Text)  # How it was resolved
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    schedule = db.relationship('Schedule', backref=db.backref('conflicts', lazy=True))

class EnergyPattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    energy_level = db.Column(db.Float, nullable=False)  # 0-10 scale
    focus_score = db.Column(db.Float, nullable=False)  # 0-10 scale
    tasks_completed = db.Column(db.Integer, default=0)
    breaks_taken = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('energy_patterns', lazy=True))

class BreakActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'physical', 'mental', 'creative', 'social'
    duration_minutes = db.Column(db.Integer, nullable=False)
    difficulty_level = db.Column(db.String(20), default='easy')  # 'easy', 'medium', 'hard'
    energy_required = db.Column(db.Float, nullable=False)  # 0-10 scale
    description = db.Column(db.Text)
    benefits = db.Column(db.Text)  # JSON array of benefits
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_benefits(self):
        return json.loads(self.benefits) if self.benefits else []

    def set_benefits(self, benefits):
        self.benefits = json.dumps(benefits)

class ScheduleBreak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_task_id = db.Column(db.Integer, db.ForeignKey('schedule_task.id'), nullable=False)
    break_activity_id = db.Column(db.Integer, db.ForeignKey('break_activity.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    energy_boost = db.Column(db.Float, default=0.0)  # Expected energy increase
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    break_activity = db.relationship('BreakActivity')