# taskflow_ftp_processing_dag.py
from datetime import datetime, timedelta
import os
import paramiko
from airflow.decorators import dag, task

# Configuration
VM2_HOST = '192.168.83.132'
VM3_HOST = '192.168.83.133'
VM2_USERNAME = 'rocky'
VM3_USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'
FTP_PASSWORD = '111'

# Source and destination mapping (same index = paired files)
SOURCE_PATHS = [
    '/home/rocky/in/sample1.txt',
    '/home/rocky/bon/in/sample3.txt', 
    '/home/rocky/card/in/sample2.txt'
]

DESTINATION_PATHS = [
    '/home/rocky/in/sample1.txt',
    '/home/rocky/bon/in/sample3.txt',
    '/home/rocky/card/in/sample2.txt'
]

def run_ssh_command(host, username, command):
    """Execute command on remote host via SSH"""
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
    """Get file size on remote host, return None if not exists"""
    try:
        command = f"stat -c%s {file_path} 2>/dev/null || echo 'FILE_NOT_FOUND'"
        result = run_ssh_command(host, username, command)
        
        if result == 'FILE_NOT_FOUND':
            return None
        
        return int(result)
    except:
        return None

@dag(
    dag_id='taskflow_ftp_processing',
    description='File processing using TaskFlow API',
    schedule_interval=None,
    start_date=datetime(2024, 5, 1),
    catchup=False,
    default_args={
        'owner': 'rocky',
        'retries': 0,
    },
    tags=['taskflow', 'ftp', 'file-processing']
)
def taskflow_ftp_processing_workflow():
    """Main DAG function defining the workflow"""
    
    @task
    def check_and_transfer_files():
        """Transfer files via FTP with size checking"""
        print("=== STARTING FILE TRANSFER ===")
        
        # Validate configuration
        if len(SOURCE_PATHS) != len(DESTINATION_PATHS):
            raise Exception(f"Source and destination lists must have same length")
        
        processed_files = []
        
        # Process each source-destination pair
        for i in range(len(SOURCE_PATHS)):
            source_file = SOURCE_PATHS[i]
            dest_file = DESTINATION_PATHS[i]
            
            print(f"\n--- Processing {i+1}/{len(SOURCE_PATHS)}: {source_file} ---")
            
            try:
                # Check source file exists
                source_size = get_file_size(VM2_HOST, VM2_USERNAME, source_file)
                if source_size is None:
                    raise Exception(f"Source file not found: {source_file}")
                
                # Check destination file
                dest_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
                
                if dest_size is not None:
                    if dest_size == source_size:
                        print("✓ Same size - skipping transfer")
                        processed_files.append(dest_file)
                        continue
                    else:
                        raise Exception(f"Size mismatch: source={source_size}, dest={dest_size}")
                
                # Create destination directory
                dest_dir = os.path.dirname(dest_file)
                run_ssh_command(VM3_HOST, VM3_USERNAME, f"mkdir -p {dest_dir}")
                
                # Transfer via FTP
                ftp_cmd = f'''lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e "get {source_file} -o {dest_file}; quit"'''
                run_ssh_command(VM3_HOST, VM3_USERNAME, ftp_cmd)
                
                # Verify transfer
                transferred_size = get_file_size(VM3_HOST, VM3_USERNAME, dest_file)
                if transferred_size != source_size:
                    raise Exception(f"Transfer failed: expected {source_size}, got {transferred_size}")
                
                print(f"✓ Transfer successful: {transferred_size} bytes")
                processed_files.append(dest_file)
                
            except Exception as e:
                raise Exception(f"Transfer failed for {source_file}: {e}")
        
        print(f"=== TRANSFER COMPLETED: {len(processed_files)} files ===")
        return processed_files
    
    @task
    def check_processing_eligibility(transferred_files: list):
        """Check which files need processing (no existing .dat/.inv files)"""
        print("=== CHECKING PROCESSING ELIGIBILITY ===")
        
        if not transferred_files:
            return []
        
        files_eligible = []
        
        for i, file_path in enumerate(transferred_files):
            print(f"\n--- Checking {i+1}/{len(transferred_files)}: {file_path} ---")
            
            # Generate output file names
            base_name = file_path.replace('.txt', '')
            dat_file = f"{base_name}.dat"
            inv_file = f"{base_name}.inv"
            
            # Check if ANY output file exists
            dat_exists = get_file_size(VM3_HOST, VM3_USERNAME, dat_file) is not None
            inv_exists = get_file_size(VM3_HOST, VM3_USERNAME, inv_file) is not None
            
            if dat_exists or inv_exists:
                # If ANY output exists, raise error
                existing = []
                if dat_exists:
                    existing.append(".dat")
                if inv_exists:
                    existing.append(".inv")
                
                error_msg = f"Output files already exist: {', '.join(existing)}"
                raise Exception(error_msg)
            
            print("✓ No output files - eligible for processing")
            files_eligible.append(file_path)
        
        print(f"=== ELIGIBILITY CHECK COMPLETED: {len(files_eligible)} eligible ===")
        return files_eligible
    
    @task
    def process_eligible_files(eligible_files: list):
        """Process files using Python script on VM3"""
        print("=== STARTING FILE PROCESSING ===")
        
        if not eligible_files:
            print("No files to process")
            return {"processed": 0, "status": "completed"}
        
        processed_count = 0
        
        for i, file_path in enumerate(eligible_files):
            print(f"\n--- Processing {i+1}/{len(eligible_files)}: {file_path} ---")
            
            try:
                # Run processing script
                script_cmd = f"python3 /home/{VM3_USERNAME}/scripts/simple_file_manager.py {file_path}"
                result = run_ssh_command(VM3_HOST, VM3_USERNAME, script_cmd)
                
                print(f"✓ Processing successful: {result}")
                processed_count += 1
                
            except Exception as e:
                raise Exception(f"Processing failed for {file_path}: {e}")
        
        print(f"=== PROCESSING COMPLETED: {processed_count}/{len(eligible_files)} files ===")
        return {"processed": processed_count, "total": len(eligible_files), "status": "completed"}
    
    # Define task dependencies using TaskFlow API
    transferred_files = check_and_transfer_files()
    eligible_files = check_processing_eligibility(transferred_files)
    final_results = process_eligible_files(eligible_files)
    
    return final_results

# Create DAG instance
dag_instance = taskflow_ftp_processing_workflow()
