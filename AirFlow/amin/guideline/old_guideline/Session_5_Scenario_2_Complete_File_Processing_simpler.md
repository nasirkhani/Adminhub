You're absolutely right! Let me simplify everything and fix the SSH authentication issue.

## Issue #1: SSH Key Problem

In your config, you're using the **public key** (.pub), but you need the **private key**:

```python
# WRONG:
'ssh_key_path': '/home/rocky/.ssh/id_ed25519.pub',  # This is public key

# CORRECT:
'ssh_key_path': '/home/rocky/.ssh/id_ed25519',      # This is private key
```

## Simplified Solution

### Step 1: Simple Processing Script on VM3

```python
#!/usr/bin/env python3
# simple_file_manager.py

import sys
import os

def process_file(input_file):
    """Remove extra spaces from text file"""
    try:
        # Read the file
        with open(input_file, 'r') as f:
            content = f.read()
        
        # Remove extra spaces
        clean_content = ' '.join(content.split())
        
        # Get file name without .txt
        base_name = os.path.basename(input_file).replace('.txt', '')
        
        # Get directory and change 'in' to 'out'
        input_dir = os.path.dirname(input_file)
        output_dir = input_dir.replace('/in', '/out')
        
        # Create output file
        output_file = f"{output_dir}/modified_{base_name}.txt"
        with open(output_file, 'w') as f:
            f.write(clean_content)
        
        print(f"SUCCESS: Created {output_file}")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 simple_file_manager.py <file_path>")
        exit(1)
    
    success = process_file(sys.argv[1])
    exit(0 if success else 1)
```

### Step 2: Very Simple DAG

```python
# simple_file_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko

# Simple configuration
VM2_HOST = '192.168.83.132'
VM3_HOST = '192.168.83.133'  
USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'  # PRIVATE key, not .pub

def run_ssh_command(host, command):
    """Run command on remote host"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect with private key
        ssh.connect(hostname=host, username=USERNAME, key_filename=SSH_KEY)
        
        # Run command
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            print(f"Error: {error}")
            return None
        
        return output
    
    except Exception as e:
        print(f"SSH Error: {e}")
        return None
    
    finally:
        ssh.close()

def find_files(**context):
    """Find txt files on VM2"""
    command = f"find /home/{USERNAME} -name '*.txt' -path '*/in/*'"
    result = run_ssh_command(VM2_HOST, command)
    
    if result:
        files = result.split('\n')
        print(f"Found files: {files}")
        return files
    else:
        print("No files found")
        return []

def copy_and_process(**context):
    """Copy files from VM2 to VM3 and process them"""
    # Get file list from previous task
    files = context['task_instance'].xcom_pull(task_ids='find_files')
    
    if not files:
        print("No files to process")
        return
    
    for file_path in files:
        print(f"Processing: {file_path}")
        
        # Step 1: Copy file from VM2 to VM3
        copy_cmd = f"scp -i {SSH_KEY} {USERNAME}@{VM2_HOST}:{file_path} {USERNAME}@{VM3_HOST}:{file_path}"
        copy_result = os.system(copy_cmd)
        
        if copy_result == 0:
            print(f"File copied successfully: {file_path}")
            
            # Step 2: Process file on VM3
            process_cmd = f"python3 /home/{USERNAME}/scripts/simple_file_manager.py {file_path}"
            process_result = run_ssh_command(VM3_HOST, process_cmd)
            
            if process_result:
                print(f"Processing result: {process_result}")
            else:
                print(f"Processing failed for: {file_path}")
        else:
            print(f"Copy failed for: {file_path}")

# Simple DAG
with DAG(
    'simple_file_processing',
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

    # Task 1: Find files on VM2
    find_task = PythonOperator(
        task_id='find_files',
        python_callable=find_files,
    )

    # Task 2: Copy and process files
    process_task = PythonOperator(
        task_id='copy_and_process',
        python_callable=copy_and_process,
        provide_context=True,
    )

    # Set dependency
    find_task >> process_task
```

## What Each Part Does:

### Processing Script Explanation:
1. **Input**: Takes file path as argument (`/home/rocky/in/sample.txt`)
2. **Read**: Opens and reads the file content
3. **Clean**: Uses `' '.join(content.split())` to remove extra spaces
4. **Output**: Saves cleaned content to corresponding `out/` directory
5. **Example**: 
   - Input: `"Hello    world   !"` 
   - Output: `"Hello world !"`

### DAG Explanation:
1. **find_files**: Runs `find` command on VM2 to locate all .txt files in `/in/` directories
2. **copy_and_process**: 
   - Gets file list from first task
   - For each file: copies it to VM3, then processes it
   - Uses `scp` for copying and SSH for processing

## Fix Your Configuration:

Change this line in your DAG:
```python
'ssh_key_path': '/home/rocky/.ssh/id_ed25519',  # Remove .pub
```

## Quick Test Setup:

On VM2, create test files:
```bash
# On VM2
mkdir -p /home/rocky/{in,out,bon/in,bon/out,card/in,card/out}
echo "Hello    world   with   spaces" > /home/rocky/in/test.txt
```

On VM3, create the script:
```bash
# On VM3  
mkdir -p /home/rocky/scripts
# Copy the simple_file_manager.py script above
chmod +x /home/rocky/scripts/simple_file_manager.py
```

