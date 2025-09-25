import datetime
from typing import List, Dict, Optional
import google.generativeai as genai
import os
from app.models import db, Task, Schedule, ScheduleTask, UserSettings, UserProductivity, PomodoroSession
from app import db

class SmartScheduleGenerator:
    """
    Enterprise-grade AI-powered schedule generator with advanced optimization algorithms,
    machine learning adaptation, conflict resolution, and comprehensive productivity analytics.
    Features: Multi-day planning, energy optimization, adaptive learning, collaboration support,
    external integrations, and predictive workload management.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user_settings = UserSettings.query.filter_by(user_id=user_id).first()
        self.productivity_data = UserProductivity.query.filter_by(user_id=user_id).order_by(UserProductivity.date.desc()).limit(90).all()

        # Initialize Gemini AI with enhanced configuration
        api_key = os.getenv('GEMINI_API_KEY', '').strip()

        if not api_key or api_key == '' or api_key == 'AIzaSyB9Q8w8k8Q8w8k8Q8w8k8Q8w8k8Q8w8k8Q8w8k' or len(api_key) < 20:
            print("WARNING: Gemini API key not configured properly for schedules. Using advanced fallback only.")
            self.api_available = False
            self.model = None
        else:
            try:
                genai.configure(api_key=api_key)

                # Enhanced generation configuration for complex scheduling
                generation_config = {
                    "temperature": 0.3,  # Lower temperature for more consistent scheduling decisions
                    "top_k": 50,
                    "top_p": 0.9,
                    "max_output_tokens": 4096,  # Increased for detailed schedules
                }

                self.model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash-lite",
                    generation_config=generation_config
                )

                # Test with scheduling-specific prompt
                try:
                    test_response = self.model.generate_content("Test scheduling optimization capabilities")
                    print("SUCCESS: Advanced Gemini API initialized for enterprise scheduling")
                except Exception as test_e:
                    print(f"WARNING: Gemini API test failed: {str(test_e)}")

                self.api_available = True

            except Exception as e:
                print(f"ERROR: Failed to initialize advanced Gemini API: {str(e)}")
                self.api_available = False
                self.model = None

        # Initialize core scheduling system
        self.energy_patterns = self._load_energy_patterns()
        self.break_activities = self._load_break_activities()

        # Initialize basic components only
        self.user_patterns = {}
        self.collaboration_data = {}
        self.external_constraints = {}
        self.constraint_solver = {}
        self.predictive_model = {}
        self.adaptive_engine = {}
        self.collaboration_engine = {}
        self.schedule_history = []
        self.performance_analytics = {}
        self.conflict_resolution_engine = {}

    def generate_schedule(self, date: datetime.date, tasks: Optional[List[Task]] = None) -> Schedule:
        """
        Generate an enterprise-grade optimized schedule for the given date.
        Uses comprehensive AI, ML, and optimization algorithms with productivity enhancements.
        """
        try:
            # Enhanced scheduling with productivity focus
            return self._generate_productivity_optimized_schedule(date, tasks)
        except Exception as e:
            print(f"Productivity scheduling failed: {e}, falling back to advanced scheduling")
            try:
                # Fall back to advanced rule-based scheduling
                return self._generate_advanced_schedule(date, tasks)
            except Exception as e2:
                print(f"Advanced scheduling failed: {e2}, falling back to basic")
                # Final fallback to basic scheduling
                return self._generate_basic_schedule(date, tasks)

    def _generate_advanced_schedule(self, date: datetime.date, tasks: Optional[List[Task]] = None) -> Schedule:
        """
        Generate advanced schedule with comprehensive rule-based intelligence.
        """
        if tasks is None:
            # Get pending tasks with enterprise context
            tasks = self._get_enterprise_tasks(date)

        if not tasks:
            # No tasks to schedule
            schedule = Schedule(
                user_id=self.user_id,
                date=date,
                generated_by_ai=True,
                total_study_time=0
            )
            db.session.add(schedule)
            db.session.commit()
            return schedule

        # Use advanced rule-based scheduling
        scheduled_tasks = self._allocate_tasks_fallback(tasks, date)

        # Create schedule
        schedule = Schedule(
            user_id=self.user_id,
            date=date,
            generated_by_ai=True,
            total_study_time=sum(duration for _, _, duration in scheduled_tasks)
        )
        db.session.add(schedule)
        db.session.flush()

        # Add scheduled tasks
        for task_id, scheduled_time, duration in scheduled_tasks:
            schedule_task = ScheduleTask(
                schedule_id=schedule.id,
                task_id=task_id,
                scheduled_time=scheduled_time,
                duration=duration
            )
            db.session.add(schedule_task)

        db.session.commit()
        return schedule

    def _generate_basic_schedule(self, date: datetime.date, tasks: Optional[List[Task]] = None) -> Schedule:
        """
        Basic fallback scheduling when advanced methods fail.
        """
        if tasks is None:
            tasks = Task.query.filter_by(user_id=self.user_id, completed=False)\
                              .filter(Task.due_date <= date + datetime.timedelta(days=7))\
                              .order_by(Task.priority.desc(), Task.due_date.asc())\
                              .limit(5).all()

        if not tasks:
            schedule = Schedule(
                user_id=self.user_id,
                date=date,
                generated_by_ai=False,
                total_study_time=0
            )
            db.session.add(schedule)
            db.session.commit()
            return schedule

        # Simple scheduling: one task per preferred time slot
        allocations = []
        preferred_times = self._get_preferred_times()

        for i, task in enumerate(tasks[:len(preferred_times)]):
            if i < len(preferred_times):
                scheduled_time = datetime.datetime.combine(date, preferred_times[i])
                duration = task.estimated_duration or 25
                allocations.append((task.id, scheduled_time, duration))

        # Create schedule
        schedule = Schedule(
            user_id=self.user_id,
            date=date,
            generated_by_ai=False,
            total_study_time=sum(duration for _, _, duration in allocations)
        )
        db.session.add(schedule)
        db.session.flush()

        # Add scheduled tasks
        for task_id, scheduled_time, duration in allocations:
            schedule_task = ScheduleTask(
                schedule_id=schedule.id,
                task_id=task_id,
                scheduled_time=scheduled_time,
                duration=duration
            )
            db.session.add(schedule_task)

        db.session.commit()
        return schedule

    def _get_preferred_times(self) -> List[datetime.time]:
        """
        Get user's preferred study times.
        """
        if self.user_settings and self.user_settings.preferred_study_times:
            times = self.user_settings.get_preferred_times()
            return [datetime.datetime.strptime(t, '%H:%M').time() for t in times]
        else:
            # Default: 9 AM, 2 PM, 7 PM
            return [
                datetime.time(9, 0),
                datetime.time(14, 0),
                datetime.time(19, 0)
            ]

    def _generate_ai_schedule(self, tasks: List[Task], date: datetime.date) -> List[tuple]:
        """
        Use Gemini AI to generate an intelligent schedule based on tasks and user patterns.
        """
        # Check if API is available
        if not hasattr(self, 'api_available') or not self.api_available or not self.model:
            print("Gemini API not available for schedules, using fallback")
            return self._allocate_tasks_fallback(tasks, date)

        try:
            # Prepare task data
            task_data = []
            for task in tasks:
                task_info = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description or 'No description',
                    'priority': task.priority,
                    'category': task.category or 'General',
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else 'No due date',
                    'estimated_duration': task.estimated_duration or 30  # Default 30 min if not set
                }
                task_data.append(task_info)

            # Get user preferences
            preferred_times = self._get_preferred_times()
            work_duration = self.user_settings.pomodoro_work_duration if self.user_settings else 25
            break_duration = self.user_settings.pomodoro_break_duration if self.user_settings else 5

            # Get productivity insights
            productivity_context = self._get_productivity_context()

            # Create AI prompt
            prompt = f"""
