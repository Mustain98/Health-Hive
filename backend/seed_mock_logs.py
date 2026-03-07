import os
import sys
from datetime import datetime, timedelta, timezone, date
from sqlmodel import select, Session

# Setup python path to include backend app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import engine
from app.models.user import User  # important for FK resolution
from app.models.user_goal import UserGoal, GoalType
from app.models.user_data import UserGoalLog

def generate_mock_logs():
    print("Starting log generation...")
    # Find all active goals
    with Session(engine) as session:
        # 1. Clear ALL existing logs to start fresh
        print("Deleting all existing UserGoalLogs...")
        existing_logs = session.exec(select(UserGoalLog)).all()
        for el in existing_logs:
            session.delete(el)
        session.commit()
    
        active_goals = session.exec(select(UserGoal).where(UserGoal.active == True)).all()
        
        if not active_goals:
            print("No active goals found.")
            return

        for goal in active_goals:
            if goal.initial_weight is None or goal.target_weight is None:
                print(f"Skipping goal {goal.id} - missing weights")
                continue

            start_date_ref = goal.start_date or date.today()
            start_dt = datetime.combine(start_date_ref, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            print(f"Generating logs for user {goal.created_for}, goal {goal.id}")
            
            base_weight = goal.initial_weight
            target = goal.target_weight
            total_delta = target - base_weight  # Negative for lose, positive for gain
            days = goal.duration_days or 30
            
            # Create an initial log for Day 0
            session.add(UserGoalLog(
                user_id=goal.created_for, goal_id=goal.id, date=start_dt, weight=base_weight, due_terget=0.0
            ))

            # Intervals and realistic fluctuations
            intervals = [4, 9, 14, 18, 22, 28, 30]
            # To simulate ups and downs, the progress percentage won't strictly be linear.
            # Example percentages of progress toward target with some regression:
            # Day 4: 10%
            # Day 9: 35% (Good progress)
            # Day 14: 25% (Slight regression / up)
            # Day 18: 50%
            # Day 22: 45% (Another minor up)
            # Day 28: 85%
            # Day 30: 95%
            progress_factors = [0.10, 0.35, 0.25, 0.50, 0.45, 0.85, 0.95]

            for i, days_passed in enumerate(intervals):
                if days_passed > days:
                    break

                log_dt = start_dt + timedelta(days=days_passed)
                
                # Mock progress
                current_weight = base_weight + (total_delta * progress_factors[i])
                
                # Due target calculation (linear expected progress)
                daily_delta = total_delta / float(days)
                due_target = daily_delta * days_passed  # expected delta at this point in time
                
                new_log = UserGoalLog(
                    user_id=goal.created_for,
                    goal_id=goal.id,
                    date=log_dt,
                    weight=current_weight,
                    due_terget=due_target
                )
                session.add(new_log)
                print(f"Added log Day {days_passed}: Weight={current_weight:.1f}, DueTarget={due_target:.1f}")
            
        session.commit()
        print("Mock logs generated and committed!")

if __name__ == "__main__":
    generate_mock_logs()
