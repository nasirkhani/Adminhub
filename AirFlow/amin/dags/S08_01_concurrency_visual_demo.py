# concurrent_demo_dag.py
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import time
import random

@dag(
    dag_id='S08_01_concurrency_visual_demo',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_tasks=10,  # DAG-level concurrency limit
    default_args={'owner': 'rocky'}
)
def concurrency_demo():
    
    @task(queue='high_priority')
    def simulate_quick_task(task_num):
        """Simulates a quick task (5-10 seconds)"""
        start = datetime.now()
        duration = random.randint(5, 10)
        time.sleep(duration)
        end = datetime.now()
        
        return {
            'task': f'quick_{task_num}',
            'start': start.isoformat(),
            'end': end.isoformat(),
            'duration': duration,
            'queue': 'high_priority'
        }
    
    @task(queue='default')
    def simulate_slow_task(task_num):
        """Simulates a slow task (20-30 seconds)"""
        start = datetime.now()
        duration = random.randint(20, 30)
        time.sleep(duration)
        end = datetime.now()
        
        return {
            'task': f'slow_{task_num}',
            'start': start.isoformat(),
            'end': end.isoformat(),
            'duration': duration,
            'queue': 'default'
        }
    
    @task
    def analyze_concurrency(results):
        """Shows how tasks ran concurrently"""
        print("\n=== CONCURRENCY ANALYSIS ===")
        print(f"Total tasks: {len(results)}")
        
        # Sort by start time
        sorted_results = sorted(results, key=lambda x: x['start'])
        
        # Find overlapping tasks
        overlaps = 0
        for i in range(len(sorted_results)):
            for j in range(i+1, len(sorted_results)):
                task1_end = sorted_results[i]['end']
                task2_start = sorted_results[j]['start']
                if task2_start < task1_end:
                    overlaps += 1
                    print(f"CONCURRENT: {sorted_results[i]['task']} and {sorted_results[j]['task']}")
        
        print(f"\nTotal concurrent executions: {overlaps}")
        
        # Timeline visualization
        print("\n=== EXECUTION TIMELINE ===")
        for r in sorted_results:
            print(f"{r['task']:12} [{r['start'][11:19]}] --> [{r['end'][11:19]}] ({r['duration']}s) Queue: {r['queue']}")
        
        return "Analysis complete"
    
    # Create 5 quick tasks and 3 slow tasks
    quick_results = []
    slow_results = []
    
    for i in range(5):
        quick_results.append(simulate_quick_task(i))
    
    for i in range(3):
        slow_results.append(simulate_slow_task(i))
    
    # All tasks will start at once (up to concurrency limit)
    all_results = quick_results + slow_results
    
    # Analyze how they ran
    analyze_concurrency(all_results)

dag = concurrency_demo()