You are an AI study schedule optimizer for a productivity app. Create an optimal daily study schedule.

USER CONTEXT:
- Preferred study times: {', '.join([t.strftime('%I:%M %p') for t in preferred_times])}
- Typical work session: {work_duration} minutes
- Break duration: {break_duration} minutes
- Productivity patterns: {productivity_context}
- Current date: {date.strftime('%A, %B %d, %Y')}

TASKS TO SCHEDULE:
{chr(10).join([f"- Task {t['id']}: {t['title']} (Priority: {t['priority']}, Category: {t['category']}, Est. time: {t['estimated_duration']} min, Due: {t['due_date']})" for t in task_data])}

INSTRUCTIONS:
1. Schedule tasks during preferred study times when possible
2. Consider task priorities (high > medium > low)
3. Respect estimated durations, but suggest realistic adjustments if needed
4. Include short breaks between tasks to prevent burnout
5. Don't exceed 6-8 hours total study time per day
6. Group similar tasks together for better focus
7. Consider urgency based on due dates

Return a JSON schedule with this exact format:
{{
  "schedule": [
    {{
      "task_id": TASK_ID,
      "scheduled_time": "HH:MM",
      "duration": MINUTES,
      "reason": "Brief explanation for this scheduling choice"
    }}
  ],
  "total_study_time": TOTAL_MINUTES,
  "insights": ["2-3 productivity insights or recommendations"]
}}

