## Fixed Code with Path Mapping and Stricter Checking

### Updated simple_file_manager.py (same as before, no changes needed)

```python
#!/usr/bin/env python3
import sys
import os
import random

def process_text_file(input_file_path):
    try:
        with open(input_file_path, 'r') as f:
            lines = f.readlines()
        
        lines = [line.rstrip('\n') for line in lines]
        random_chars = []
        selected_lines = []
        
        for i, line in enumerate(lines):
            char = random.choice(['v', 'x'])
            random_chars.append(char)
            if char == 'v':
                selected_lines.append(f"Line {i+1}: {line}")
        
        base_name = input_file_path.replace('.txt', '')
        dat_file = f"{base_name}.dat"
        inv_file = f"{base_name}.inv"
        
        with open(dat_file, 'w') as f:
            f.write(''.join(random_chars))
        
        with open(inv_file, 'w') as f:
            for line in selected_lines:
                f.write(line + '\n')
        
        print(f"SUCCESS: Created {dat_file} and {inv_file}")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file) or not input_file.endswith('.txt'):
        exit(1)
    
    success = process_text_file(input_file)
    exit(0 if success else 1)
```

### Updated DAG with Path Mapping

```python
# fixed_ftp_file_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko
import os

# Configuration
VM2_HOST = '192.168.83.132'
VM3_HOST = '192.168.83.133'
VM2_USERNAME = 'rocky'
VM3_USERNAME = 'rocky'  # Can be different now
SSH_KEY = '/home/rocky/.ssh/id_ed25519'
FTP_PASSWORD = 'your_ftp_password'

# Source and destination path mapping (must have same number of elements)
SOURCE_PATHS = [
    '/home/rocky/in/sample1.txt',
    '/home/rocky/bon/in/sample3.txt', 
    '/home/rocky/card/in/sample2.txt'
]

DESTINATION_PATHS = [
    '/home/rocky/in/sample1.txt',       # Maps to SOURCE_PATHS[0]
    '/home/rocky/bon/in/sample3.txt',   # Maps to SOURCE_PATHS[1]
    '/home/rocky/card/in/sample2.txt'   # Maps to SOURCE_PATHS[2]
]

def run_ssh_command(host, username, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, username=username, key_filename=SSH_KEY)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise Exception(f"Command failed (exit code {exit_code}): {error}")
        return output
    except Exception as e:
        raise Exception(f"SSH error on {host}: {e}")
    finally:
        ssh.close()

def get_file_size(host, username, file_path):
    try:
        command = f"stat -c%s {file_path} 2>/dev/null || echo 'FILE_NOT_FOUND'"
        result = run_ssh_command(host, username, command)
        if result == 'FILE_NOT_FOUND':
            return None
        return int(result)
    except:
        return None

def check_and_transfer_files(**context):
    print("=== STARTING FILE CHECK AND TRANSFER ===")
    
    # Validate that source and destination lists have same length
    if len(SOURCE_PATHS) != len(DESTINATION_PATHS):
        raise Exception(f"Source paths ({len(SOURCE_PATHS)}) and destination paths ({len(DESTINATION_PATHS)}) must have same length")
    
    transferred_files = []
    
    for i in range(len(SOURCE_PATHS)):
        source_file = SOURCE_PATHS[i]
        dest_file = DESTINATION_PATHS[i]
        
        print(f"\n--- Processing file {i+1}/{len(SOURCE_PATHS)} ---")
        print(f"Source: {source_file}")
        print(f"Destination: {dest_file}")
        
        try:
            # Check source file exists and get size
            source_size = get_file_size(VM2_HOST, VM2_USERNAME, source_file)
            if source_size is None:
                raise Exception(f"Source file not found: {source_file}")
            
            # Check destination file
            dest_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
            
            if dest_size is not None:
                if dest_size == source_size:
                    print("✓ File exists with same size - SKIPPING")
                    transferred_files.append(dest_file)
                    continue
                else:
                    raise Exception(f"File exists with different size: source={source_size}, dest={dest_size}")
            
            # Transfer file
            dest_dir = os.path.dirname(dest_file)
            run_ssh_command(VM3_HOST, VM3_USERNAME, f"mkdir -p {dest_dir}")
            
            ftp_cmd = f'''lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e "get {source_file} -o {dest_file}; quit"'''
            run_ssh_command(VM3_HOST, VM3_USERNAME, ftp_cmd)
            
            # Verify transfer
            transferred_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
            if transferred_size != source_size:
                raise Exception(f"Transfer failed: expected {source_size}, got {transferred_size}")
            
            print(f"✓ SUCCESS: Transferred {transferred_size} bytes")
            transferred_files.append(dest_file)
            
        except Exception as e:
            raise Exception(f"Transfer failed for {source_file}: {e}")
    
    return transferred_files

def check_processing_needed(**context):
    print("=== CHECKING PROCESSING STATUS ===")
    
    transferred_files = context['task_instance'].xcom_pull(task_ids='check_and_transfer')
    if not transferred_files:
        return []
    
    files_needing_processing = []
    
    for i, file_path in enumerate(transferred_files, 1):
        print(f"\n--- Checking file {i}: {file_path} ---")
        
        base_name = file_path.replace('.txt', '')
        dat_file = f"{base_name}.dat"
        inv_file = f"{base_name}.inv"
        
        # Check if ANY output file exists
        dat_exists = get_file_size(VM3_HOST, VM3_USERNAME, dat_file) is not None
        inv_exists = get_file_size(VM3_HOST, VM3_USERNAME, inv_file) is not None
        
        if dat_exists or inv_exists:
            # If ANY output file exists, raise error (don't process)
            error_msg = f"Output files already exist for {file_path}"
            if dat_exists:
                error_msg += f" (.dat exists)"
            if inv_exists:
                error_msg += f" (.inv exists)"
            
            print(f"✗ ERROR: {error_msg}")
            raise Exception(error_msg)
        
        print("○ No output files - will process")
        files_needing_processing.append(file_path)
    
    return files_needing_processing

def process_files(**context):
    print("=== STARTING FILE PROCESSING ===")
    
    files_to_process = context['task_instance'].xcom_pull(task_ids='check_processing_needed')
    if not files_to_process:
        print("No files to process")
        return
    
    for i, file_path in enumerate(files_to_process, 1):
        print(f"\n--- Processing file {i}: {file_path} ---")
        
        try:
            script_cmd = f"python3 /home/{VM3_USERNAME}/scripts/simple_file_manager.py {file_path}"
            result = run_ssh_command(VM3_HOST, VM3_USERNAME, script_cmd)
            print(f"✓ SUCCESS: {result}")
            
        except Exception as e:
            raise Exception(f"Processing failed for {file_path}: {e}")

# DAG Definition
with DAG(
    'fixed_ftp_file_processing',
    default_args={
        'owner': 'rocky',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Fixed FTP processing with path mapping',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    transfer_task = PythonOperator(
        task_id='check_and_transfer',
        python_callable=check_and_transfer_files,
    )
    
    check_task = PythonOperator(
        task_id='check_processing_needed',
        python_callable=check_processing_needed,
        provide_context=True,
    )
    
    process_task = PythonOperator(
        task_id='process_files',
        python_callable=process_files,
        provide_context=True,
    )
    
    transfer_task >> check_task >> process_task
```

