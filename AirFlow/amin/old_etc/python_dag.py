# python_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Simple function for our first task
def say_hello():
    print("Hello from Python operator!")
    return "Task completed successfully"

# Function that handles data processing with Airflow context
def process_data(**context):
    # Get execution date from context
    execution_date = context['logical_date']
    print(f"Processing data for {execution_date}")
    
    # Simulate data processing
    data = {'processed_records': 100, 'success': True}
    
    # Store results in XCom for next task
    task_instance = context['task_instance']
    task_instance.xcom_push(key='results', value=data)
    
    return "Data processing completed"

# Function that retrieves and uses results from previous task
def check_results(**context):
    # Get results from previous task
    task_instance = context['task_instance']
    results = task_instance.xcom_pull(task_ids='process_data_task', key='results')
    
    print(f"Retrieved results: {results}")
    print(f"Processed {results['processed_records']} records")
    
    # Check success status
    if results['success']:
        print("Data processing was successful!")
    else:
        print("Data processing failed!")
    
    return f"Checked {results['processed_records']} records"

# DAG definition
with DAG(
    'python_functions_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='DAG using Python functions',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task 1: Simple hello function
    hello_task = PythonOperator(
        task_id='hello_task',
        python_callable=say_hello,
    )

    # Task 2: Process data and store results
    process_data_task = PythonOperator(
        task_id='process_data_task',
        python_callable=process_data,
        provide_context=True,
    )

    # Task 3: Check results from previous task
    check_results_task = PythonOperator(
        task_id='check_results_task',
        python_callable=check_results,
        provide_context=True,
    )

    # Set task dependencies (order of execution)
    hello_task >> process_data_task >> check_results_task