This simplified version should work much better. Try it and let me know what happens!











! prompt 
Excellent questions! You've identified critical issues that are fundamental to understanding Airflow. Let me fix them and explain the concepts.

## Issue #1: Missing Import - Fixed

## Issue #2: .dat File Creation - Fixed  

## Issue #3: Critical Error Handling Issue - Fixed

**This is the most important concept**: In Airflow, if you want a task to **FAIL**, you must **raise an exception**. If your function completes without raising an exception, Airflow considers it **SUCCESS** regardless of what happened inside.

## Fixed Code

### Fixed Processing Script on VM3:

```python
#!/usr/bin/env python3
# simple_file_manager.py

import sys
import os

def process_file(input_file):
    """Remove extra spaces and create .dat file"""
    try:
        # Read the file
        with open(input_file, 'r') as f:
            content = f.read()
        
        # Remove extra spaces
        clean_content = ' '.join(content.split())
        
        # Get file name without .txt
        base_name = os.path.basename(input_file).replace('.txt', '')
        
        # Get directory and change 'in' to 'out'
        input_dir = os.path.dirname(input_file)
        output_dir = input_dir.replace('/in', '/out')
        
        # Create output files
        txt_file = f"{output_dir}/modified_{base_name}.txt"
        dat_file = f"{output_dir}/{base_name}.dat"
        
        # Write modified text file
        with open(txt_file, 'w') as f:
            f.write(clean_content)
        
        # Write success to .dat file (binary with "1")
        with open(dat_file, 'wb') as f:
            f.write(b'1')
        
        print(f"SUCCESS: Created {txt_file}")
        print(f"SUCCESS: Created {dat_file}")
        return True
        
    except Exception as e:
        # Create failure .dat file with "0"
        base_name = os.path.basename(input_file).replace('.txt', '')
        input_dir = os.path.dirname(input_file)
        output_dir = input_dir.replace('/in', '/out')
        dat_file = f"{output_dir}/{base_name}.dat"
        
        with open(dat_file, 'wb') as f:
            f.write(b'0')
        
        print(f"ERROR: {e}")
        print(f"ERROR: Created failure {dat_file}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 simple_file_manager.py <file_path>")
        exit(1)
    
    success = process_file(sys.argv[1])
    exit(0 if success else 1)
```

### Fixed DAG with Proper Error Handling:

```python
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
    'simple_file_processing',
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
```

## Key Fixes Explained:

### 1. Added Missing Import:
```python
import os  # Now SCP commands will work
```

### 2. Fixed .dat File Creation:
```python
# Success case: Write binary "1"
with open(dat_file, 'wb') as f:
    f.write(b'1')

# Failure case: Write binary "0"  
with open(dat_file, 'wb') as f:
    f.write(b'0')
```

### 3. Fixed Critical Error Handling:
```python
# BEFORE (Wrong):
if copy_result != 0:
    print("Copy failed")  # Task still shows SUCCESS!

# AFTER (Correct):
if copy_result != 0:
    raise Exception("Copy failed")  # Task shows FAILED!
```

## Understanding Airflow Logs

**Where do log messages come from?**

1. **Python `print()` statements** in your DAG functions → Appear in task logs
2. **Airflow internal messages** → Automatically generated (connection info, task status)
3. **Command outputs** from SSH/SCP → Captured and displayed
4. **Error messages** from exceptions → Automatically logged

**Example log breakdown:**
```
[2025-05-25, 10:22:19 +0330] {logging_mixin.py:188} INFO - Processing: /home/rocky/in/sample1.txt
↑ Timestamp                   ↑ Airflow internal        ↑ Your print() statement

[2025-05-25, 10:22:19 +0330] {transport.py:1909} INFO - Connected (version 2.0, client OpenSSH_8.7)
↑ Timestamp                   ↑ Paramiko SSH library    ↑ SSH connection message
```

## Understanding FTP Setup

### What is FTP and Why We Set It Up:

**FTP (File Transfer Protocol)** allows file sharing between machines over a network.

### Testing FTP Separately:

```bash
# Test 1: Connect to FTP server from any machine
ftp 192.168.83.132

# You should see:
# Connected to 192.168.83.132
# 220 (vsFTPd 3.0.2)
# Name (192.168.83.132:username): rocky
# Password: [enter password]
# 230 Login successful

# Test 2: Basic FTP commands
ftp> ls                    # List files
ftp> cd bon/in            # Change directory  
ftp> put localfile.txt    # Upload file
ftp> get remotefile.txt   # Download file
ftp> quit                 # Exit

# Test 3: Command-line FTP upload
echo "test content" > test.txt
ftp -inv 192.168.83.132 << EOF
user rocky your_password
cd in
put test.txt
quit
EOF
```

### FTP Use Cases:
1. **File sharing** between different systems
2. **Automated file transfers** in scripts
3. **Backup operations** to remote servers
4. **Web server file uploads** for websites

### Most Useful FTP Commands:
```bash
ls          # List files
cd dirname  # Change directory
pwd         # Show current directory
get file    # Download file
put file    # Upload file
mget *.txt  # Download multiple files
mput *.txt  # Upload multiple files
binary      # Switch to binary mode (for non-text files)
quit        # Exit FTP
```

Now try the fixed code - it should properly fail tasks when errors occur and create both .txt and .dat files!
