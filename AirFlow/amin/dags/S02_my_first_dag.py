# my_first_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Define default arguments for the DAG
default_args = {
    'owner': 'your_name',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
with DAG(
    'S02_my_first_dag',
    default_args=default_args,
    description='My first Airflow DAG',
    schedule_interval=timedelta(days=1),  # Run daily
    start_date=datetime(2024, 5, 1),  # Start date (won't run for dates before this)
    catchup=False,  # Don't run for past dates
) as dag:

    # Define three tasks using BashOperator
    task1 = BashOperator(
        task_id='print_date',
        bash_command='date',
    )

    task2 = BashOperator(
        task_id='print_hello',
        bash_command='echo "Hello, Airflow!"',
    )

    task3 = BashOperator(
        task_id='list_files',
        bash_command='ls -la',   # or 'cd /home/rocky/airflow && ls -la'
        cwd='/home/rocky/airflow',  # Run in this directory
    )


    # Set task dependencies (task1 → task2 → task3)
    # This means: run task1 first, then task2, then task3
    task1 >> task2 >> task3
