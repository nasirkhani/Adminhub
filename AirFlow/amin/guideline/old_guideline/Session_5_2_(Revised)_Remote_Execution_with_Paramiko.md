# Session 5 (Revised): Remote Execution with Paramiko

I see you're encountering dependency conflicts. Let's use an alternative approach that avoids these issues: using the PythonOperator with Paramiko for SSH operations.

## Step 1: Install Paramiko

Paramiko is a Python implementation of the SSHv2 protocol that doesn't have the same complex dependencies as the Airflow SSH provider:

```bash
pip install paramiko
```

## Step 2: Create a DAG Using Paramiko for SSH

```python
# paramiko_ssh_dag.py
from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# Import paramiko for SSH functionality
import paramiko
import io

# Function to execute commands over SSH using Paramiko
def execute_ssh_command(remote_host, username, key_path, command, **context):
    """
    Execute a command on a remote server via SSH using Paramiko
    """
    # Initialize SSH client
    ssh_client = paramiko.SSHClient()
    
    # Auto-add host keys (similar to accepting fingerprints manually)
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the remote server using key-based authentication
        ssh_client.connect(
            hostname=remote_host,
            username=username,
            key_filename=key_path
        )
        
        print(f"Connected to {remote_host} successfully")
        print(f"Executing command: {command}")
        
        # Execute the command
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Read the outputs
        stdout_str = stdout.read().decode('utf-8')
        stderr_str = stderr.read().decode('utf-8')
        
        # Check the exit status
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("Command executed successfully")
            print(f"Output:\n{stdout_str}")
        else:
            print(f"Command failed with exit status {exit_status}")
            print(f"Error:\n{stderr_str}")
            raise Exception(f"Command failed with exit status {exit_status}: {stderr_str}")
        
        return stdout_str
    
    finally:
        # Always close the connection
        ssh_client.close()
        print("SSH connection closed")

# Function to create a Python script on the remote server
def create_remote_script(remote_host, username, key_path, **context):
    # Script content as a Python string
    script_content = '''
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
'''

    # Commands to create directory and script
    commands = [
        'mkdir -p /tmp/airflow_scripts',
        f'cat > /tmp/airflow_scripts/remote_script.py << EOF\n{script_content}\nEOF'
    ]
    
    # Join commands with &&
    full_command = ' && '.join(commands)
    
    # Execute the command
    return execute_ssh_command(remote_host, username, key_path, full_command, **context)

# Function to run the Python script on the remote server
def run_remote_script(remote_host, username, key_path, **context):
    command = 'python3 /tmp/airflow_scripts/remote_script.py'
    return execute_ssh_command(remote_host, username, key_path, command, **context)

# Function to verify the script output
def verify_script_output(remote_host, username, key_path, **context):
    command = 'cat /tmp/remote_execution_result.txt'
    return execute_ssh_command(remote_host, username, key_path, command, **context)

# DAG definition
with DAG(
    'paramiko_ssh_dag',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Execute commands on remote servers using Paramiko',
    schedule_interval='@daily',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:
    
    # Define remote connection parameters
    # For security, these could be stored in Airflow Variables or Connections
    REMOTE_HOST = "your_remote_host"  # Replace with your remote host
    USERNAME = "your_username"        # Replace with your SSH username
    KEY_PATH = "/path/to/ssh/key"     # Replace with path to your private key
    
    # Task 1: Check system info
    check_system = PythonOperator(
        task_id='check_system_info',
        python_callable=execute_ssh_command,
        op_kwargs={
            'remote_host': REMOTE_HOST,
            'username': USERNAME,
            'key_path': KEY_PATH,
            'command': 'hostname && uptime && df -h',
        },
    )
    
    # Task 2: Create remote script
    setup_remote = PythonOperator(
        task_id='setup_remote_environment',
        python_callable=create_remote_script,
        op_kwargs={
            'remote_host': REMOTE_HOST,
            'username': USERNAME,
            'key_path': KEY_PATH,
        },
    )
    
    # Task 3: Run remote script
    run_script = PythonOperator(
        task_id='run_remote_script',
        python_callable=run_remote_script,
        op_kwargs={
            'remote_host': REMOTE_HOST,
            'username': USERNAME,
            'key_path': KEY_PATH,
        },
    )
    
    # Task 4: Verify output
    verify_output = PythonOperator(
        task_id='verify_script_output',
        python_callable=verify_script_output,
        op_kwargs={
            'remote_host': REMOTE_HOST,
            'username': USERNAME,
            'key_path': KEY_PATH,
        },
    )
    
    # Set dependencies
    check_system >> setup_remote >> run_script >> verify_output
```

## Detailed Explanation

The approach above uses Paramiko to handle SSH connections instead of relying on Airflow's SSHOperator. Here's what's happening:

1. **SSH Connection Function**: The `execute_ssh_command` function handles:
   - Establishing an SSH connection using key-based authentication
   - Executing commands on the remote server
   - Capturing stdout/stderr output
   - Checking exit codes
   - Properly closing connections

2. **Task Functions**:
   - `create_remote_script`: Creates a directory and Python script on the remote server
   - `run_remote_script`: Executes the Python script
   - `verify_script_output`: Checks the output file created by the script

3. **Security Practices**:
   - Uses key-based authentication (more secure than passwords)
   - Connection parameters could be stored in Airflow Variables or Connections (better than hardcoding)

## Using Airflow Variables for Sensitive Information

For better security, you can store connection parameters in Airflow Variables:

1. In the Airflow UI, go to Admin → Variables
2. Add variables:
   - `remote_host`: Your remote server hostname/IP
   - `remote_username`: SSH username
   - `remote_key_path`: Path to your SSH private key

Then update your DAG:

```python
# Replace hardcoded values with Variables
from airflow.models import Variable

REMOTE_HOST = Variable.get("remote_host")
USERNAME = Variable.get("remote_username")
KEY_PATH = Variable.get("remote_key_path")
```

## Mini Exercise

1. Install Paramiko: `pip install paramiko`
2. Create the DAG file with your specific connection parameters
3. Run the DAG and check the logs to see if commands execute successfully on the remote server

Let me know if you encounter any issues with this approach or need help implementing secure credential management!