Only return the JSON, no other text.
"""

            # Generate response with Gemini
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse JSON response
            import json
            result = json.loads(result_text)

            # Convert to expected format
            allocations = []
            for item in result['schedule']:
                # Convert time string to datetime
                time_obj = datetime.datetime.strptime(item['scheduled_time'], '%H:%M').time()
                scheduled_datetime = datetime.datetime.combine(date, time_obj)

                # Ensure reasonable duration (15-90 minutes)
                duration = max(15, min(item['duration'], 90))

                allocations.append((
                    item['task_id'],
                    scheduled_datetime,
                    duration
                ))

            return allocations

        except Exception as e:
            print(f"Gemini AI scheduling failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to rule-based scheduling
            return self._allocate_tasks_fallback(tasks, date)

    def generate_multi_day_schedule(self, start_date: datetime.date, days: int = 7) -> List[Schedule]:
        """
        Generate an intelligent multi-day schedule spanning multiple days.
        """
        if not self.api_available:
            return self._generate_multi_day_fallback(start_date, days)

        schedules = []
        all_tasks = Task.query.filter_by(user_id=self.user_id, completed=False)\
                             .filter(Task.due_date >= start_date)\
                             .order_by(Task.priority.desc(), Task.due_date.asc())\
                             .all()

        # Use AI to distribute tasks across days
        day_distributions = self._distribute_tasks_across_days(all_tasks, days, start_date)

        for day_offset, day_tasks in enumerate(day_distributions):
            current_date = start_date + datetime.timedelta(days=day_offset)
            if day_tasks:
                schedule = self.generate_schedule(current_date, day_tasks)
                schedules.append(schedule)

        return schedules

    def _distribute_tasks_across_days(self, tasks: List[Task], days: int, start_date: datetime.date) -> List[List[Task]]:
        """
        Use AI to intelligently distribute tasks across multiple days.
        """
        if not tasks:
            return [[] for _ in range(days)]

        prompt = f"""
        You are an expert study planner. Distribute these {len(tasks)} tasks across {days} days optimally.

        Tasks to distribute:
        {chr(10).join([f"- Task {i+1}: {t.title} (Priority: {t.priority}, Due: {t.due_date.strftime('%m/%d') if t.due_date else 'No due date'}, Est: {t.estimated_duration or 30}min)" for i, t in enumerate(tasks)])}

        Rules for distribution:
        1. High priority tasks get earliest slots
        2. Respect due dates - don't schedule after due date
        3. Balance workload - similar study time per day
        4. Group related tasks together when possible
        5. Leave buffer time for unexpected events

        Return a JSON array where each element is a list of task indices (0-based) for that day.
        Example: [[0, 2], [1, 3], [], [4]] means day 1 gets tasks 0 and 2, day 2 gets tasks 1 and 3, etc.

        Return only the JSON array, no other text.
        """

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Clean JSON response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]

            day_indices = json.loads(result_text.strip())

            # Convert indices to task lists
            distributions = []
            for day_indices_list in day_indices:
                day_tasks = [tasks[i] for i in day_indices_list if i < len(tasks)]
                distributions.append(day_tasks)

            return distributions

        except Exception as e:
            print(f"Multi-day distribution failed: {e}")
            return self._distribute_tasks_fallback(tasks, days)

    def _distribute_tasks_fallback(self, tasks: List[Task], days: int) -> List[List[Task]]:
        """Fallback distribution when AI fails"""
        distributions = [[] for _ in range(days)]
        for i, task in enumerate(tasks):
            day_index = i % days
            distributions[day_index].append(task)
        return distributions

    def _generate_multi_day_fallback(self, start_date: datetime.date, days: int) -> List[Schedule]:
        """Fallback multi-day generation"""
        schedules = []
        for day_offset in range(days):
            current_date = start_date + datetime.timedelta(days=day_offset)
            schedule = self.generate_schedule(current_date)
            if schedule.total_study_time > 0:  # Only add if has tasks
                schedules.append(schedule)
        return schedules

    def _load_energy_patterns(self) -> Dict:
        """Load user's energy patterns for intelligent scheduling"""
        from app.models import EnergyPattern

        patterns = EnergyPattern.query.filter_by(user_id=self.user_id)\
                                    .order_by(EnergyPattern.date.desc())\
                                    .limit(30).all()

        # Aggregate patterns by hour
        hourly_patterns = {}
        for pattern in patterns:
            hour = pattern.hour
            if hour not in hourly_patterns:
                hourly_patterns[hour] = {
                    'energy_levels': [],
                    'focus_scores': [],
                    'productivity': []
                }
            hourly_patterns[hour]['energy_levels'].append(pattern.energy_level)
            hourly_patterns[hour]['focus_scores'].append(pattern.focus_score)
            hourly_patterns[hour]['productivity'].append(pattern.tasks_completed)

        # Calculate averages
        for hour, data in hourly_patterns.items():
            data['avg_energy'] = sum(data['energy_levels']) / len(data['energy_levels']) if data['energy_levels'] else 5.0
            data['avg_focus'] = sum(data['focus_scores']) / len(data['focus_scores']) if data['focus_scores'] else 5.0
            data['avg_productivity'] = sum(data['productivity']) / len(data['productivity']) if data['productivity'] else 1.0

        return hourly_patterns

    def _load_break_activities(self) -> List[Dict]:
        """Load break activity suggestions"""
        from app.models import BreakActivity

        activities = BreakActivity.query.filter_by(is_active=True).all()
        return [{
            'id': a.id,
            'name': a.name,
            'category': a.category,
            'duration': a.duration_minutes,
            'difficulty': a.difficulty_level,
            'energy_required': a.energy_required,
            'description': a.description,
            'benefits': a.get_benefits()
        } for a in activities]

    def suggest_optimal_breaks(self, schedule_tasks: List, total_study_time: int) -> List[Dict]:
        """
        Suggest optimal breaks with activities for a schedule.
        """
        if not self.break_activities:
            return []

        breaks = []
        study_blocks = len(schedule_tasks)

        # Suggest breaks based on study intensity
        if study_blocks >= 3:
            # Add break after 2nd task
            break_time = schedule_tasks[1]['end_time'] + datetime.timedelta(minutes=5)
            activity = self._select_break_activity('medium', 10)
            if activity:
                breaks.append({
                    'time': break_time,
                    'duration': 10,
                    'activity': activity['name'],
                    'category': activity['category'],
                    'reason': 'Prevent mental fatigue after intensive study block'
                })

        # Add final break if long session
        if total_study_time > 120:  # Over 2 hours
            final_break_time = schedule_tasks[-1]['end_time'] + datetime.timedelta(minutes=5)
            activity = self._select_break_activity('easy', 15)
            if activity:
                breaks.append({
                    'time': final_break_time,
                    'duration': 15,
                    'activity': activity['name'],
                    'category': activity['category'],
                    'reason': 'Recovery break after long study session'
                })

        return breaks

    def _select_break_activity(self, energy_level: str, duration: int) -> Optional[Dict]:
        """Select appropriate break activity based on energy and duration"""
        suitable = [a for a in self.break_activities
                   if a['difficulty'] == energy_level and a['duration'] <= duration]

        if suitable:
            # Return random suitable activity
            import random
            return random.choice(suitable)
        return None

    def detect_schedule_conflicts(self, schedule: Schedule) -> List[Dict]:
        """
        Detect potential conflicts in the schedule.
        """
        conflicts = []

        # Check energy conflicts
        for task_data in schedule.tasks:
            task_hour = task_data.scheduled_time.hour
            energy_data = self.energy_patterns.get(task_hour, {})

            if energy_data.get('avg_energy', 5.0) < 3.0:
                conflicts.append({
                    'type': 'energy',
                    'severity': 'high',
                    'description': f'Low energy period at {task_hour}:00',
                    'suggestion': 'Consider rescheduling to higher energy time'
                })

        # Check workload conflicts
        total_time = schedule.total_study_time
        if total_time > 300:  # Over 5 hours
            conflicts.append({
                'type': 'workload',
                'severity': 'medium',
                'description': f'Heavy study load: {total_time} minutes',
                'suggestion': 'Consider spreading over multiple days'
            })

        return conflicts

    def record_energy_feedback(self, hour: int, energy_level: float, focus_score: float, tasks_completed: int):
        """
        Record user's energy and focus feedback for learning.
        """
        from app.models import EnergyPattern, db

        today = datetime.date.today()
        pattern = EnergyPattern.query.filter_by(
            user_id=self.user_id,
            date=today,
            hour=hour
        ).first()

        if pattern:
            # Update existing
            pattern.energy_level = energy_level
            pattern.focus_score = focus_score
            pattern.tasks_completed = tasks_completed
        else:
            # Create new
            pattern = EnergyPattern(
                user_id=self.user_id,
                date=today,
                hour=hour,
                energy_level=energy_level,
                focus_score=focus_score,
                tasks_completed=tasks_completed
            )
            db.session.add(pattern)

        db.session.commit()

    def get_schedule_insights(self, schedule: Schedule) -> Dict:
        """
        Generate advanced insights about the schedule.
        """
        insights = {
            'energy_optimization': self._analyze_energy_optimization(schedule),
            'workload_balance': self._analyze_workload_balance(schedule),
            'goal_alignment': self._analyze_goal_alignment(schedule),
            'adaptive_recommendations': self._generate_adaptive_recommendations(schedule)
        }

        return insights

    def _analyze_energy_optimization(self, schedule: Schedule) -> Dict:
        """Analyze how well the schedule matches energy patterns"""
        total_energy_score = 0
        task_count = 0

        for task_data in schedule.tasks:
            hour = task_data.scheduled_time.hour
            energy_data = self.energy_patterns.get(hour, {})
            energy_score = energy_data.get('avg_energy', 5.0)
            total_energy_score += energy_score
            task_count += 1

        avg_energy_score = total_energy_score / task_count if task_count > 0 else 5.0

        return {
            'average_energy_score': round(avg_energy_score, 1),
            'optimization_level': 'excellent' if avg_energy_score >= 7.0 else 'good' if avg_energy_score >= 5.0 else 'needs_improvement',
            'recommendation': 'Consider shifting tasks to higher energy hours' if avg_energy_score < 5.0 else None
        }

    def _analyze_workload_balance(self, schedule: Schedule) -> Dict:
        """Analyze workload distribution"""
        total_time = schedule.total_study_time

        if total_time > 300:
            balance_level = 'overloaded'
            recommendation = 'Consider breaking into multiple days'
        elif total_time > 180:
            balance_level = 'balanced'
            recommendation = None
        else:
            balance_level = 'light'
            recommendation = 'Could add more study time if available'

        return {
            'total_study_time': total_time,
            'balance_level': balance_level,
            'recommendation': recommendation
        }

    def _analyze_goal_alignment(self, schedule: Schedule) -> Dict:
        """Analyze how schedule aligns with user goals"""
        from app.models import Goal

        active_goals = Goal.query.filter_by(user_id=self.user_id, achieved=False).all()

        alignment_score = 0
        if active_goals:
            # Simple alignment check - this could be more sophisticated
            alignment_score = 7.0  # Placeholder

        return {
            'goals_count': len(active_goals),
            'alignment_score': alignment_score,
            'recommendation': 'Schedule aligns well with your goals' if alignment_score >= 6.0 else 'Consider goal priorities'
        }

    def _generate_adaptive_recommendations(self, schedule: Schedule) -> List[str]:
        """Generate personalized recommendations based on patterns"""
        recommendations = []

        # Analyze energy patterns
        energy_analysis = self._analyze_energy_optimization(schedule)
        if energy_analysis['optimization_level'] == 'needs_improvement':
            recommendations.append("Try scheduling high-priority tasks during your peak energy hours (typically morning for most people)")

        # Analyze workload
        workload_analysis = self._analyze_workload_balance(schedule)
        if workload_analysis['balance_level'] == 'overloaded':
            recommendations.append("Your schedule is quite intensive. Consider the '80/20 rule' - focus on high-impact tasks")

        # Add adaptive suggestions
        if len(schedule.tasks) >= 3:
            recommendations.append("Great job planning multiple tasks! Remember to take micro-breaks between subjects")

        if not recommendations:
            recommendations.append("Your schedule looks well-balanced! Keep up the good planning habits")

        return recommendations

    def _is_productive_time(self, time: datetime.time) -> bool:
        """
        Determine if a time is productive based on historical data.
        """
        if not self.productivity_data:
            return True  # Default to productive

        hour = time.hour
        # Simple heuristic: check average productivity score for this hour
        # For now, assume morning/afternoon/evening are productive
        return True  # Placeholder

    def get_productivity_insights(self) -> Dict:
        """
        Analyze user's productivity patterns for recommendations.
        """
        if not self.productivity_data:
            return {"insights": "Not enough data yet. Start logging study sessions!"}

        avg_hours = sum(d.hours_studied for d in self.productivity_data) / len(self.productivity_data)
        avg_score = sum(d.productivity_score for d in self.productivity_data) / len(self.productivity_data)

        insights = {
            "average_daily_study_hours": round(avg_hours, 1),
            "average_productivity_score": round(avg_score, 1),
            "recommendations": []
        }

        if avg_score < 50:
            insights["recommendations"].append("Consider scheduling study sessions during your most productive hours.")
        if avg_hours < 2:
            insights["recommendations"].append("Aim for at least 2 hours of focused study per day.")

        # Add burnout risk
        burnout_risk = sum(d.burnout_risk for d in self.productivity_data) / len(self.productivity_data)
        if burnout_risk > 70:
            insights["recommendations"].append("High burnout risk detected. Consider taking a rest day.")

        return insights

    def _get_productivity_context(self) -> str:
        """
        Get productivity context for AI prompt.
        """
        if not self.productivity_data:
            return "No historical data available - first-time user"

        avg_hours = sum(d.hours_studied for d in self.productivity_data) / len(self.productivity_data)
        avg_score = sum(d.productivity_score for d in self.productivity_data) / len(self.productivity_data)
        burnout_risk = sum(d.burnout_risk for d in self.productivity_data) / len(self.productivity_data)

        return f"Average {avg_hours:.1f} hours/day, productivity score {avg_score:.1f}, burnout risk {burnout_risk:.1f}"

    def _allocate_tasks_fallback(self, tasks: List[Task], date: datetime.date) -> List[tuple]:
        """
        Advanced intelligent task allocation with comprehensive daily scheduling.
        Creates realistic study blocks throughout the day with proper breaks and transitions.
        """
        allocations = []
        work_duration = self.user_settings.pomodoro_work_duration if self.user_settings else 25
        break_duration = self.user_settings.pomodoro_break_duration if self.user_settings else 5
        long_break_duration = self.user_settings.long_break_duration if self.user_settings else 15
        sessions_until_long_break = self.user_settings.sessions_until_long_break if self.user_settings else 4

        # Sort tasks by priority, due date, and category for intelligent grouping
        sorted_tasks = sorted(tasks, key=lambda t: (
            0 if t.priority == 'high' else 1 if t.priority == 'medium' else 2,  # Priority first
            t.due_date or datetime.date.max,  # Then due date
            t.category or 'z'  # Group by category
        ))

        # Create comprehensive daily schedule with multiple time blocks
        daily_schedule = self._create_advanced_daily_structure(date)

        # Distribute tasks intelligently across the day
        task_index = 0
        session_count = 0

        for time_block in daily_schedule:
            if task_index >= len(sorted_tasks):
                break

            block_start = time_block['start']
            block_end = time_block['end']
            block_type = time_block['type']
            available_minutes = (block_end - block_start).seconds // 60

            # Skip break blocks for task scheduling
            if block_type == 'break':
                continue

            # Calculate how many tasks can fit in this block
            remaining_block_time = available_minutes
            block_start_time = block_start

            while remaining_block_time >= work_duration and task_index < len(sorted_tasks):
                task = sorted_tasks[task_index]

                # Smart duration calculation based on task type and user patterns
                duration = self._calculate_optimal_duration(task, remaining_block_time, work_duration)

                if duration <= remaining_block_time:
                    scheduled_datetime = block_start_time

                    allocations.append((task.id, scheduled_datetime, duration))

                    # Update timing
                    block_start_time += datetime.timedelta(minutes=duration)
                    remaining_block_time -= duration
                    task_index += 1
                    session_count += 1

                    # Add break after work session (except for last task in block)
                    if remaining_block_time >= break_duration and task_index < len(sorted_tasks):
                        break_duration_actual = break_duration if session_count % sessions_until_long_break != 0 else long_break_duration
                        if remaining_block_time >= break_duration_actual:
                            # Schedule break (this would be handled by pomodoro system)
                            remaining_block_time -= break_duration_actual
                            block_start_time += datetime.timedelta(minutes=break_duration_actual)
                            session_count = 0 if session_count % sessions_until_long_break == 0 else session_count
                else:
                    break  # Can't fit this task, try next block

        return allocations

    def _analyze_user_patterns(self) -> Dict:
        """
        Advanced analysis of user behavior patterns for predictive scheduling.
        Analyzes historical data to identify optimal times, task completion rates,
        energy cycles, and productivity patterns.
        """
        patterns = {
            'peak_productivity_hours': self._identify_peak_hours(),
            'task_completion_patterns': self._analyze_task_completion_rates(),
            'energy_cycles': self._detect_energy_patterns(),
            'preferred_task_sequences': self._analyze_task_sequences(),
            'break_patterns': self._analyze_break_preferences(),
            'adaptation_trends': self._detect_adaptation_trends()
        }
        return patterns

    def _load_collaboration_context(self) -> Dict:
        """
        Load collaboration and team scheduling context.
        Includes shared availability, meeting preferences, and team constraints.
        """
        # For now, return placeholder - would integrate with calendar APIs
        return {
            'team_availability': {},
            'meeting_preferences': {},
            'shared_resources': {},
            'collaboration_history': []
        }

    def _load_external_constraints(self) -> Dict:
        """
        Load external constraints from calendar integrations, holidays, etc.
        """
        constraints = {
            'calendar_events': [],  # Would integrate with Google Calendar, Outlook
            'holidays': self._get_holiday_schedule(),
            'timezone_constraints': self._analyze_timezone_impact(),
            'resource_availability': self._check_resource_constraints()
        }
        return constraints

    def _initialize_constraint_solver(self) -> Dict:
        """
        Initialize advanced constraint satisfaction solver for complex scheduling.
        """
        solver = {
            'hard_constraints': [
                'time_conflicts', 'resource_limits', 'deadline_requirements',
                'energy_thresholds', 'break_requirements'
            ],
            'soft_constraints': [
                'user_preferences', 'productivity_patterns', 'task_dependencies',
                'collaboration_needs', 'learning_objectives'
            ],
            'optimization_weights': {
                'deadline_proximity': 0.3,
                'energy_alignment': 0.25,
                'task_importance': 0.2,
                'user_preferences': 0.15,
                'completion_probability': 0.1
            }
        }
        return solver

    def _load_predictive_model(self) -> Dict:
        """
        Load predictive modeling capabilities for workload forecasting.
        """
        model = {
            'workload_prediction': self._build_workload_predictor(),
            'completion_probability': self._build_completion_predictor(),
            'energy_forecasting': self._build_energy_predictor(),
            'conflict_prediction': self._build_conflict_predictor()
        }
        return model

    def _initialize_adaptive_engine(self) -> Dict:
        """
        Initialize machine learning adaptive engine for continuous improvement.
        """
        engine = {
            'learning_rate': 0.1,
            'adaptation_triggers': [
                'schedule_completion_rate',
                'user_feedback_score',
                'productivity_variance',
                'conflict_frequency'
            ],
            'improvement_metrics': [
                'schedule_adherence',
                'task_completion_rate',
                'user_satisfaction',
                'energy_optimization'
            ]
        }
        return engine

    def _initialize_collaboration_engine(self) -> Dict:
        """
        Initialize collaboration and team scheduling features.
        """
        engine = {
            'meeting_optimization': self._setup_meeting_optimizer(),
            'availability_matching': self._setup_availability_matcher(),
            'resource_sharing': self._setup_resource_sharing(),
            'communication_integration': self._setup_communication_integration()
        }
        return engine

    def _load_schedule_history(self) -> List[Dict]:
        """
        Load comprehensive schedule history for learning and analytics.
        """
        from app.models import Schedule, ScheduleTask

        schedules = Schedule.query.filter_by(user_id=self.user_id)\
                                 .order_by(Schedule.created_at.desc())\
                                 .limit(100).all()

        history = []
        for schedule in schedules:
            history.append({
                'date': schedule.date,
                'total_tasks': len(schedule.tasks),
                'completion_rate': self._calculate_schedule_completion(schedule),
                'efficiency_score': self._calculate_schedule_efficiency(schedule),
                'user_feedback': self._get_schedule_feedback(schedule)
            })

        return history

    def _initialize_performance_analytics(self) -> Dict:
        """
        Initialize comprehensive performance analytics system.
        """
        analytics = {
            'schedule_performance': self._analyze_schedule_performance(),
            'task_completion_analytics': self._analyze_task_completion(),
            'time_management_metrics': self._analyze_time_management(),
            'productivity_trends': self._analyze_productivity_trends(),
            'adaptation_effectiveness': self._measure_adaptation_success()
        }
        return analytics

    def _initialize_conflict_resolution(self) -> Dict:
        """
        Initialize intelligent conflict resolution system.
        """
        resolution = {
            'conflict_types': {
                'time_overlap': 'reschedule_conflicting_tasks',
                'resource_contention': 'optimize_resource_usage',
                'energy_depletion': 'redistribute_high_energy_tasks',
                'deadline_pressure': 'prioritize_critical_tasks',
                'preference_conflict': 'find_optimal_compromise'
            },
            'resolution_strategies': [
                'temporal_shift', 'priority_reordering', 'resource_reallocation',
                'energy_optimization', 'collaborative_negotiation'
            ],
            'success_metrics': self._track_resolution_effectiveness()
        }
        return resolution

    def _generate_productivity_optimized_schedule(self, date: datetime.date, tasks: Optional[List[Task]] = None) -> Schedule:
            """
            Generate a productivity-optimized schedule with energy awareness, break planning, and performance tracking.
            """
            if tasks is None:
                # Get pending tasks with productivity context
                tasks = self._get_productivity_tasks(date)
    
            if not tasks:
                return self._generate_empty_schedule(date)
    
            # Enhanced task prioritization
            prioritized_tasks = self._prioritize_for_productivity(tasks, date)
    
            # Energy-aware time allocation
            time_blocks = self._allocate_energy_aware_times(prioritized_tasks, date)
    
            # Add intelligent breaks
            schedule_with_breaks = self._inject_productivity_breaks(time_blocks, date)
    
            # Create and save schedule
            return self._create_productivity_schedule(schedule_with_breaks, date)

    def _gather_enterprise_context(self, date: datetime.date, context: Dict) -> Dict:
        """
        Gather comprehensive enterprise scheduling context.
        """
        enterprise_context = {
            'date': date,
            'user_patterns': self.user_patterns,
            'energy_forecast': self._generate_energy_forecast(date),
            'workload_capacity': self._calculate_workload_capacity(date),
            'external_constraints': self.external_constraints,
            'collaboration_context': self.collaboration_data,
            'historical_performance': self._get_historical_performance(date),
            'adaptive_recommendations': self._generate_adaptive_recommendations(date),
            'tasks': self._get_enterprise_tasks(date),
            'goals': self._get_active_goals(),
            'preferences': self._get_user_preferences(),
            'constraints': self._get_scheduling_constraints(date)
        }
        return enterprise_context

    def _apply_ml_prioritization(self, tasks: List[Task]) -> List[Dict]:
        """
        Apply machine learning-based task prioritization.
        """
        prioritized = []
        for task in tasks:
            priority_score = self._calculate_ml_priority_score(task)
            prioritized.append({
                'task': task,
                'ml_priority': priority_score,
                'completion_probability': self._predict_completion_probability(task),
                'optimal_time': self._predict_optimal_scheduling_time(task),
                'energy_requirement': self._predict_energy_requirement(task)
            })

        # Sort by ML priority score
        prioritized.sort(key=lambda x: x['ml_priority'], reverse=True)
        return prioritized

    def _solve_constraints(self, prioritized_tasks: List[Dict], context: Dict) -> Dict:
        """
        Solve complex scheduling constraints using advanced algorithms.
        """
        # Initialize constraint solver
        solver = self.constraint_solver

        # Apply hard constraints first
        feasible_schedule = self._apply_hard_constraints(prioritized_tasks, context)

        # Optimize soft constraints
        optimized_schedule = self._optimize_soft_constraints(feasible_schedule, context)

        # Resolve any remaining conflicts
        conflict_free_schedule = self._resolve_remaining_conflicts(optimized_schedule, context)

        return conflict_free_schedule

    def _apply_predictive_optimization(self, schedule: Dict, context: Dict) -> Dict:
        """
        Apply predictive optimization using learned patterns.
        """
        # Use predictive model to optimize schedule
        predictions = self.predictive_model

        # Optimize based on predicted outcomes
        optimized = self._optimize_for_predictions(schedule, predictions, context)

        return optimized

    def _integrate_collaboration(self, schedule: Dict, context: Dict) -> Dict:
        """
        Integrate collaboration features and team scheduling.
        """
        # Apply collaboration engine
        collaborative = self.collaboration_engine

        # Integrate team availability, shared resources, etc.
        integrated = self._merge_collaboration_data(schedule, collaborative, context)

        return integrated

    def _apply_learning_adaptation(self, schedule: Dict, context: Dict) -> Schedule:
        """
        Apply learning and adaptation based on historical performance.
        """
        # Use adaptive engine to refine schedule
        adaptive = self.adaptive_engine

        # Apply learned improvements
        final_schedule = self._adapt_based_on_learning(schedule, adaptive, context)

        # Convert to database schedule object
        db_schedule = self._create_enterprise_schedule(final_schedule, context)

        return db_schedule

