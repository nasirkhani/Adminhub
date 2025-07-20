# improved_ftp_file_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import paramiko
import os

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Server connection details
VM2_HOST = '192.168.83.132'        # FTP server (source files)
VM3_HOST = '192.168.83.133'        # Processing server (destination)

# Username configuration (can be different for each VM)
VM2_USERNAME = 'rocky'             # Username on VM2 (FTP server)
VM3_USERNAME = 'rocky'             # Username on VM3 (processing server)

# Authentication details
SSH_KEY = '/home/rocky/.ssh/id_ed25519'    # SSH private key path
FTP_PASSWORD = '111'         # FTP password for VM2

# File paths to process (hardcoded list - no discovery needed)
FILE_PATHS_TO_PROCESS = [
    '/home/rocky/in/sample1.txt',
    '/home/rocky/bon/in/sample3.txt', 
    '/home/rocky/card/in/sample2.txt'
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_ssh_command(host, username, command):
    """
    Execute a command on remote host via SSH
    
    Parameters:
    - host: Target server IP address
    - username: Username for SSH connection
    - command: Command to execute
    
    Returns:
    - Command output as string
    
    Raises:
    - Exception if command fails
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host} as {username}...")
        ssh.connect(hostname=host, username=username, key_filename=SSH_KEY)
        
        print(f"Executing: {command}")
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
    """
    Get file size on remote host
    
    Returns:
    - File size in bytes, or None if file doesn't exist
    """
    try:
        # Use 'stat' command to get file size
        command = f"stat -c%s {file_path} 2>/dev/null || echo 'FILE_NOT_FOUND'"
        result = run_ssh_command(host, username, command)
        
        if result == 'FILE_NOT_FOUND':
            return None
        
        return int(result)
    
    except:
        return None

# =============================================================================
# TASK FUNCTIONS
# =============================================================================

def check_and_transfer_files(**context):
    """
    TASK 1: Check file existence and transfer files via FTP
    
    For each file in FILE_PATHS_TO_PROCESS:
    1. Check if file exists on destination (VM3)
    2. If exists with same size -> skip transfer
    3. If exists with different size -> raise error
    4. If doesn't exist -> transfer via FTP
    """
    print("=== STARTING FILE CHECK AND TRANSFER ===")
    
    transferred_files = []  # Keep track of which files we processed
    
    for i, source_file_path in enumerate(FILE_PATHS_TO_PROCESS, 1):
        print(f"\n--- Processing file {i}/{len(FILE_PATHS_TO_PROCESS)}: {source_file_path} ---")
        
        try:
            # Get source file size on VM2
            source_size = get_file_size(VM2_HOST, VM2_USERNAME, source_file_path)
            if source_size is None:
                raise Exception(f"Source file does not exist on VM2: {source_file_path}")
            
            print(f"Source file size on VM2: {source_size} bytes")
            
            # Check if destination file exists on VM3
            dest_size = get_file_size(VM3_HOST, VM3_USERNAME, source_file_path)
            
            if dest_size is not None:
                # File exists on destination
                print(f"Destination file size on VM3: {dest_size} bytes")
                
                if dest_size == source_size:
                    # Same size - skip transfer
                    print("✓ File already exists with identical size - SKIPPING transfer")
                    transferred_files.append(source_file_path)
                    continue
                else:
                    # Different size - this is an error condition
                    error_msg = f"File exists on destination but size differs: source={source_size}, dest={dest_size}"
                    print(f"✗ ERROR: {error_msg}")
                    raise Exception(error_msg)
            
            # File doesn't exist on destination - proceed with transfer
            print("File not found on destination - proceeding with FTP transfer")
            
            # Create destination directory structure on VM3
            dest_dir = os.path.dirname(source_file_path)
            create_dir_cmd = f"mkdir -p {dest_dir}"
            run_ssh_command(VM3_HOST, VM3_USERNAME, create_dir_cmd)
            print(f"Created directory: {dest_dir}")
            
            # Transfer file using FTP (lftp command executed on VM3)
            filename = os.path.basename(source_file_path)
            ftp_cmd = f'''lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e "get {source_file_path} -o {source_file_path}; quit"'''
            
            print("Starting FTP transfer...")
            run_ssh_command(VM3_HOST, VM3_USERNAME, ftp_cmd)
            
            # Verify transfer by checking file size
            transferred_size = get_file_size(VM3_HOST, VM3_USERNAME, source_file_path)
            if transferred_size != source_size:
                raise Exception(f"Transfer verification failed: expected {source_size}, got {transferred_size}")
            
            print(f"✓ SUCCESS: File transferred successfully ({transferred_size} bytes)")
            transferred_files.append(source_file_path)
            
        except Exception as e:
            print(f"✗ ERROR: Failed to process {source_file_path}: {e}")
            raise Exception(f"File transfer failed: {e}")
    
    print(f"\n=== TRANSFER COMPLETED ===")
    print(f"Total files processed: {len(transferred_files)}")
    
    # Return list of files for next task
    return transferred_files

def check_processing_needed(**context):
    """
    TASK 2: Check if files need processing
    
    For each transferred file, check if output files (.dat and .inv) already exist.
    Only process files that don't have complete output files.
    """
    print("=== CHECKING WHICH FILES NEED PROCESSING ===")
    
    # Get transferred files from previous task
    transferred_files = context['task_instance'].xcom_pull(task_ids='check_and_transfer')
    
    if not transferred_files:
        print("No files to check for processing")
        return []
    
    files_needing_processing = []
    
    for i, file_path in enumerate(transferred_files, 1):
        print(f"\n--- Checking file {i}/{len(transferred_files)}: {file_path} ---")
        
        try:
            # Generate expected output file names
            base_name = file_path.replace('.txt', '')
            dat_file = f"{base_name}.dat"
            inv_file = f"{base_name}.inv"
            
            print(f"Checking for: {dat_file}")
            print(f"Checking for: {inv_file}")
            
            # Check if both output files exist on VM3
            dat_exists = get_file_size(VM3_HOST, VM3_USERNAME, dat_file) is not None
            inv_exists = get_file_size(VM3_HOST, VM3_USERNAME, inv_file) is not None
            
            if dat_exists and inv_exists:
                print("✓ Both .dat and .inv files already exist - SKIPPING processing")
            elif dat_exists or inv_exists:
                print("⚠ Only partial output files exist - WILL reprocess")
                files_needing_processing.append(file_path)
            else:
                print("○ No output files exist - WILL process")
                files_needing_processing.append(file_path)
                
        except Exception as e:
            print(f"✗ ERROR checking {file_path}: {e}")
            # If we can't check, assume processing is needed
            files_needing_processing.append(file_path)
    
    print(f"\n=== PROCESSING CHECK COMPLETED ===")
    print(f"Files needing processing: {len(files_needing_processing)}")
    for file_path in files_needing_processing:
        print(f"  - {file_path}")
    
    return files_needing_processing

def process_files(**context):
    """
    TASK 3: Process files that need processing
    
    Run the simple_file_manager.py script on VM3 for each file that needs processing.
    """
    print("=== STARTING FILE PROCESSING ===")
    
    # Get files that need processing from previous task
    files_to_process = context['task_instance'].xcom_pull(task_ids='check_processing_needed')
    
    if not files_to_process:
        print("No files need processing - all files already have output files")
        return
    
    print(f"Processing {len(files_to_process)} files...")
    
    success_count = 0
    
    for i, file_path in enumerate(files_to_process, 1):
        print(f"\n--- Processing file {i}/{len(files_to_process)}: {file_path} ---")
        
        try:
            # Run the processing script on VM3
            script_cmd = f"python3 /home/{VM3_USERNAME}/scripts/simple_file_manager.py {file_path}"
            
            print("Running processing script...")
            result = run_ssh_command(VM3_HOST, VM3_USERNAME, script_cmd)
            
            print(f"✓ SUCCESS: Processing completed")
            print(f"Script output: {result}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ ERROR: Processing failed for {file_path}: {e}")
            raise Exception(f"File processing failed: {e}")
    
    print(f"\n=== PROCESSING COMPLETED ===")
    print(f"Successfully processed: {success_count}/{len(files_to_process)} files")

# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    'improved_ftp_file_processing',
    default_args={
        'owner': 'rocky',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Improved FTP file processing with existence checks',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 1),
    catchup=False,
    tags=['ftp', 'file-processing', 'improved'],
) as dag:

    # Task 1: Check files and transfer if needed
    transfer_task = PythonOperator(
        task_id='check_and_transfer',
        python_callable=check_and_transfer_files,
        doc_md="""
        **File Transfer Task**
        
        Checks each file in the hardcoded list and:
        - Skips if already exists with same size
        - Errors if exists with different size  
        - Transfers via FTP if doesn't exist
        """,
    )
    
    # Task 2: Check which files need processing
    check_task = PythonOperator(
        task_id='check_processing_needed',
        python_callable=check_processing_needed,
        provide_context=True,
        doc_md="""
        **Processing Check Task**
        
        Determines which files need processing by checking
        if .dat and .inv output files already exist.
        """,
    )
    
    # Task 3: Process files that need processing
    process_task = PythonOperator(
        task_id='process_files',
        python_callable=process_files,
        provide_context=True,
        doc_md="""
        **File Processing Task**
        
        Runs the Python script to generate .dat and .inv files
        for files that don't already have complete output.
        """,
    )
    
    # Task dependencies: transfer -> check -> process
    transfer_task >> check_task >> process_task
