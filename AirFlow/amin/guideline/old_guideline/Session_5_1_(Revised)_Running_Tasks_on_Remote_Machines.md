# Session 5 (Revised): Running Tasks on Remote Machines

You've identified a critical issue - thank you! Version compatibility is extremely important in Airflow. Let's correct our approach.

## SSH Provider Installation with Version Compatibility

First, install the correct version of the SSH provider that works with Airflow 2.9.0:

```bash
pip install apache-airflow-providers-ssh==3.10.3 --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
```

This ensures we get a compatible provider version without upgrading your entire Airflow installation.

## Configuring SSH with Key-Based Authentication (Recommended)

### Step 1: Set Up SSH Keys (if not already done)

On your Airflow server:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "airflow@example.com"

# Copy the key to your remote server
ssh-copy-id username@remote-server
```

### Step 2: Configure an SSH Connection in Airflow

1. Go to Airflow UI → Admin → Connections
2. Click "+" to add a new connection
3. Fill in the details:
   - **Connection Id**: `ssh_remote`
   - **Connection Type**: `SSH`
   - **Host**: Your remote server hostname or IP
   - **Username**: SSH username
   - **Private Key File**: Path to your private key (e.g., `/home/rocky/.ssh/id_ed25519`)
   - **Port**: 22 (or your custom SSH port)

### Step 3: Create a DAG with SSHOperator

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

    # Task 1: Check system info on remote server
    check_system = SSHOperator(
        task_id='check_system_info',
        ssh_conn_id='ssh_remote',  # Uses the SSH connection we created
        command='hostname && uptime && df -h',  # Multiple commands
    )
    
    # Task 2: Create a directory and script on remote server
    setup_remote = SSHOperator(
        task_id='setup_remote_environment',
        ssh_conn_id='ssh_remote',
        # Create directory and script in one command
        command='''
        mkdir -p /tmp/airflow_scripts &&
        cat > /tmp/airflow_scripts/remote_script.py << 'EOL'
import socket
import datetime
import os

# Get information about the remote environment
hostname = socket.gethostname()
current_time = datetime.datetime.now()
user = os.getenv('USER')

# Write results to a file
with open('/tmp/remote_execution_result.txt', 'w') as f:
    f.write(f"Script executed on host: {hostname}\\n")
    f.write(f"Execution time: {current_time}\\n")
    f.write(f"Executing user: {user}\\n")

print(f"Script executed successfully on {hostname} at {current_time}")
print(f"Results saved to /tmp/remote_execution_result.txt")
EOL
        ''',
    )
    
    # Task 3: Run the Python script on remote server
    run_remote_script = SSHOperator(
        task_id='run_remote_script',
        ssh_conn_id='ssh_remote',
        command='python3 /tmp/airflow_scripts/remote_script.py',
    )
    
    # Task 4: Verify the script output on remote server
    verify_output = SSHOperator(
        task_id='verify_script_output',
        ssh_conn_id='ssh_remote',
        command='cat /tmp/remote_execution_result.txt',
    )
    
    # Task 5: Local task to confirm remote execution
    confirm = BashOperator(
        task_id='confirm_execution',
        bash_command='echo "Remote tasks completed successfully"',
    )
    
    # Set dependencies
    check_system >> setup_remote >> run_remote_script >> verify_output >> confirm
```

## Alternative: Using Celery with Worker-Specific Queues

If you prefer using your Celery setup, you can assign specific tasks to specific workers:

1. Start workers on different machines with specific queue names:

```bash
# On machine 1
airflow celery worker -q machine1_queue

# On machine 2
airflow celery worker -q machine2_queue
```

2. Create a DAG that targets specific workers:

```python
# celery_targeted_dag.py
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
```

## Mini Exercise

1. Install the correct SSH provider version
2. Set up SSH key-based authentication between your Airflow server and a remote machine
3. Create the SSH connection in the Airflow UI
4. Create and run the `remote_execution_dag.py` DAG
5. Check the logs to see that the commands executed on the remote server

Let me know if you encounter any other compatibility issues or if you have questions about secure SSH authentication!
