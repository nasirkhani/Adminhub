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


# Session 5: Running Tasks on Remote Machines

Now that you understand how to execute local scripts, let's move to running tasks on remote machines - exactly what you need for your requirements.

## Approach 1: SSHOperator - Direct Execution on Remote Servers

The SSH Operator allows you to run commands directly on remote servers using SSH. This is ideal for executing scripts on specific machines.

First, install the SSH provider if you haven't already:

```bash
pip install apache-airflow-providers-ssh
```

### Step 1: Configure an SSH Connection in Airflow

1. Go to the Airflow UI → Admin → Connections
2. Click "+" to add a new connection
3. Fill in the details:
   - **Connection Id**: `ssh_default` (or any name you prefer)
   - **Connection Type**: `SSH`
   - **Host**: Your remote server hostname or IP (e.g., `192.168.1.100`)
   - **Username**: SSH username
   - **Password**: SSH password (or use Private Key instead)
   - **Port**: 22 (or your custom SSH port)
   - **Extra**: You can add extra options if needed

### Step 2: Create a DAG with SSHOperator

```python
# remote_execution_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.bash import BashOperator

with DAG(
    'remote_execution_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Execute commands on remote servers',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task 1: Check disk space on remote server
    # Uses SSHOperator to run a command remotely
    check_disk = SSHOperator(
        task_id='check_disk_space',
        ssh_conn_id='ssh_default',  # Uses the connection we created
        command='df -h',  # Command to run on remote server
    )
    
    # Task 2: Run a Python script on remote server
    # Assumes the script exists on the remote server
    run_remote_script = SSHOperator(
        task_id='run_remote_script',
        ssh_conn_id='ssh_default',
        command='python3 /path/to/script.py',  # Path on remote server
    )
    
    # Task 3: Local task to confirm remote execution
    # This runs on the Airflow server, not the remote machine
    confirm = BashOperator(
        task_id='confirm_execution',
        bash_command='echo "Remote tasks completed successfully"',
    )
    
    # Set dependencies - run check_disk first, then the script, then confirm
    check_disk >> run_remote_script >> confirm
```

### Step 3: Prepare a Script on the Remote Server

On your remote server, create a sample script:

```bash
# SSH into your remote server and run:
mkdir -p /tmp/airflow_scripts
nano /tmp/airflow_scripts/remote_script.py
```

Add this content:

```python
# remote_script.py on remote server
import socket
import datetime
import os

# Get information about the remote environment
hostname = socket.gethostname()
current_time = datetime.datetime.now()
user = os.getenv('USER')

# Write results to a file
with open('/tmp/remote_execution_result.txt', 'w') as f:
    f.write(f"Script executed on host: {hostname}\n")
    f.write(f"Execution time: {current_time}\n")
    f.write(f"Executing user: {user}\n")

print(f"Script executed successfully on {hostname} at {current_time}")
print(f"Results saved to /tmp/remote_execution_result.txt")
```

### Step 4: Update Your DAG to Use the Correct Path

Update the `run_remote_script` task in your DAG:

```python
run_remote_script = SSHOperator(
    task_id='run_remote_script',
    ssh_conn_id='ssh_default',
    command='python3 /tmp/airflow_scripts/remote_script.py',  # Updated path
)
```

## Approach 2: Using Your Existing Celery Setup

Since you mentioned you've already set up Celery, you can distribute tasks to different worker nodes.

### Step 1: Verify Your Celery Setup

Make sure your `airflow.cfg` has:

```ini
executor = CeleryExecutor
broker_url = your_rabbitmq_connection_string
result_backend = your_database_connection_string
```

And that you have Celery workers running on your target machines.

### Step 2: Create a DAG Without Special Operators

With Celery, you don't need special operators - tasks are automatically distributed to workers:

```python
# celery_distributed_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import socket  # For getting the hostname

def get_hostname():
    """Function that returns the current hostname - will run on a worker"""
    hostname = socket.gethostname()
    print(f"Task executed on worker: {hostname}")
    return hostname

with DAG(
    'celery_distributed_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Distribute tasks across Celery workers',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task 1: Get hostname of the worker executing the task
    get_worker_hostname = PythonOperator(
        task_id='get_worker_hostname',
        python_callable=get_hostname,
    )
    
    # Task 2: Run a shell command on whichever worker gets assigned
    run_command = BashOperator(
        task_id='run_shell_command',
        bash_command='echo "Running on host: $(hostname)"',
    )
    
    # Set dependencies
    get_worker_hostname >> run_command
```

### Step 3: Use Queues to Target Specific Workers

You can target specific workers by assigning tasks to specific queues:

```python
# Inside your DAG
task_for_specific_worker = BashOperator(
    task_id='task_for_specific_worker',
    bash_command='echo "This task should run on a specific worker"',
    queue='worker_1_queue',  # Specific queue name
)
```

On the worker machine, start the worker with this queue:

```bash
airflow celery worker -q worker_1_queue
```

## Which Approach to Choose?

1. **Use SSHOperator when:** 
   - You need to execute tasks on specific servers
   - You don't want to install Airflow on remote machines
   - You need to execute different commands on different hosts

2. **Use Celery when:**
   - You want automatic load balancing across workers
   - You have Airflow installed on all worker machines
   - You want centralized management of distributed execution

## Mini Exercise

1. Choose one approach (SSHOperator is simpler to start with)
2. Create the DAG file and necessary remote scripts
3. Run the DAG and check the logs to confirm it executed on the remote server

Once you've tried this, we can move on to more complex scenarios and monitoring. Let me know if you have any questions or run into issues!