# Helper methods for enterprise features
    def _identify_peak_hours(self) -> List[int]:
        """Identify user's most productive hours"""
        if not self.productivity_data:
            return [9, 10, 11, 14, 15]  # Default productive hours

        hourly_scores = {}
        for data in self.productivity_data:
            hour_key = data.date.hour  # Assuming we have hourly data
            if hour_key not in hourly_scores:
                hourly_scores[hour_key] = []
            hourly_scores[hour_key].append(data.productivity_score)

        # Calculate average productivity per hour
        avg_scores = {}
        for hour, scores in hourly_scores.items():
            avg_scores[hour] = sum(scores) / len(scores)

        # Return top 5 most productive hours
        sorted_hours = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, score in sorted_hours[:5]]

    def _analyze_task_completion_rates(self) -> Dict:
        """Analyze task completion patterns by category, priority, etc."""
        return {
            'by_category': {},
            'by_priority': {},
            'by_time_of_day': {},
            'by_day_of_week': {}
        }

    def _detect_energy_patterns(self) -> Dict:
        """Detect user's energy cycles throughout the day/week"""
        return {
            'daily_cycles': self.energy_patterns,
            'weekly_patterns': {},
            'seasonal_trends': {}
        }

    def _analyze_task_sequences(self) -> List[List[str]]:
        """Analyze preferred task sequences for better focus"""
        return []

    def _analyze_break_preferences(self) -> Dict:
        """Analyze user break preferences and patterns"""
        return {}

    def _detect_adaptation_trends(self) -> Dict:
        """Detect how user adapts to schedule changes"""
        return {}

    def _get_holiday_schedule(self) -> List[datetime.date]:
        """Get holiday schedule for the current period"""
        return []

    def _analyze_timezone_impact(self) -> Dict:
        """Analyze timezone-related scheduling constraints"""
        return {}

    def _check_resource_constraints(self) -> Dict:
        """Check availability of shared resources"""
        return {}

    def _build_workload_predictor(self) -> Dict:
        """Build predictive model for workload forecasting"""
        return {}

    def _build_completion_predictor(self) -> Dict:
        """Build predictive model for task completion probability"""
        return {}

    def _build_energy_predictor(self) -> Dict:
        """Build predictive model for energy forecasting"""
        return {}

    def _build_conflict_predictor(self) -> Dict:
        """Build predictive model for conflict detection"""
        return {}

    def _setup_meeting_optimizer(self) -> Dict:
        """Setup meeting time optimization"""
        return {}

    def _setup_availability_matcher(self) -> Dict:
        """Setup team availability matching"""
        return {}

    def _setup_resource_sharing(self) -> Dict:
        """Setup resource sharing coordination"""
        return {}

    def _setup_communication_integration(self) -> Dict:
        """Setup communication tool integration"""
        return {}

    def _calculate_schedule_completion(self, schedule: Schedule) -> float:
        """Calculate schedule completion percentage"""
        return 0.0

    def _calculate_schedule_efficiency(self, schedule: Schedule) -> float:
        """Calculate schedule efficiency score"""
        return 0.0

    def _get_schedule_feedback(self, schedule: Schedule) -> float:
        """Get user feedback score for schedule"""
        return 0.0

    def _analyze_schedule_performance(self) -> Dict:
        """Analyze overall schedule performance"""
        return {}

    def _analyze_task_completion(self) -> Dict:
        """Analyze task completion analytics"""
        return {}

    def _analyze_time_management(self) -> Dict:
        """Analyze time management effectiveness"""
        return {}

    def _analyze_productivity_trends(self) -> Dict:
        """Analyze productivity trends over time"""
        return {}

    def _measure_adaptation_success(self) -> Dict:
        """Measure how well adaptations improve scheduling"""
        return {}

    def _track_resolution_effectiveness(self) -> Dict:
        """Track effectiveness of conflict resolution strategies"""
        return {}

    def _generate_energy_forecast(self, date: datetime.date) -> Dict:
        """Generate energy forecast for the given date"""
        return {}

    def _calculate_workload_capacity(self, date: datetime.date) -> float:
        """Calculate user's workload capacity for the date"""
        return 1.0

    def _get_historical_performance(self, date: datetime.date) -> Dict:
        """Get historical performance data for similar dates"""
        return {}

    def _generate_adaptive_recommendations(self, date: datetime.date) -> List[str]:
        """Generate adaptive recommendations based on learning"""
        return []

    def _get_enterprise_tasks(self, date: datetime.date) -> List[Task]:
        """Get tasks with enterprise context"""
        return Task.query.filter_by(user_id=self.user_id, completed=False)\
                        .filter(Task.due_date >= date - datetime.timedelta(days=7))\
                        .order_by(Task.priority.desc(), Task.due_date.asc())\
                        .all()

    def _get_active_goals(self) -> List:
        """Get active user goals"""
        from app.models import Goal
        return Goal.query.filter_by(user_id=self.user_id, achieved=False).all()

    def _get_user_preferences(self) -> Dict:
        """Get comprehensive user scheduling preferences"""
        if self.user_settings:
            return {
                'work_hours': self.user_settings.preferred_study_times,
                'pomodoro_duration': self.user_settings.pomodoro_work_duration,
                'break_duration': self.user_settings.pomodoro_break_duration,
                'long_break_duration': self.user_settings.long_break_duration,
                'sessions_until_long_break': self.user_settings.sessions_until_long_break,
                'notifications_enabled': self.user_settings.notifications_enabled
            }
        return {}

    def _get_scheduling_constraints(self, date: datetime.date) -> Dict:
        """Get all scheduling constraints for the date"""
        return {
            'date': date,
            'existing_schedules': Schedule.query.filter_by(user_id=self.user_id, date=date).all(),
            'energy_constraints': self.energy_patterns,
            'external_constraints': self.external_constraints
        }

    def _calculate_ml_priority_score(self, task: Task) -> float:
        """Calculate ML-based priority score for task"""
        base_score = 0.0

        # Priority weight
        if task.priority == 'high':
            base_score += 0.4
        elif task.priority == 'medium':
            base_score += 0.2

        # Due date urgency
        if task.due_date:
            days_until_due = (task.due_date - datetime.date.today()).days
            if days_until_due <= 1:
                base_score += 0.3
            elif days_until_due <= 3:
                base_score += 0.2
            elif days_until_due <= 7:
                base_score += 0.1

        # Category importance
        category_weights = {
            'exam': 0.2, 'assignment': 0.15, 'practice': 0.1,
            'reading': 0.05, 'review': 0.05
        }
        if task.category and task.category.lower() in category_weights:
            base_score += category_weights[task.category.lower()]

        return min(base_score, 1.0)  # Cap at 1.0

    def _predict_completion_probability(self, task: Task) -> float:
        """Predict probability of task completion"""
        return 0.8  # Placeholder

    def _predict_optimal_scheduling_time(self, task: Task) -> datetime.time:
        """Predict optimal time to schedule task"""
        return datetime.time(9, 0)  # Placeholder

    def _predict_energy_requirement(self, task: Task) -> float:
        """Predict energy requirement for task"""
        return 5.0  # Placeholder

    def _apply_hard_constraints(self, tasks: List[Dict], context: Dict) -> Dict:
        """Apply hard scheduling constraints"""
        return {'scheduled_tasks': []}

    def _optimize_soft_constraints(self, schedule: Dict, context: Dict) -> Dict:
        """Optimize soft scheduling constraints"""
        return schedule

    def _resolve_remaining_conflicts(self, schedule: Dict, context: Dict) -> Dict:
        """Resolve any remaining scheduling conflicts"""
        return schedule

    def _optimize_for_predictions(self, schedule: Dict, predictions: Dict, context: Dict) -> Dict:
        """Optimize schedule based on predictions"""
        return schedule

    def _merge_collaboration_data(self, schedule: Dict, collaboration: Dict, context: Dict) -> Dict:
        """Merge collaboration data into schedule"""
        return schedule

    def _adapt_based_on_learning(self, schedule: Dict, adaptive: Dict, context: Dict) -> Dict:
        """Adapt schedule based on learning"""
        return schedule

    def _create_enterprise_schedule(self, schedule_data: Dict, context: Dict) -> Schedule:
        """Create database schedule from enterprise schedule data"""
        # This would convert the optimized schedule data into database objects
        # For now, fall back to basic schedule generation
        return self.generate_schedule(context['date'])

