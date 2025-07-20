# Session 4: Executing External Python Scripts

Now that you understand how to run Python functions within Airflow, let's take the next step: executing external Python scripts. This is crucial for your goal of running scripts on remote machines.

## Why Execute External Scripts?

1. **Separation of concerns**: Keep your DAG definition clean and focused on workflow
2. **Code reuse**: Scripts can be used outside of Airflow too
3. **Easier development**: Write and test your scripts separately from Airflow
4. **Resource management**: External scripts can run in different environments/machines

## Method 1: Using BashOperator to Run Python Scripts

Let's create a simple Python script and then execute it with Airflow:

**First**, create a scripts directory in your Airflow home:

```bash
mkdir -p /home/rocky/airflow/scripts
```

**Second**, create a sample script:

```bash
# Create a file at /home/rocky/airflow/scripts/sample_script.py
nano /home/rocky/airflow/scripts/sample_script.py
```

Add this content to the script:

```python
# sample_script.py
import os
import datetime
import random

# Get current information
current_time = datetime.datetime.now()
hostname = os.uname().nodename
user = os.getenv('USER')

# Simulate processing some data
data_points = [random.randint(1, 100) for _ in range(5)]
average = sum(data_points) / len(data_points)

# Print information (will appear in Airflow logs)
print(f"Script executed at: {current_time}")
print(f"Running on host: {hostname}")
print(f"Running as user: {user}")
print(f"Generated data points: {data_points}")
print(f"Average value: {average}")

# Create output file to demonstrate file creation
output_path = '/tmp/airflow_script_output.txt'
with open(output_path, 'w') as f:
    f.write(f"Script executed at: {current_time}\n")
    f.write(f"Running on host: {hostname}\n")
    f.write(f"Average of data: {average}\n")

print(f"Output written to: {output_path}")

# Return success (exit code 0)
exit(0)
```

**Third**, create a DAG to run this script:

```python
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
```

## Method 2: Using PythonOperator with External Code

Another approach is importing external Python functions into your DAG file:

```python
# external_module_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Import function from our script
# This assumes you have an __init__.py file in the scripts directory
import sys
sys.path.append('/home/rocky/airflow/scripts')

# Import the function directly 
# (create this in your scripts directory)
from my_module import process_data_function

with DAG(
    'external_module_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='DAG that imports external Python modules',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task that calls the imported function
    process_task = PythonOperator(
        task_id='process_data',
        python_callable=process_data_function,
        op_kwargs={'param1': 'value1', 'param2': 'value2'},  # Parameters to your function
    )
```

Create the module file:

```python
# /home/rocky/airflow/scripts/my_module.py
def process_data_function(param1, param2):
    """Function that will be imported into our DAG"""
    print(f"Processing data with parameters: {param1}, {param2}")
    
    # Simulate processing
    result = f"Processed {param1} and {param2}"
    
    return result
```

Also create the `__init__.py` file:

```bash
# Create an empty __init__.py file to make the directory a package
touch /home/rocky/airflow/scripts/__init__.py
```

## Passing Parameters to Scripts

You can pass parameters to your scripts in several ways:

### 1. Command-line arguments:

```python
# In DAG:
run_script = BashOperator(
    task_id='run_python_script',
    bash_command='python3 /home/rocky/airflow/scripts/sample_script.py arg1 arg2',
)

# In script:
import sys
args = sys.argv[1:]  # Get command-line arguments
print(f"Received arguments: {args}")
```

### 2. Environment variables:

```python
# In DAG:
run_script = BashOperator(
    task_id='run_python_script',
    bash_command='export MY_PARAM="value" && python3 /home/rocky/airflow/scripts/sample_script.py',
)

# In script:
import os
param = os.getenv('MY_PARAM')
print(f"Received parameter: {param}")
```

### 3. Airflow variables:

```python
# In DAG:
from airflow.models import Variable

# Store a variable in Airflow
Variable.set("my_script_param", "some_value")

# In your script:
from airflow.models import Variable
param = Variable.get("my_script_param")
print(f"Received parameter: {param}")
```

## Mini Exercise

1. Create the `sample_script.py` file and the `script_execution_dag.py` DAG
2. Run the DAG and check the logs for both tasks
3. Verify the output file at `/tmp/airflow_script_output.txt`
4. Modify the script to accept a command-line parameter and pass it from the DAG

When you're done, let me know what you observed in the logs and if the script executed successfully!
