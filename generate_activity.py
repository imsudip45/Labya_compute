#!/usr/bin/env python3
"""
Autonomous Git Activity Generator
Generates backdated Git commits for the past 365 days with random professional messages
to populate the contributor's history graph locally.
"""

import os
import random
import subprocess
from datetime import datetime, timedelta

# User configurations
GIT_USERNAME = "imsudip45"
GIT_EMAIL = "sudipniroula5@gmail.com"

COMMIT_MESSAGES = [
    "refactor: optimize database connection pool size",
    "docs: update API endpoints and request parameters documentation",
    "feat: implement rate limiting controls on authentication routes",
    "style: format code structure and clean up unused variables",
    "test: add unit tests for user profile wallet balance modifications",
    "fix: resolve race conditions on simultaneous reverse SSH port requests",
    "perf: optimize memory consumption on container metrics aggregation",
    "chore: update dependencies and patch security alerts",
    "refactor: abstract session billing queries into reusable modules",
    "docs: update setup and container deployment instructions",
    "feat: add validation rules to GPU registration payload schemas",
    "fix: resolve connection timeout on host heartbeat status checks",
    "perf: improve response times of available GPUs marketplace",
    "style: adjust margins and responsive cards in landing page grid",
    "test: add mock integration tests for host agent GUI polling loop"
]

def run_command(cmd, env=None):
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)

def main():
    print(f"Configuring local Git credentials to: {GIT_USERNAME} <{GIT_EMAIL}>...", flush=True)
    # Set local repository credentials
    run_command(f'git config --local user.name "{GIT_USERNAME}"')
    run_command(f'git config --local user.email "{GIT_EMAIL}"')
    
    activity_file = "activity.txt"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"Generating activity from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...", flush=True)
    
    current_date = start_date
    total_commits = 0
    
    while current_date <= end_date:
        # Determine day type (weekday vs weekend)
        is_weekend = current_date.weekday() >= 5
        
        # Decide if we make commits on this day
        # Weekdays have 65% chance of activity; weekends have 15%
        probability = 0.15 if is_weekend else 0.65
        
        if random.random() < probability:
            # Decide how many commits (1 to 4 commits)
            num_commits = random.randint(1, 4)
            for _ in range(num_commits):
                # Generate random hour (9am to 6pm)
                hour = random.randint(9, 18)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                commit_time = current_date.replace(hour=hour, minute=minute, second=second)
                date_str = commit_time.isoformat()
                
                # Append a line to the activity file to create a file change
                with open(activity_file, "a") as f:
                    f.write(f"Contribution logged at: {date_str}\n")
                
                # Stage the file
                run_command(f"git add {activity_file}")
                
                # Commit using backdated environment variables
                msg = random.choice(COMMIT_MESSAGES)
                env = os.environ.copy()
                env["GIT_AUTHOR_DATE"] = date_str
                env["GIT_COMMITTER_DATE"] = date_str
                
                # Run git commit with custom env variables
                run_command(f'git commit -m "{msg}"', env=env)
                total_commits += 1
                
        current_date += timedelta(days=1)
        
    print(f"[SUCCESS] Generation finished. Created {total_commits} backdated commits in local git history!", flush=True)

if __name__ == "__main__":
    main()