## Airflow Logging System Explained

### 1. **Where Logs Are Stored:**
```bash
# Logs are stored in files, not database
$AIRFLOW_HOME/logs/

# Directory structure:
/home/rocky/airflow/logs/
├── dag_id=your_dag_name/
│   ├── run_id=manual__2025-05-25T10:00:00+00:00/
│   │   ├── task_id=task_name/
│   │   │   └── attempt=1.log
```

### 2. **How to Read Logs via Command Line:**

```bash
# Navigate to logs directory
cd /home/rocky/airflow/logs

# Find logs for specific DAG
find . -name "*fixed_ftp_file_processing*" -type d

# Read specific task log
cat dag_id=fixed_ftp_file_processing/run_id=manual__2025-05-25T10:00:00+00:00/task_id=check_and_transfer/attempt=1.log

# View recent logs
tail -f dag_id=fixed_ftp_file_processing/run_id=*/task_id=*/attempt=1.log

# Search logs for errors
grep -r "ERROR" dag_id=fixed_ftp_file_processing/
```

### 3. **Airflow CLI Commands for Logs:**

```bash
# View task logs
airflow tasks logs fixed_ftp_file_processing check_and_transfer 2025-05-25

# View DAG run logs
airflow dags show fixed_ftp_file_processing

# List task instances
airflow tasks list fixed_ftp_file_processing
```

### 4. **Log Storage Details:**

- **NOT handled by journald** - stored as regular files
- **Database stores** - metadata only (task status, timing, etc.)
- **Actual logs** - stored in filesystem as .log files
- **Log rotation** - configured in airflow.cfg
- **Retention** - old logs can be cleaned up automatically

### 5. **Quick Log Access:**

```bash
# Most recent run logs
ls -lat /home/rocky/airflow/logs/dag_id=fixed_ftp_file_processing/

# Live monitoring during DAG run
tail -f /home/rocky/airflow/logs/dag_id=fixed_ftp_file_processing/run_id=*/task_id=check_and_transfer/attempt=1.log
```

The key improvements:
1. **Path mapping** - source and destination lists map by index
2. **Stricter checking** - error if ANY output file exists
3. **Reduced comments** - cleaner code
4. **Log access** - multiple ways to read logs outside UI
