# S12_card_processing_workflow.py
from datetime import datetime, timedelta
import os
import paramiko
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue

# Configuration
VM2_HOST = '192.168.83.132'  # FTP server (source)
VM3_HOST = '192.168.83.133'  # Card1 server (destination/processing)
VM2_USERNAME = 'rocky'
VM3_USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'
FTP_PASSWORD = '111'

# Files to monitor and process
CARD_SOURCE_PATHS = [
    '/home/rocky/card/in/card_batch_001.txt',
    '/home/rocky/card/in/card_batch_002.txt',
    '/home/rocky/card/in/card_batch_003.txt'
]

# Destination paths on VM3 (same structure)
CARD_DEST_PATHS = [
    '/home/rocky/card/in/card_batch_001.txt',
    '/home/rocky/card/in/card_batch_002.txt',
    '/home/rocky/card/in/card_batch_003.txt'
]

# Processing script path on VM3
CARD_PROCESSOR_SCRIPT = '/home/rocky/scripts/card_processor.py'

def ssh_execute(host, user, cmd):
    """Execute command via SSH and return output"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname=host, username=user, key_filename=SSH_KEY, timeout=30)
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            raise Exception(f"Command failed (exit {exit_code}): {error}")
        
        return output
    
    except Exception as e:
        raise Exception(f"SSH error on {host}: {e}")
    
    finally:
        ssh.close()

def get_file_info(host, user, path):
    """Get file size and existence status"""
    try:
        cmd = f"stat -c'%s' {path} 2>/dev/null || echo 'NOT_FOUND'"
        result = ssh_execute(host, user, cmd)
        
        if result == 'NOT_FOUND':
            return None
        
        return int(result)
    except:
        return None

@dag(
    dag_id='S12_card_processing_workflow',
    schedule_interval=None,  # Triggered by sensor
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_tasks=5,  # DAG-level concurrency limit
    default_args={
        'owner': 'rocky',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'queue': 'card_processing_queue'  # Custom queue for all tasks
    },
    tags=['card-processing', 'vm3', 'sensor']
)
def card_processing_workflow():
    
    @task.sensor(
        poke_interval=300,  # Check every 5 minutes
        timeout=7200,       # Timeout after 2 hours
        mode="poke",
        queue='card_processing_queue'
    )
    def detect_card_files():
        """Monitor for card files on VM2"""
        print("=== CHECKING FOR CARD FILES ON VM2 ===")
        
        detected_files = []
        
        for src_path in CARD_SOURCE_PATHS:
            print(f"Checking: {src_path}")
            
            size = get_file_info(VM2_HOST, VM2_USERNAME, src_path)
            if size is not None:
                detected_files.append({
                    'path': src_path,
                    'size': size
                })
                print(f"  ✓ Found: {src_path} ({size} bytes)")
            else:
                print(f"  ✗ Not found: {src_path}")
        
        if detected_files:
            print(f"\nDetected {len(detected_files)} files ready for processing")
            return PokeReturnValue(is_done=True, xcom_value=detected_files)
        else:
            print("No files detected yet, will check again...")
            return PokeReturnValue(is_done=False)
    
    @task(queue='card_processing_queue')
    def transfer_card_files(detected_files: list):
        """Transfer detected files from VM2 to VM3"""
        print("=== TRANSFERRING CARD FILES TO VM3 ===")
        
        transferred_files = []
        
        for file_info in detected_files:
            src_path = file_info['path']
            src_size = file_info['size']
            
            # Find corresponding destination path
            src_index = CARD_SOURCE_PATHS.index(src_path)
            dst_path = CARD_DEST_PATHS[src_index]
            
            print(f"\n--- Transferring: {src_path} ---")
            print(f"Source size: {src_size} bytes")
            
            # Check if file already exists on destination
            dst_size = get_file_info(VM3_HOST, VM3_USERNAME, dst_path)
            
            if dst_size is not None:
                if dst_size == src_size:
                    print("✓ File already exists with same size - skipping transfer")
                    transferred_files.append({
                        'src': src_path,
                        'dst': dst_path,
                        'size': src_size,
                        'transferred': False
                    })
                    continue
                else:
                    raise Exception(f"File exists with different size! Source: {src_size}, Dest: {dst_size}")
            
            # Create destination directory
            dst_dir = os.path.dirname(dst_path)
            ssh_execute(VM3_HOST, VM3_USERNAME, f"mkdir -p {dst_dir}")
            
            # Transfer file using FTP (executed from VM3)
            print("Starting FTP transfer...")
            ftp_cmd = f"lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e 'get {src_path} -o {dst_path}; quit'"
            ssh_execute(VM3_HOST, VM3_USERNAME, ftp_cmd)
            
            # Verify transfer
            transferred_size = get_file_info(VM3_HOST, VM3_USERNAME, dst_path)
            if transferred_size != src_size:
                raise Exception(f"Transfer verification failed! Expected: {src_size}, Got: {transferred_size}")
            
            print(f"✓ Transfer successful: {transferred_size} bytes")
            transferred_files.append({
                'src': src_path,
                'dst': dst_path,
                'size': transferred_size,
                'transferred': True
            })
        
        print(f"\n=== TRANSFER COMPLETED: {len(transferred_files)} files ===")
        return transferred_files
    
    @task(queue='card_processing_queue')
    def check_processing_status(transferred_files: list):
        """Check which files need processing on VM3"""
        print("=== CHECKING PROCESSING STATUS ===")
        
        files_to_process = []
        
        for file_info in transferred_files:
            dst_path = file_info['dst']
            print(f"\n--- Checking: {dst_path} ---")
            
            # Expected output files
            base_name = dst_path.replace('.txt', '')
            processed_file = f"{base_name}.processed"
            report_file = f"{base_name}.report"
            
            # Check if output files exist
            processed_exists = get_file_info(VM3_HOST, VM3_USERNAME, processed_file) is not None
            report_exists = get_file_info(VM3_HOST, VM3_USERNAME, report_file) is not None
            
            if processed_exists and report_exists:
                print("✓ Already processed (output files exist)")
            else:
                print("○ Needs processing")
                files_to_process.append(dst_path)
        
        print(f"\n=== STATUS CHECK COMPLETED: {len(files_to_process)} files need processing ===")
        return files_to_process
    
    @task(queue='card_processing_queue')
    def process_card_files(files_to_process: list):
        """Process card files on VM3"""
        print("=== PROCESSING CARD FILES ON VM3 ===")
        
        if not files_to_process:
            print("No files to process")
            return {"processed": 0, "status": "no_files"}
        
        processed_count = 0
        results = []
        
        for file_path in files_to_process:
            print(f"\n--- Processing: {file_path} ---")
            
            try:
                # Run card processor script on VM3
                cmd = f"python3 {CARD_PROCESSOR_SCRIPT} {file_path}"
                print(f"Executing: {cmd}")
                
                output = ssh_execute(VM3_HOST, VM3_USERNAME, cmd)
                print(f"Processing output: {output}")
                
                processed_count += 1
                results.append({
                    'file': file_path,
                    'status': 'success',
                    'output': output
                })
                
            except Exception as e:
                print(f"✗ Processing failed: {e}")
                results.append({
                    'file': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
                # Continue with other files instead of failing entire task
        
        print(f"\n=== PROCESSING COMPLETED: {processed_count}/{len(files_to_process)} successful ===")
        return {
            "processed": processed_count,
            "total": len(files_to_process),
            "results": results,
            "status": "completed"
        }
    
    @task(queue='card_processing_queue')
    def cleanup_source_files(processing_results: dict, transferred_files: list):
        """Optional: Move or archive processed source files on VM2"""
        print("=== CLEANUP SOURCE FILES ===")
        
        if processing_results['processed'] == 0:
            print("No files were processed successfully, skipping cleanup")
            return
        
        archive_dir = '/home/rocky/card/archive'
        
        # Create archive directory on VM2
        ssh_execute(VM2_HOST, VM2_USERNAME, f"mkdir -p {archive_dir}")
        
        archived_count = 0
        for file_info in transferred_files:
            src_path = file_info['src']
            archive_path = f"{archive_dir}/{os.path.basename(src_path)}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                # Move file to archive
                ssh_execute(VM2_HOST, VM2_USERNAME, f"mv {src_path} {archive_path}")
                print(f"✓ Archived: {src_path} -> {archive_path}")
                archived_count += 1
            except Exception as e:
                print(f"✗ Failed to archive {src_path}: {e}")
        
        print(f"=== CLEANUP COMPLETED: {archived_count} files archived ===")
        return {"archived": archived_count}
    
    # Define workflow
    detected = detect_card_files()
    transferred = transfer_card_files(detected)
    to_process = check_processing_status(transferred)
    results = process_card_files(to_process)
    cleanup = cleanup_source_files(results, transferred)
    
    # Dependencies
    detected >> transferred >> to_process >> results >> cleanup

# Create DAG instance
dag_instance = card_processing_workflow()
