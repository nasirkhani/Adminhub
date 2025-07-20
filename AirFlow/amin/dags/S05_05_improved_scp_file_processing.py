# simple_file_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko
import os  # FIXED: Added missing import

# Simple configuration
VM2_HOST = '192.168.83.132'
VM3_HOST = '192.168.83.133'  
USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'

def run_ssh_command(host, command):
    """Run command on remote host"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname=host, username=USERNAME, key_filename=SSH_KEY)
        stdin, stdout, stderr = ssh.exec_command(command)
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        
        # CRITICAL: Check exit code to determine success/failure
        if exit_code != 0:
            raise Exception(f"Command failed with exit code {exit_code}: {error}")
        
        return output
    
    except Exception as e:
        raise Exception(f"SSH Error: {e}")  # Re-raise to fail the task
    
    finally:
        ssh.close()

def find_files(**context):
    """Find txt files on VM2"""
    command = f"find /home/{USERNAME} -name '*.txt' -path '*/in/*'"
    
    try:
        result = run_ssh_command(VM2_HOST, command)
        
        if result:
            files = result.split('\n')
            files = [f.strip() for f in files if f.strip()]  # Clean empty lines
            print(f"Found {len(files)} files: {files}")
            return files
        else:
            print("No files found")
            return []
    
    except Exception as e:
        print(f"FAILED to find files: {e}")
        raise  # Re-raise to fail the task

def copy_and_process(**context):
    """Copy files from VM2 to VM3 and process them"""
    # Get file list from previous task
    files = context['task_instance'].xcom_pull(task_ids='find_files')
    
    if not files:
        raise Exception("No files to process - this should not happen")
    
    success_count = 0
    total_files = len(files)
    
    for file_path in files:
        print(f"Processing: {file_path}")
        
        try:
            # Step 1: Copy file from VM2 to VM3
            copy_cmd = f"scp -i {SSH_KEY} {USERNAME}@{VM2_HOST}:{file_path} {USERNAME}@{VM3_HOST}:{file_path}"
            copy_result = os.system(copy_cmd)
            
            if copy_result != 0:
                raise Exception(f"SCP failed with exit code {copy_result}")
            
            print(f"File copied successfully: {file_path}")
            
            # Step 2: Process file on VM3
            process_cmd = f"python3 /home/{USERNAME}/scripts/simple_file_manager.py {file_path}"
            process_result = run_ssh_command(VM3_HOST, process_cmd)
            
            print(f"Processing completed: {process_result}")
            success_count += 1
            
        except Exception as e:
            print(f"FAILED processing {file_path}: {e}")
            # CRITICAL: Raise exception to fail the entire task
            raise Exception(f"File processing failed for {file_path}: {e}")
    
    print(f"Successfully processed {success_count}/{total_files} files")

# Simple DAG
with DAG(
    'S05_05_improved_scp_file_processing',
    default_args={
        'owner': 'rocky',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Simple file processing workflow',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    find_task = PythonOperator(
        task_id='find_files',
        python_callable=find_files,
    )

    process_task = PythonOperator(
        task_id='copy_and_process',
        python_callable=copy_and_process,
        provide_context=True,
    )

    find_task >> process_task
