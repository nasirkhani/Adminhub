You're absolutely right! The **TaskFlow API** with `@dag` and `@task` decorators is **much better** and **easier** to write. It was introduced in Airflow 2.0 and is now the **recommended approach**.

## Why TaskFlow API (@dag/@task) is Better:

1. **Cleaner syntax** - No need for PythonOperator
2. **Automatic data passing** - Return values automatically become XComs
3. **Less boilerplate** - Functions directly become tasks
4. **More Pythonic** - Feels like normal Python programming
5. **Better type hints** - IDE support and error checking
6. **Easier debugging** - Simpler code structure

## Rewritten Code Using TaskFlow API with Comprehensive Comments

### TaskFlow API Version with Full Comments

```python
# taskflow_ftp_processing_dag.py

# =============================================================================
# IMPORTS SECTION
# =============================================================================
# Import all necessary modules for our Airflow DAG

from datetime import datetime, timedelta  # For date/time handling in DAG scheduling
import os                                # For file path operations
import paramiko                          # For SSH connections to remote servers

# TASKFLOW API IMPORTS - These are the modern way to write Airflow DAGs
from airflow.decorators import dag, task  # Main decorators for creating DAGs and tasks

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================
# Centralized configuration makes the code easy to modify and maintain

# VM Connection Details
VM2_HOST = '192.168.83.132'              # IP address of FTP server (source)
VM3_HOST = '192.168.83.133'              # IP address of processing server (destination)

# User Authentication (can be different for each VM)
VM2_USERNAME = 'rocky'                   # Username on VM2 (FTP server)
VM3_USERNAME = 'rocky'                   # Username on VM3 (processing server)
SSH_KEY = '/home/rocky/.ssh/id_ed25519'  # Path to SSH private key for authentication
FTP_PASSWORD = 'your_ftp_password'       # Password for FTP login on VM2

# FILE MAPPING CONFIGURATION
# These two lists must have the same number of elements
# Each index position maps source to destination (index 0 -> index 0, etc.)
SOURCE_PATHS = [
    '/home/rocky/in/sample1.txt',         # Source file 1 on VM2
    '/home/rocky/bon/in/sample3.txt',     # Source file 2 on VM2
    '/home/rocky/card/in/sample2.txt'     # Source file 3 on VM2
]

DESTINATION_PATHS = [
    '/home/rocky/in/sample1.txt',         # Where source file 1 goes on VM3
    '/home/rocky/bon/in/sample3.txt',     # Where source file 2 goes on VM3
    '/home/rocky/card/in/sample2.txt'     # Where source file 3 goes on VM3
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
# These helper functions are used by multiple tasks but are not tasks themselves

def run_ssh_command(host, username, command):
    """
    Execute a shell command on a remote server via SSH
    
    This function handles all the complexity of SSH connections:
    - Establishes secure connection using SSH keys
    - Executes the command remotely
    - Captures output and error messages
    - Checks if command succeeded or failed
    - Closes connection properly
    
    Parameters:
        host (str): IP address of remote server (e.g., '192.168.83.132')
        username (str): Username to connect with (e.g., 'rocky')
        command (str): Shell command to execute (e.g., 'ls -la')
    
    Returns:
        str: Output from the executed command
    
    Raises:
        Exception: If SSH connection fails or command returns non-zero exit code
        
    Example:
        result = run_ssh_command('192.168.83.132', 'rocky', 'hostname')
        # result might be: 'vm2-server'
    """
    # Create SSH client object - this handles the secure connection
    ssh = paramiko.SSHClient()
    
    # Auto-accept host keys (in production, you'd verify these manually)
    # This prevents "unknown host" errors when connecting to new servers
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"🔌 Connecting to {host} as user '{username}'...")
        
        # Establish SSH connection using private key authentication
        # This is more secure than password authentication
        ssh.connect(
            hostname=host,           # Server to connect to
            username=username,       # User account to use
            key_filename=SSH_KEY     # Private key file for authentication
        )
        
        print(f"💻 Executing command: {command}")
        
        # Execute command on remote server
        # stdin = input channel (we don't use this)
        # stdout = normal output from command
        # stderr = error output from command
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Read the results from command execution
        output = stdout.read().decode().strip()    # Convert bytes to string, remove whitespace
        error = stderr.read().decode().strip()     # Get any error messages
        exit_code = stdout.channel.recv_exit_status()  # 0 = success, other = failure
        
        # Check if command executed successfully
        if exit_code != 0:
            # Command failed - create descriptive error message
            error_message = f"Command '{command}' failed with exit code {exit_code}"
            if error:
                error_message += f": {error}"
            
            print(f"❌ {error_message}")
            raise Exception(error_message)
        
        # Command succeeded - return the output
        print(f"✅ Command executed successfully")
        if output:
            print(f"📄 Output: {output}")
        
        return output
    
    except Exception as e:
        # Re-raise with more context about what went wrong
        error_message = f"SSH operation failed on {host}: {str(e)}"
        print(f"💥 {error_message}")
        raise Exception(error_message)
    
    finally:
        # Always close SSH connection to free resources
        # This happens even if an exception occurred
        ssh.close()
        print(f"🔌 SSH connection to {host} closed")

def get_file_size(host, username, file_path):
    """
    Get the size of a file on a remote server
    
    Uses the 'stat' command to check if file exists and get its size.
    This is useful for comparing files before transfer.
    
    Parameters:
        host (str): IP address of remote server
        username (str): Username for SSH connection
        file_path (str): Full path to file on remote server
    
    Returns:
        int: File size in bytes, or None if file doesn't exist
        
    Example:
        size = get_file_size('192.168.83.132', 'rocky', '/home/rocky/test.txt')
        if size is None:
            print("File doesn't exist")
        else:
            print(f"File is {size} bytes")
    """
    try:
        # Build command to get file size
        # stat -c%s = show only size in bytes
        # 2>/dev/null = hide error messages if file doesn't exist
        # || echo 'FILE_NOT_FOUND' = if stat fails, print this instead
        command = f"stat -c%s {file_path} 2>/dev/null || echo 'FILE_NOT_FOUND'"
        
        # Execute the command
        result = run_ssh_command(host, username, command)
        
        # Check if file was found
        if result == 'FILE_NOT_FOUND':
            print(f"📁 File not found: {file_path}")
            return None
        
        # Convert size string to integer
        file_size = int(result)
        print(f"📏 File size: {file_size} bytes")
        return file_size
    
    except Exception as e:
        # If anything goes wrong, assume file doesn't exist
        print(f"⚠️  Error checking file size for {file_path}: {e}")
        return None

# =============================================================================
# DAG DEFINITION USING TASKFLOW API
# =============================================================================
# The @dag decorator converts this function into an Airflow DAG
# This is much cleaner than the traditional DAG() context manager approach

@dag(
    # DAG CONFIGURATION
    dag_id='taskflow_ftp_processing',                    # Unique identifier in Airflow UI
    description='File processing using TaskFlow API',    # Description shown in UI
    
    # SCHEDULING CONFIGURATION
    schedule_interval='@hourly',                         # Run every hour (cron: 0 * * * *)
    start_date=datetime(2024, 5, 1),                    # When scheduling should begin
    catchup=False,                                      # Don't run for past dates
    
    # DEFAULT TASK CONFIGURATION
    # These settings apply to all tasks in the DAG unless overridden
    default_args={
        'owner': 'rocky',                               # Who owns this DAG
        'retries': 1,                                   # Retry failed tasks once
        'retry_delay': timedelta(minutes=5),            # Wait 5 minutes before retry
        'email_on_failure': False,                      # Don't send emails on failure
        'email_on_retry': False,                        # Don't send emails on retry
    },
    
    # METADATA
    tags=['taskflow', 'ftp', 'file-processing']         # Tags for organization in UI
)
def taskflow_ftp_processing_workflow():
    """
    MAIN DAG FUNCTION
    
    This function defines the entire workflow using TaskFlow API.
    Each @task decorated function becomes an Airflow task.
    Task dependencies are defined by function calls and return values.
    
    Workflow:
    1. Check files and transfer via FTP if needed
    2. Check which files need processing (no existing output files)
    3. Process files that need processing
    """
    
    # =========================================================================
    # TASK 1: FILE TRANSFER WITH EXISTENCE CHECKING
    # =========================================================================
    # The @task decorator converts this function into an Airflow task
    # The function name becomes the task_id automatically
    
    @task
    def check_and_transfer_files():
        """
        TASK 1: Intelligent file transfer with existence checking
        
        This task performs smart file transfer:
        - Skips files that already exist with same size
        - Errors if files exist with different size
        - Transfers files that don't exist using FTP protocol
        
        Returns:
            list: List of destination file paths that were processed
            
        Why return a list?
        - TaskFlow API automatically stores return values in XCom
        - Next tasks can access this data by accepting it as parameter
        - This eliminates manual XCom push/pull operations
        """
        print("=" * 60)
        print("🚀 STARTING INTELLIGENT FILE TRANSFER")
        print("=" * 60)
        
        # VALIDATION: Ensure source and destination lists match
        if len(SOURCE_PATHS) != len(DESTINATION_PATHS):
            error_msg = f"Configuration error: SOURCE_PATHS has {len(SOURCE_PATHS)} items, DESTINATION_PATHS has {len(DESTINATION_PATHS)} items. They must match!"
            print(f"💥 {error_msg}")
            raise Exception(error_msg)
        
        print(f"📋 Processing {len(SOURCE_PATHS)} file mappings")
        
        # Keep track of successfully processed files
        processed_files = []
        
        # MAIN LOOP: Process each source-destination pair
        for index in range(len(SOURCE_PATHS)):
            source_file = SOURCE_PATHS[index]
            dest_file = DESTINATION_PATHS[index]
            
            print(f"\n{'─' * 40}")
            print(f"📂 Processing file {index + 1}/{len(SOURCE_PATHS)}")
            print(f"📤 Source:      {source_file}")
            print(f"📥 Destination: {dest_file}")
            print(f"{'─' * 40}")
            
            try:
                # STEP 1: Verify source file exists and get its size
                print("🔍 Checking source file...")
                source_size = get_file_size(VM2_HOST, VM2_USERNAME, source_file)
                
                if source_size is None:
                    error_msg = f"Source file not found on VM2: {source_file}"
                    print(f"💥 {error_msg}")
                    raise Exception(error_msg)
                
                print(f"✅ Source file found: {source_size} bytes")
                
                # STEP 2: Check if destination file already exists
                print("🔍 Checking destination file...")
                dest_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
                
                if dest_size is not None:
                    # File exists on destination - check size
                    print(f"📄 Destination file exists: {dest_size} bytes")
                    
                    if dest_size == source_size:
                        # Same size - skip transfer (optimization)
                        print("🎯 Files are identical size - SKIPPING transfer")
                        processed_files.append(dest_file)
                        continue
                    else:
                        # Different size - this indicates a problem
                        error_msg = f"File size mismatch! Source: {source_size} bytes, Destination: {dest_size} bytes"
                        print(f"💥 {error_msg}")
                        raise Exception(error_msg)
                
                # STEP 3: File doesn't exist on destination - proceed with transfer
                print("📂 Destination file not found - proceeding with FTP transfer")
                
                # Create destination directory structure if it doesn't exist
                dest_directory = os.path.dirname(dest_file)
                print(f"📁 Creating destination directory: {dest_directory}")
                
                create_dir_command = f"mkdir -p {dest_directory}"
                run_ssh_command(VM3_HOST, VM3_USERNAME, create_dir_command)
                
                # STEP 4: Transfer file using FTP protocol
                print("🌐 Starting FTP transfer...")
                
                # Build lftp command for secure file transfer
                # lftp is more reliable than basic ftp command
                ftp_command = f'''lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e "get {source_file} -o {dest_file}; quit"'''
                
                # Execute FTP transfer on VM3 (VM3 downloads from VM2)
                run_ssh_command(VM3_HOST, VM3_USERNAME, ftp_command)
                
                # STEP 5: Verify transfer was successful
                print("🔍 Verifying transfer...")
                transferred_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
                
                if transferred_size != source_size:
                    error_msg = f"Transfer verification failed! Expected: {source_size} bytes, Got: {transferred_size} bytes"
                    print(f"💥 {error_msg}")
                    raise Exception(error_msg)
                
                print(f"🎉 SUCCESS: File transferred successfully ({transferred_size} bytes)")
                processed_files.append(dest_file)
                
            except Exception as e:
                # If any step fails, stop the entire process
                error_msg = f"Transfer failed for {source_file} -> {dest_file}: {str(e)}"
                print(f"💥 {error_msg}")
                raise Exception(error_msg)
        
        # SUMMARY
        print(f"\n{'=' * 60}")
        print(f"🎊 TRANSFER COMPLETED SUCCESSFULLY")
        print(f"📊 Total files processed: {len(processed_files)}")
        print(f"{'=' * 60}")
        
        # RETURN: TaskFlow API automatically stores this in XCom
        # Next tasks can access this data as function parameters
        return processed_files
    
    # =========================================================================
    # TASK 2: PROCESSING ELIGIBILITY CHECK
    # =========================================================================
    
    @task
    def check_processing_eligibility(transferred_files: list):
        """
        TASK 2: Determine which files are eligible for processing
        
        This task implements strict checking:
        - If ANY output file (.dat or .inv) exists, ERROR and stop
        - Only process files with NO existing output files
        - This prevents partial processing and ensures data consistency
        
        Parameters:
            transferred_files (list): Files that were transferred (from previous task)
            
        Returns:
            list: Files that need processing (have no existing output files)
            
        TaskFlow API Magic:
        - The parameter 'transferred_files' automatically gets the return value
          from the previous task (check_and_transfer_files)
        - No need for manual XCom operations!
        """
        print("=" * 60)
        print("🔎 CHECKING PROCESSING ELIGIBILITY")
        print("=" * 60)
        
        # Handle edge case: no files to check
        if not transferred_files:
            print("📝 No files to check for processing eligibility")
            return []
        
        print(f"📋 Checking eligibility for {len(transferred_files)} files")
        
        files_eligible_for_processing = []
        
        # CHECK EACH FILE
        for index, file_path in enumerate(transferred_files):
            print(f"\n{'─' * 40}")
            print(f"🔍 Checking file {index + 1}/{len(transferred_files)}: {file_path}")
            print(f"{'─' * 40}")
            
            try:
                # Generate expected output file names
                # Example: /home/rocky/in/sample1.txt -> /home/rocky/in/sample1
                base_name = file_path.replace('.txt', '')
                dat_file_path = f"{base_name}.dat"
                inv_file_path = f"{base_name}.inv"
                
                print(f"🔍 Checking for: {dat_file_path}")
                print(f"🔍 Checking for: {inv_file_path}")
                
                # Check if output files exist
                dat_exists = get_file_size(VM3_HOST, VM3_USERNAME, dat_file_path) is not None
                inv_exists = get_file_size(VM3_HOST, VM3_USERNAME, inv_file_path) is not None
                
                # STRICT POLICY: If ANY output file exists, don't process
                if dat_exists or inv_exists:
                    # Build detailed error message
                    existing_files = []
                    if dat_exists:
                        existing_files.append(".dat file")
                    if inv_exists:
                        existing_files.append(".inv file")
                    
                    error_msg = f"Cannot process {file_path} because {' and '.join(existing_files)} already exist(s). This indicates previous processing."
                    print(f"🚫 {error_msg}")
                    raise Exception(error_msg)
                
                # No output files exist - eligible for processing
                print("✅ No output files found - ELIGIBLE for processing")
                files_eligible_for_processing.append(file_path)
                
            except Exception as e:
                # If checking fails, treat as ineligible and stop
                error_msg = f"Eligibility check failed for {file_path}: {str(e)}"
                print(f"💥 {error_msg}")
                raise Exception(error_msg)
        
        # SUMMARY
        print(f"\n{'=' * 60}")
        print(f"📊 ELIGIBILITY CHECK COMPLETED")
        print(f"✅ Files eligible for processing: {len(files_eligible_for_processing)}")
        for file_path in files_eligible_for_processing:
            print(f"   📄 {file_path}")
        print(f"{'=' * 60}")
        
        return files_eligible_for_processing
    
    # =========================================================================
    # TASK 3: FILE PROCESSING
    # =========================================================================
    
    @task
    def process_eligible_files(eligible_files: list):
        """
        TASK 3: Process files using the Python script on VM3
        
        This task runs the simple_file_manager.py script for each eligible file.
        The script generates .dat and .inv files based on the input text file.
        
        Parameters:
            eligible_files (list): Files that need processing (from previous task)
            
        Returns:
            dict: Processing results summary
            
        Processing Logic:
        - For each eligible file, run the Python script on VM3
        - The script reads the text file and generates random v/x characters
        - .dat file contains the v/x string
        - .inv file contains lines corresponding to 'v' positions
        """
        print("=" * 60)
        print("⚙️  STARTING FILE PROCESSING")
        print("=" * 60)
        
        # Handle edge case: no files to process
        if not eligible_files:
            print("📝 No files need processing - all files already have output")
            return {"processed": 0, "skipped": len(eligible_files), "status": "completed"}
        
        print(f"⚙️  Processing {len(eligible_files)} eligible files")
        
        # Track processing results
        processed_count = 0
        processing_results = []
        
        # PROCESS EACH FILE
        for index, file_path in enumerate(eligible_files):
            print(f"\n{'─' * 40}")
            print(f"⚙️  Processing file {index + 1}/{len(eligible_files)}: {file_path}")
            print(f"{'─' * 40}")
            
            try:
                # Build command to run the processing script
                # The script takes the file path as a command-line argument
                script_path = f"/home/{VM3_USERNAME}/scripts/simple_file_manager.py"
                processing_command = f"python3 {script_path} {file_path}"
                
                print(f"🐍 Executing Python script: {processing_command}")
                
                # Execute processing script on VM3
                script_output = run_ssh_command(VM3_HOST, VM3_USERNAME, processing_command)
                
                print(f"🎉 Processing completed successfully")
                print(f"📄 Script output: {script_output}")
                
                # Track successful processing
                processed_count += 1
                processing_results.append({
                    "file": file_path,
                    "status": "success",
                    "output": script_output
                })
                
            except Exception as e:
                # If processing fails for any file, stop the entire task
                error_msg = f"Processing failed for {file_path}: {str(e)}"
                print(f"💥 {error_msg}")
                raise Exception(error_msg)
        
        # FINAL SUMMARY
        print(f"\n{'=' * 60}")
        print(f"🎊 FILE PROCESSING COMPLETED SUCCESSFULLY")
        print(f"📊 Files processed: {processed_count}/{len(eligible_files)}")
        print(f"{'=' * 60}")
        
        # Return summary for monitoring
        return {
            "processed": processed_count,
            "total": len(eligible_files),
            "status": "completed",
            "results": processing_results
        }
    
    # =========================================================================
    # TASK DEPENDENCY DEFINITION (TASKFLOW API STYLE)
    # =========================================================================
    # In TaskFlow API, dependencies are defined by function calls and parameters
    # This is much more intuitive than the traditional >> syntax
    
    # STEP 1: Execute file transfer task
    transferred_files = check_and_transfer_files()
    
    # STEP 2: Check processing eligibility (depends on transfer completion)
    # The return value from step 1 is automatically passed as parameter
    eligible_files = check_processing_eligibility(transferred_files)
    
    # STEP 3: Process eligible files (depends on eligibility check)
    # The return value from step 2 is automatically passed as parameter
    final_results = process_eligible_files(eligible_files)
    
    # OPTIONAL: Return overall workflow results
    # This can be useful for monitoring or triggering downstream processes
    return final_results

# =============================================================================
# DAG INSTANTIATION
# =============================================================================
# Create the actual DAG instance
# In TaskFlow API, we call the decorated function to create the DAG

# This line creates the DAG and registers it with Airflow
dag_instance = taskflow_ftp_processing_workflow()

# =============================================================================
# END OF DAG DEFINITION
# =============================================================================

# SUMMARY OF TASKFLOW API BENEFITS DEMONSTRATED:
#
# 1. CLEANER SYNTAX:
#    - No PythonOperator boilerplate
#    - Functions directly become tasks
#    - More readable and maintainable
#
# 2. AUTOMATIC DATA PASSING:
#    - Return values automatically stored in XCom
#    - Parameters automatically retrieve XCom data
#    - No manual xcom_push/xcom_pull operations
#
# 3. INTUITIVE DEPENDENCIES:
#    - Dependencies defined by function calls
#    - More logical than >> syntax
#    - Easier to understand data flow
#
# 4. BETTER TYPE HINTS:
#    - IDE can understand parameter types
#    - Better code completion and error detection
#    - More robust development experience
#
# 5. SIMPLIFIED DEBUGGING:
#    - Standard Python functions
#    - Easier to test individual components
#    - Less Airflow-specific complexity
```

## Key Benefits Demonstrated:

### 1. **Automatic Data Passing:**
```python
# OLD WAY (Manual XCom):
files = context['task_instance'].xcom_pull(task_ids='previous_task')

# NEW WAY (Automatic):
def process_files(files_from_previous_task: list):  # Automatic!
```

### 2. **Cleaner Dependencies:**
```python
# OLD WAY:
task1 >> task2 >> task3

# NEW WAY:
result1 = task1()
result2 = task2(result1)  # More intuitive!
result3 = task3(result2)
```

### 3. **No Boilerplate:**
```python
# OLD WAY:
task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    provide_context=True
)

# NEW WAY:
@task
def my_task():  # That's it!
    pass
```

The TaskFlow API makes Airflow DAGs **much more Pythonic** and **easier to understand**!
