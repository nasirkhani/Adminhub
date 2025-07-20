# remote_execution_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.bash import BashOperator

with DAG(
    'S05_01_remote_execution_dag',
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
