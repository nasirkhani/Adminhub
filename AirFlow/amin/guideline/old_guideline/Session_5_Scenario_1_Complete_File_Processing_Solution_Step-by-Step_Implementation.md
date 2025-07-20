# Complete File Processing Solution: Step-by-Step Implementation

Perfect! Now I have all the details. Let me guide you through the complete implementation, starting with the FTP server setup, then the processing script, and finally the DAG.

## Step 1: Setting Up FTP Server on VM2 (192.168.83.132)

### Install and Configure vsftpd on VM2:

```bash
# SSH into VM2 first
ssh your_username@192.168.83.132

# Install FTP server
sudo yum install vsftpd -y

# Edit the configuration
sudo nano /etc/vsftpd/vsftpd.conf
```

### FTP Configuration (/etc/vsftpd/vsftpd.conf):

```bash
# Basic FTP settings
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022

# Security settings
chroot_local_user=YES
allow_writeable_chroot=YES

# Passive mode (important for network access)
pasv_enable=YES
pasv_min_port=10000
pasv_max_port=10100

# Listen settings
listen=YES
listen_ipv6=NO

# User settings
userlist_enable=YES
userlist_file=/etc/vsftpd/user_list
userlist_deny=NO
```

### Start and Enable FTP Service:

```bash
# Start FTP service
sudo systemctl start vsftpd
sudo systemctl enable vsftpd

# Allow FTP through firewall
sudo firewall-cmd --permanent --add-service=ftp
sudo firewall-cmd --permanent --add-port=10000-10100/tcp
sudo firewall-cmd --reload

# Add your user to allowed FTP users
echo "your_username" | sudo tee -a /etc/vsftpd/user_list
```

### Create Directory Structure on VM2:

```bash
# Create the required directory structure
cd /home/your_username
mkdir -p {bon,card,""}/{in,out,err}

# Create some sample files for testing
echo "This is a sample text file with extra spaces   ." > in/sample1.txt
echo "Another test file  with   whitespace    ." > card/in/sample2.txt  
echo "Third file in bon directory    ." > bon/in/sample3.txt
```

## Step 2: Create Processing Script on VM3

### SSH into VM3 and Create the Script:

```bash
# SSH into VM3
ssh your_username@192.168.83.133

# Create scripts directory
mkdir -p /home/your_username/scripts

# Create directory structure (same as VM2)
mkdir -p {bon,card,""}/{in,out,err}
```

### Create file_manager.py on VM3:

```python
#!/usr/bin/env python3
# file_manager.py - Process text files by removing whitespace and creating binary version

import sys
import os
import re
from datetime import datetime

def process_file(input_file_path):
    """
    Process a text file: remove extra whitespace and create binary version
    """
    try:
        # Get file information
        file_dir = os.path.dirname(input_file_path)
        file_name = os.path.basename(input_file_path)
        file_base = os.path.splitext(file_name)[0]  # Remove .txt extension
        
        # Determine output directory (replace 'in' with 'out' in path)
        output_dir = file_dir.replace('/in', '/out')
        
        # Determine error directory (replace 'in' with 'err' in path)  
        error_dir = file_dir.replace('/in', '/err')
        
        print(f"Processing file: {input_file_path}")
        print(f"Output directory: {output_dir}")
        
        # Read the input file
        with open(input_file_path, 'r') as f:
            content = f.read()
        
        # Remove extra whitespace (multiple spaces become single space)
        cleaned_content = re.sub(r'\s+', ' ', content.strip())
        
        # Create modified text file
        modified_file_path = os.path.join(output_dir, f'modified_{file_name}')
        with open(modified_file_path, 'w') as f:
            f.write(cleaned_content)
        
        # Create binary file (.dat)
        binary_file_path = os.path.join(output_dir, f'{file_base}.dat')
        with open(binary_file_path, 'wb') as f:
            f.write(cleaned_content.encode('utf-8'))
        
        print(f"SUCCESS: Created {modified_file_path}")
        print(f"SUCCESS: Created {binary_file_path}")
        
        return True
        
    except Exception as e:
        # Create error file in err directory
        error_file_path = os.path.join(error_dir, f'error_{file_name}')
        error_message = f"Error processing {input_file_path} at {datetime.now()}: {str(e)}"
        
        with open(error_file_path, 'w') as f:
            f.write(error_message)
        
        print(f"ERROR: {error_message}")
        print(f"ERROR: Created error file at {error_file_path}")
        
        return False

if __name__ == "__main__":
    # Check if file path argument is provided
    if len(sys.argv) != 2:
        print("Usage: python3 file_manager.py <input_file_path>")
        sys.exit(1)
    
    # Get input file path from command line
    input_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} does not exist")
        sys.exit(1)
    
    # Process the file
    success = process_file(input_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
```

### Make the Script Executable:

```bash
chmod +x /home/your_username/scripts/file_manager.py
```

## Step 3: Create the Airflow DAG

### Create the DAG file on VM1:

```python
# file_processing_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko
import os

# Configuration - Change these values for your setup
CONFIG = {
    'vm2_host': '192.168.83.132',  # FTP server
    'vm3_host': '192.168.83.133',  # Processing server
    'username': 'your_username',   # Same username on both VMs
    'ssh_key_path': '/home/rocky/.ssh/id_rsa',  # SSH key path on VM1
    'base_dirs': ['in', 'bon/in', 'card/in'],   # Directories to scan for files
}

def ssh_execute_command(host, username, key_path, command):
    """Execute command on remote host via SSH"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to remote host
        ssh_client.connect(hostname=host, username=username, key_filename=key_path)
        
        # Execute command
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Get results
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0 and error:
            raise Exception(f"Command failed: {error}")
        
        return output
    
    finally:
        ssh_client.close()

def discover_files(**context):
    """Discover all .txt files in the specified directories on VM2"""
    files_found = []
    
    # Command to find all .txt files in the specified directories
    find_command = f"find /home/{CONFIG['username']} -name '*.txt' -path '*/in/*' -type f"
    
    try:
        # Execute find command on VM2
        output = ssh_execute_command(
            CONFIG['vm2_host'], 
            CONFIG['username'], 
            CONFIG['ssh_key_path'], 
            find_command
        )
        
        # Parse output to get list of files
        if output:
            files_found = output.split('\n')
            files_found = [f.strip() for f in files_found if f.strip()]
        
        print(f"Found {len(files_found)} files to process:")
        for file_path in files_found:
            print(f"  - {file_path}")
        
        # Store file list in XCom for other tasks
        return files_found
    
    except Exception as e:
        print(f"Error discovering files: {e}")
        return []

def transfer_file(source_file, **context):
    """Transfer a single file from VM2 to VM3"""
    try:
        # Use SCP command to transfer file
        scp_command = f"scp -i {CONFIG['ssh_key_path']} {CONFIG['username']}@{CONFIG['vm2_host']}:{source_file} {CONFIG['username']}@{CONFIG['vm3_host']}:{source_file}"
        
        # Execute SCP from VM1 (this machine)
        result = os.system(scp_command)
        
        if result == 0:
            print(f"Successfully transferred: {source_file}")
            return True
        else:
            raise Exception(f"SCP command failed with exit code {result}")
    
    except Exception as e:
        print(f"Error transferring {source_file}: {e}")
        return False

def process_file_on_vm3(file_path, **context):
    """Process the transferred file using file_manager.py on VM3"""
    try:
        # Command to run file_manager.py on VM3
        process_command = f"python3 /home/{CONFIG['username']}/scripts/file_manager.py {file_path}"
        
        # Execute processing command on VM3
        result = ssh_execute_command(
            CONFIG['vm3_host'],
            CONFIG['username'], 
            CONFIG['ssh_key_path'],
            process_command
        )
        
        print(f"Processing result for {file_path}:")
        print(result)
        
        return True
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

# Define the DAG
with DAG(
    'file_processing_workflow',
    default_args={
        'owner': 'your_name',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Hourly file processing from VM2 to VM3',
    schedule_interval='@hourly',  # Run every hour
    start_date=datetime(2024, 5, 1),
    catchup=False,
) as dag:

    # Task 1: Discover files on VM2
    discover_task = PythonOperator(
        task_id='discover_files',
        python_callable=discover_files,
    )

    # Task 2: Create dynamic tasks for each file found
    # This will be created dynamically based on discovered files
    def create_file_processing_tasks(**context):
        """Create processing tasks for each discovered file"""
        # Get file list from discover task
        files = context['task_instance'].xcom_pull(task_ids='discover_files')
        
        if not files:
            print("No files found to process")
            return
        
        # Process each file (in this simplified version, we'll process them sequentially)
        for file_path in files:
            print(f"\n--- Processing {file_path} ---")
            
            # Step 1: Transfer file
            if transfer_file(file_path, **context):
                # Step 2: Process file on VM3
                process_file_on_vm3(file_path, **context)
            else:
                print(f"Skipping processing of {file_path} due to transfer failure")

    # Combined task for transfer and processing
    process_files_task = PythonOperator(
        task_id='process_all_files',
        python_callable=create_file_processing_tasks,
        provide_context=True,
    )

    # Set task dependencies
    discover_task >> process_files_task
```

## Explanation of the Complete Solution

### How the FTP Server Setup Works:
- **vsftpd**: A secure FTP daemon that allows file transfer
- **Passive Mode**: Configured for better network compatibility
- **User Authentication**: Only specified users can access FTP
- **Directory Structure**: Created to match your requirements

### How the file_manager.py Script Works:
- **Input**: Takes file path as command-line argument
- **Processing**: Removes extra whitespace using regex `\s+` (multiple spaces → single space)
- **Output Success**: Creates `modified_*.txt` and `*.dat` files in corresponding `out/` directory
- **Output Failure**: Creates error description file in corresponding `err/` directory

### How the DAG Works:
1. **discover_files**: Finds all `.txt` files in `in/` directories on VM2
2. **process_all_files**: For each discovered file:
   - Transfers from VM2 to VM3 using SCP
   - Runs `file_manager.py` on VM3 to process the file

### Key Features:
- **Dynamic Path Resolution**: Uses `$HOME` and username variables
- **Error Handling**: Handles transfer and processing failures
- **Hourly Schedule**: Runs automatically every hour
- **One-by-One Processing**: Processes files sequentially as requested

Would you like me to explain any specific part in more detail, or shall we test this implementation?