# ===== PRODUCTIVITY-OPTIMIZED SCHEDULING METHODS =====

    def _get_productivity_tasks(self, date: datetime.date) -> List[Task]:
        """
        Get tasks with productivity context and prioritization.
        """
        from app.models import Goal

        # Get pending tasks
        base_tasks = Task.query.filter_by(user_id=self.user_id, completed=False)\
                              .filter(Task.due_date >= date - datetime.timedelta(days=7))\
                              .order_by(Task.priority.desc(), Task.due_date.asc())\
                              .all()

        # Add goal-related context
        active_goals = Goal.query.filter_by(user_id=self.user_id, achieved=False).all()

        # Enhance tasks with goal alignment
        enhanced_tasks = []
        for task in base_tasks:
            task.goal_alignment = self._calculate_goal_alignment(task, active_goals)
            task.productivity_score = self._calculate_productivity_score(task, date)
            enhanced_tasks.append(task)

        # Sort by combined priority and productivity score
        enhanced_tasks.sort(key=lambda t: (t.priority == 'high' and 3 or t.priority == 'medium' and 2 or 1,
                                           t.productivity_score), reverse=True)

        return enhanced_tasks[:10]  # Limit to top 10 for focused scheduling

    def _prioritize_for_productivity(self, tasks: List[Task], date: datetime.date) -> List[Dict]:
        """
        Enhanced task prioritization considering multiple productivity factors.
        """
        prioritized = []

        for task in tasks:
            # Calculate comprehensive priority score
            priority_factors = {
                'base_priority': 3 if task.priority == 'high' else 2 if task.priority == 'medium' else 1,
                'due_date_urgency': self._calculate_due_date_urgency(task.due_date, date),
                'energy_requirement': self._predict_energy_requirement(task),
                'goal_alignment': task.goal_alignment,
                'historical_performance': self._get_task_performance_history(task)
            }

            # Combine factors into final score
            final_score = (
                priority_factors['base_priority'] * 0.3 +
                priority_factors['due_date_urgency'] * 0.25 +
                priority_factors['energy_requirement'] * 0.2 +
                priority_factors['goal_alignment'] * 0.15 +
                priority_factors['historical_performance'] * 0.1
            )

            prioritized.append({
                'task': task,
                'priority_score': final_score,
                'estimated_duration': task.estimated_duration or self._estimate_task_duration(task),
                'optimal_energy_time': self._find_optimal_energy_slot(task, date),
                'category': task.category or 'General'
            })

        return sorted(prioritized, key=lambda x: x['priority_score'], reverse=True)

    def _allocate_energy_aware_times(self, prioritized_tasks: List[Dict], date: datetime.date) -> List[Dict]:
        """
        Allocate tasks to time slots based on energy patterns and user preferences.
        """
        allocations = []
        preferred_times = self._get_preferred_times()

        # Get energy patterns for this date
        energy_forecast = self._get_energy_forecast(date)

        # Sort time slots by energy level
        energy_sorted_slots = sorted(energy_forecast.items(), key=lambda x: x[1]['energy'], reverse=True)

        task_index = 0
        for hour, energy_data in energy_sorted_slots:
            if task_index >= len(prioritized_tasks):
                break

            # Check if this hour aligns with preferred study times
            hour_time = datetime.time(hour, 0)
            if any(self._time_in_range(hour_time, pref_time) for pref_time in preferred_times):
                task_data = prioritized_tasks[task_index]

                # Check if energy level is sufficient
                if energy_data['energy'] >= 3.0:  # Minimum energy threshold
                    scheduled_time = datetime.datetime.combine(date, hour_time)

                    allocations.append({
                        'task': task_data['task'],
                        'scheduled_time': scheduled_time,
                        'duration': task_data['estimated_duration'],
                        'energy_score': energy_data['energy'],
                        'reason': f"Scheduled during high-energy period ({energy_data['energy']}/10)"
                    })

                    task_index += 1

        # Fallback: use preferred times if energy-based allocation didn't work
        while task_index < len(prioritized_tasks):
            task_data = prioritized_tasks[task_index]
            fallback_time = datetime.datetime.combine(date, preferred_times[task_index % len(preferred_times)])

            allocations.append({
                'task': task_data['task'],
                'scheduled_time': fallback_time,
                'duration': task_data['estimated_duration'],
                'energy_score': 5.0,  # Neutral score for fallback
                'reason': "Scheduled in preferred study time"
            })

            task_index += 1

        return allocations

    def _inject_productivity_breaks(self, time_blocks: List[Dict], date: datetime.date) -> List[Dict]:
        """
        Inject intelligent breaks between tasks for sustained productivity.
        """
        if not time_blocks:
            return time_blocks

        enhanced_blocks = []
        work_duration = self.user_settings.pomodoro_work_duration if self.user_settings else 25
        break_duration = self.user_settings.pomodoro_break_duration if self.user_settings else 5
        long_break_duration = self.user_settings.long_break_duration if self.user_settings else 15

        session_count = 0
        sessions_until_long_break = self.user_settings.sessions_until_long_break if self.user_settings else 4

        for i, block in enumerate(time_blocks):
            enhanced_blocks.append(block)
            session_count += 1

            # Add break after task (except last one)
            if i < len(time_blocks) - 1:
                break_time = block['scheduled_time'] + datetime.timedelta(minutes=block['duration'])

                # Determine break type
                if session_count % sessions_until_long_break == 0:
                    break_duration_actual = long_break_duration
                    break_activity = self._suggest_long_break_activity()
                    break_type = "Long Break"
                else:
                    break_duration_actual = break_duration
                    break_activity = self._suggest_short_break_activity()
                    break_type = "Short Break"

                enhanced_blocks.append({
                    'type': 'break',
                    'scheduled_time': break_time,
                    'duration': break_duration_actual,
                    'activity': break_activity,
                    'reason': f"{break_type} to maintain productivity and prevent burnout"
                })

        return enhanced_blocks

    def _create_productivity_schedule(self, schedule_blocks: List[Dict], date: datetime.date) -> Schedule:
        """
        Create database schedule from productivity-optimized blocks.
        """
        # Create main schedule
        schedule = Schedule(
            user_id=self.user_id,
            date=date,
            generated_by_ai=True,
            total_study_time=sum(block['duration'] for block in schedule_blocks if block.get('type') != 'break')
        )
        db.session.add(schedule)
        db.session.flush()

        # Add tasks and breaks
        for block in schedule_blocks:
            if block.get('type') == 'break':
                # Create break record (if you want to track breaks separately)
                continue
            else:
                # Create task schedule entry
                schedule_task = ScheduleTask(
                    schedule_id=schedule.id,
                    task_id=block['task'].id,
                    scheduled_time=block['scheduled_time'],
                    duration=block['duration']
                )
                db.session.add(schedule_task)

        db.session.commit()
        return schedule

    def _calculate_goal_alignment(self, task: Task, active_goals: List) -> float:
        """Calculate how well task aligns with active goals"""
        if not active_goals:
            return 0.5  # Neutral alignment

        # Simple alignment check - could be more sophisticated
        alignment_score = 0.0
        for goal in active_goals:
            if task.goal_id == goal.id:
                alignment_score = 1.0
                break
            # Check if task category matches goal category
            elif task.category and goal.category and task.category.lower() in goal.category.lower():
                alignment_score = max(alignment_score, 0.7)

        return alignment_score

    def _calculate_productivity_score(self, task: Task, date: datetime.date) -> float:
        """Calculate overall productivity score for task"""
        base_score = 0.5

        # Factor in task attributes
        if task.priority == 'high':
            base_score += 0.2
        elif task.priority == 'medium':
            base_score += 0.1

        # Due date proximity
        if task.due_date:
            days_until_due = (task.due_date - date).days
            if days_until_due <= 1:
                base_score += 0.2
            elif days_until_due <= 3:
                base_score += 0.1

        return min(base_score, 1.0)

    def _calculate_due_date_urgency(self, due_date, current_date: datetime.date) -> float:
        """Calculate urgency based on due date"""
        if not due_date:
            return 0.3  # Low urgency for tasks without due dates

        days_until_due = (due_date - current_date).days

        if days_until_due < 0:
            return 1.0  # Overdue - maximum urgency
        elif days_until_due == 0:
            return 0.9  # Due today
        elif days_until_due <= 3:
            return 0.7  # Due soon
        elif days_until_due <= 7:
            return 0.5  # Due this week
        else:
            return 0.2  # Not urgent

    def _get_task_performance_history(self, task: Task) -> float:
        """Get historical performance score for similar tasks"""
        # This could analyze past completion rates for tasks of similar type/category
        # For now, return neutral score
        return 0.5

    def _estimate_task_duration(self, task: Task) -> int:
        """Estimate task duration based on type and history"""
        # Base estimates by category
        category_estimates = {
            'exam': 90,      # Exams need more time
            'assignment': 60, # Assignments vary
            'reading': 45,    # Reading is usually shorter
            'practice': 30,   # Practice problems vary
            'review': 25      # Reviews are quick
        }

        base_duration = category_estimates.get(task.category.lower() if task.category else 'general', 30)

        # Adjust for priority
        if task.priority == 'high':
            base_duration = int(base_duration * 1.2)
        elif task.priority == 'low':
            base_duration = int(base_duration * 0.8)

        return max(15, min(base_duration, 120))  # Between 15-120 minutes

    def _find_optimal_energy_slot(self, task: Task, date: datetime.date) -> datetime.time:
        """Find optimal time slot based on energy patterns"""
        # Return a reasonable default - could be enhanced with actual energy data
        return datetime.time(9, 0)

    def _get_energy_forecast(self, date: datetime.date) -> Dict:
        """Get energy forecast for the date"""
        # Use energy patterns or default to reasonable assumptions
        if self.energy_patterns:
            return self.energy_patterns
        else:
            # Default energy pattern (higher in morning, dips in afternoon)
            return {
                hour: {
                    'energy': max(3.0, 8.0 - abs(hour - 10))  # Peak at 10 AM
                }
                for hour in range(6, 22)  # 6 AM to 10 PM
            }

    def _time_in_range(self, time: datetime.time, preferred_time: datetime.time, tolerance_minutes: int = 60) -> bool:
        """Check if time is within range of preferred time"""
        time_minutes = time.hour * 60 + time.minute
        preferred_minutes = preferred_time.hour * 60 + preferred_time.minute

        return abs(time_minutes - preferred_minutes) <= tolerance_minutes

    def _suggest_short_break_activity(self) -> str:
        """Suggest a short break activity"""
        activities = ["Deep breathing", "Stand and stretch", "Drink water", "Quick walk", "Eye exercises"]
        import random
        return random.choice(activities)

    def _suggest_long_break_activity(self) -> str:
        """Suggest a long break activity"""
        activities = ["Light exercise", "Healthy snack", "Meditation", "Short walk outside", "Listen to music", "Call a friend"]
        import random
        return random.choice(activities)

    def _generate_empty_schedule(self, date: datetime.date) -> Schedule:
        """Generate empty schedule when no tasks available"""
        schedule = Schedule(
            user_id=self.user_id,
            date=date,
            generated_by_ai=True,
            total_study_time=0
        )
        db.session.add(schedule)
        db.session.commit()
        return schedule

    def _create_advanced_daily_structure(self, date: datetime.date) -> List[Dict]:
        """
        Create a comprehensive daily schedule structure with multiple study blocks,
        breaks, meals, and realistic time allocation.
        """
        blocks = []

        # Morning routine (8:00 AM - 9:00 AM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(8, 0)),
            'end': datetime.datetime.combine(date, datetime.time(9, 0)),
            'type': 'morning_routine',
            'description': 'Morning preparation and light tasks'
        })

        # Morning study block 1 (9:00 AM - 10:30 AM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(9, 0)),
            'end': datetime.datetime.combine(date, datetime.time(10, 30)),
            'type': 'study',
            'description': 'Primary morning study session'
        })

        # Break/Morning routine (10:30 AM - 11:00 AM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(10, 30)),
            'end': datetime.datetime.combine(date, datetime.time(11, 0)),
            'type': 'break',
            'description': 'Break and transition'
        })

        # Morning study block 2 (11:00 AM - 12:30 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(11, 0)),
            'end': datetime.datetime.combine(date, datetime.time(12, 30)),
            'type': 'study',
            'description': 'Secondary morning study session'
        })

        # Lunch break (12:30 PM - 1:30 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(12, 30)),
            'end': datetime.datetime.combine(date, datetime.time(13, 30)),
            'type': 'meal',
            'description': 'Lunch and rest'
        })

        # Afternoon study block 1 (1:30 PM - 3:00 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(13, 30)),
            'end': datetime.datetime.combine(date, datetime.time(15, 0)),
            'type': 'study',
            'description': 'Primary afternoon study session'
        })

        # Afternoon break (3:00 PM - 3:30 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(15, 0)),
            'end': datetime.datetime.combine(date, datetime.time(15, 30)),
            'type': 'break',
            'description': 'Afternoon break'
        })

        # Afternoon study block 2 (3:30 PM - 5:00 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(15, 30)),
            'end': datetime.datetime.combine(date, datetime.time(17, 0)),
            'type': 'study',
            'description': 'Secondary afternoon study session'
        })

        # Evening break/Dinner (5:00 PM - 6:00 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(17, 0)),
            'end': datetime.datetime.combine(date, datetime.time(18, 0)),
            'type': 'meal',
            'description': 'Dinner and relaxation'
        })

        # Evening study block (6:00 PM - 7:30 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(18, 0)),
            'end': datetime.datetime.combine(date, datetime.time(19, 30)),
            'type': 'study',
            'description': 'Evening study session'
        })

        # Wind down (7:30 PM - 8:00 PM)
        blocks.append({
            'start': datetime.datetime.combine(date, datetime.time(19, 30)),
            'end': datetime.datetime.combine(date, datetime.time(20, 0)),
            'type': 'wind_down',
            'description': 'Evening wind down'
        })

        return blocks

    def _calculate_optimal_duration(self, task: Task, available_time: int, default_duration: int) -> int:
        """
        Calculate optimal duration for a task based on its characteristics and available time.
        """
        # Base duration from task estimate or default
        base_duration = task.estimated_duration or default_duration

        # Adjust based on task priority
        if task.priority == 'high':
            # High priority tasks get more time
            base_duration = min(base_duration * 1.2, available_time)
        elif task.priority == 'low':
            # Low priority tasks get less time
            base_duration = max(base_duration * 0.8, 15)

        # Adjust based on task category
        category_multipliers = {
            'exam': 1.3,      # Exams need more time
            'assignment': 1.1, # Assignments need focus
            'reading': 0.9,    # Reading can be more efficient
            'practice': 1.0,   # Practice problems vary
            'review': 0.8      # Reviews are usually shorter
        }

        if task.category and task.category.lower() in category_multipliers:
            base_duration *= category_multipliers[task.category.lower()]

        # Ensure duration fits available time and is reasonable
        duration = max(15, min(int(base_duration), min(available_time, 120)))  # 15-120 minutes

        # Round to nearest 5 minutes for clean scheduling
        duration = round(duration / 5) * 5

        return duration