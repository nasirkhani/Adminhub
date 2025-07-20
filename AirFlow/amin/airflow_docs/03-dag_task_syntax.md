# Airflow DAG & Tasks Syntax Guide

## 1. Basic DAG Definition

### Method 1: Using `with` Statement (Recommended)
```python
from datetime import datetime, timedelta
from airflow import DAG

with DAG(
    dag_id='my_workflow',                    # DAG name (required)
    description='My first workflow',         # Description
    schedule_interval='@daily',              # When to run
    start_date=datetime(2025, 1, 1),        # First run date
    catchup=False,                          # Don't run past dates
    tags=['example', 'tutorial']            # DAG tags
) as dag:
    
    # Tasks go here
    pass
```

### Method 2: Creating DAG Object
```python
dag = DAG(
    dag_id='my_workflow',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1)
)

# Tasks reference this dag object
```

## 2. Essential DAG Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `dag_id` | Unique DAG name | `'file_processing'` |
| `schedule_interval` | How often to run | `'@daily'`, `'@hourly'`, `'0 9 * * *'` |
| `start_date` | When DAG starts | `datetime(2025, 1, 1)` |
| `catchup` | Run missed dates | `False` (recommended) |
| `default_args` | Default task settings | `{'retries': 1}` |

## 3. Schedule Interval Options

```python
# Presets
schedule_interval='@once'        # Run once
schedule_interval='@hourly'      # Every hour
schedule_interval='@daily'       # Every day at midnight
schedule_interval='@weekly'      # Every Sunday
schedule_interval='@monthly'     # First day of month

# Cron expressions
schedule_interval='0 9 * * *'    # Daily at 9 AM
schedule_interval='0 */2 * * *'  # Every 2 hours
schedule_interval='0 9 * * 1-5'  # Weekdays at 9 AM

# Manual only
schedule_interval=None           # No automatic runs
```

## 4. Default Arguments

```python
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='my_dag',
    default_args=default_args,  # Apply to all tasks
    # ...
) as dag:
```

## 5. Task Definition Syntax

### Python Tasks
```python
from airflow.operators.python import PythonOperator

def my_function():
    return "Hello World"

task1 = PythonOperator(
    task_id='python_task',           # Task name (required)
    python_callable=my_function,     # Function to run (required)
    dag=dag                         # Which DAG (if not using 'with')
)
```

### Bash Tasks
```python
from airflow.operators.bash import BashOperator

task2 = BashOperator(
    task_id='bash_task',
    bash_command='echo "Hello from bash"',
    dag=dag
)
```

### SSH Tasks
```python
from airflow.providers.ssh.operators.ssh import SSHOperator

task3 = SSHOperator(
    task_id='ssh_task',
    ssh_conn_id='my_server',         # Connection ID
    command='ls -la /home',
    dag=dag
)
```

## 6. Complete DAG Template

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Default settings for all tasks
default_args = {
    'owner': 'data_team',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# DAG definition
with DAG(
    dag_id='complete_example',
    description='Complete DAG example',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['example']
) as dag:
    
    # Task functions
    def extract_data():
        return ['file1.txt', 'file2.txt']
    
    def process_data(**context):
        files = context['task_instance'].xcom_pull(task_ids='extract')
        return f"Processed {len(files)} files"
    
    # Task definitions
    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract_data
    )
    
    process_task = PythonOperator(
        task_id='process',
        python_callable=process_data
    )
    
    cleanup_task = BashOperator(
        task_id='cleanup',
        bash_command='echo "Cleanup completed"'
    )
    
    # Task dependencies
    extract_task >> process_task >> cleanup_task
```

## 7. Task Dependencies Syntax

```python
# Method 1: >> operator (most common)
task1 >> task2 >> task3

# Method 2: << operator  
task3 << task2 << task1

# Method 3: Multiple dependencies
task1 >> [task2, task3]  # task1 runs before task2 AND task3
[task2, task3] >> task4  # task2 AND task3 run before task4

# Method 4: set_downstream/upstream
task1.set_downstream(task2)
task2.set_upstream(task1)
```

## 8. TaskFlow API (Modern Syntax)

```python
from airflow.decorators import dag, task

@dag(
    dag_id='taskflow_example',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False
)
def my_taskflow_dag():
    
    @task
    def extract():
        return ['file1.txt', 'file2.txt']
    
    @task  
    def process(files):
        return f"Processed {len(files)} files"
    
    # Task flow
    files = extract()
    result = process(files)

# Create DAG instance
dag_instance = my_taskflow_dag()
```

## 9. Common Task Parameters

```python
task = PythonOperator(
    task_id='my_task',              # Required: unique task name
    python_callable=my_function,    # Required: function to run
    retries=3,                      # Override default retries
    retry_delay=timedelta(minutes=10), # Override retry delay
    depends_on_past=False,          # Don't wait for previous runs
    email=['admin@company.com'],    # Email on failure
    pool='my_pool',                 # Resource pool
    priority_weight=5,              # Task priority
    trigger_rule='all_success'      # When to run (default)
)
```

## 10. File Structure Best Practice

```python
# my_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# 1. Import functions (can be from separate files)
from my_functions import extract_data, process_data

# 2. Default arguments
default_args = {'owner': 'team', 'retries': 1}

# 3. DAG definition
with DAG(
    dag_id='my_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:
    
    # 4. Task definitions
    extract = PythonOperator(task_id='extract', python_callable=extract_data)
    process = PythonOperator(task_id='process', python_callable=process_data)
    
    # 5. Dependencies
    extract >> process
```
