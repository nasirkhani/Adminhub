# celery_targeted_dag.py

# If you prefer using your Celery setup, you can assign specific tasks to specific workers:

# Start workers on different machines with specific queue names:

# bash# On machine 1
# airflow celery worker -q machine1_queue

# # On machine 2
# airflow celery worker -q machine2_queue


from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import socket

def get_hostname():
    """Function that returns the current hostname"""
    hostname = socket.gethostname()
    print(f"Task executed on worker: {hostname}")
    return hostname

with DAG(
    'celery_targeted_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Target specific Celery workers',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # This task should run on machine 1
    task_for_machine1 = PythonOperator(
        task_id='task_for_machine1',
        python_callable=get_hostname,
        queue='machine1_queue',  # Specific queue for machine 1
    )
    
    # This task should run on machine 2
    task_for_machine2 = PythonOperator(
        task_id='task_for_machine2',
        python_callable=get_hostname,
        queue='machine2_queue',  # Specific queue for machine 2
    )
    
    # Set dependencies (these will run in parallel)
    task_for_machine1 >> task_for_machine2
