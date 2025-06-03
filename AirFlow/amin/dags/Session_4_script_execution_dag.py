# script_execution_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    'script_execution_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='DAG to execute external Python scripts',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task to run the Python script
    # Note: We specify the full path to the script
    run_script = BashOperator(
        task_id='run_python_script',
        bash_command='python3 /home/rocky/airflow/scripts/sample_script.py',
    )
    
    # Task to verify the script output exists
    check_output = BashOperator(
        task_id='check_script_output',
        bash_command='cat /tmp/airflow_script_output.txt',
    )
    
    # Set dependencies
    run_script >> check_output
