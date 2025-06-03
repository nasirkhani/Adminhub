# ftp_file_processing_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko
import os

# Configuration
VM2_HOST = '192.168.83.132'    # FTP server (source)
VM3_HOST = '192.168.83.133'    # Processing server (destination)
USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'
FTP_PASSWORD = '111'

def run_ssh_command(host, command):
    """Execute a command on a remote host via SSH"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname=host, username=USERNAME, key_filename=SSH_KEY)
        stdin, stdout, stderr = ssh.exec_command(command)
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            raise Exception(f"Command failed with exit code {exit_code}: {error}")
        
        return output
    
    except Exception as e:
        raise Exception(f"SSH connection or command execution failed: {e}")
    
    finally:
        ssh.close()

def discover_files_on_ftp(**context):
    """Discover all .txt files in /in/ directories on VM2"""
    find_command = f"find /home/{USERNAME} -name '*.txt' -path '*/in/*' -type f"
    
    try:
        result = run_ssh_command(VM2_HOST, find_command)
        
        if result:
            files = [f.strip() for f in result.split('\n') if f.strip()]
            return files
        else:
            return []
    
    except Exception as e:
        raise Exception(f"File discovery failed: {e}")

def transfer_files_via_ftp(**context):
    """Transfer files from VM2 to VM3 using FTP protocol"""
    files = context['task_instance'].xcom_pull(task_ids='discover_files')
    
    if not files:
        return
    
    for source_file_path in files:
        filename = os.path.basename(source_file_path)
        relative_path = source_file_path.replace(f'/home/{USERNAME}/', '').replace(f'/{filename}', '')
        destination_path = f'/home/{USERNAME}/{relative_path}'
        destination_file = f'{destination_path}/{filename}'
        
        # Create destination directory on VM3
        create_dir_command = f"mkdir -p {destination_path}"
        run_ssh_command(VM3_HOST, create_dir_command)
        
        # Use lftp to download file from VM2 to VM3
        ftp_command = f'''lftp -u {USERNAME},{FTP_PASSWORD} {VM2_HOST} -e "get {source_file_path} -o {destination_file}; quit"'''
        run_ssh_command(VM3_HOST, ftp_command)
        
        # Verify file was transferred
        run_ssh_command(VM3_HOST, f"ls -la {destination_file}")

def process_files_on_vm3(**context):
    """Process transferred files using Python script on VM3"""
    files = context['task_instance'].xcom_pull(task_ids='discover_files')
    
    if not files:
        raise Exception("No files to process")
    
    for original_file_path in files:
        vm3_file_path = original_file_path  # Same path on VM3
        process_command = f"python3 /home/{USERNAME}/scripts/simple_file_manager.py {vm3_file_path}"
        run_ssh_command(VM3_HOST, process_command)

# DAG Definition
with DAG(
    'ftp_file_processing_workflow',
    default_args={
        'owner': 'rocky',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'email_on_failure': False,
        'email_on_retry': False,
    },
    description='File processing workflow using FTP transfer from VM2 to VM3',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 1),
    catchup=False,
    tags=['ftp', 'file-processing', 'multi-vm'],
) as dag:
    
    # Task 1: Discover files on FTP server (VM2)
    discover_task = PythonOperator(
        task_id='discover_files',
        python_callable=discover_files_on_ftp,
    )
    
    # Task 2: Transfer files via FTP from VM2 to VM3
    transfer_task = PythonOperator(
        task_id='transfer_files',
        python_callable=transfer_files_via_ftp,
        provide_context=True,
    )
    
    # Task 3: Process files on VM3
    process_task = PythonOperator(
        task_id='process_files',
        python_callable=process_files_on_vm3,
        provide_context=True,
    )
    
    # Define task dependencies
    discover_task >> transfer_task >> process_task
