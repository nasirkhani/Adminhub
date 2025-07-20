# simple_taskflow_dag_with_sensor.py
from datetime import datetime, timedelta
import os
import paramiko
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue

# Config (updated from your requirements)
VM2_HOST = '192.168.83.132'
VM3_HOST = '192.168.83.133'
VM2_USERNAME = 'rocky'
VM3_USERNAME = 'rocky'
SSH_KEY = '/home/rocky/.ssh/id_ed25519'
FTP_PASSWORD = '111'

# Files to monitor and process (same files for both sensor and processing)
SOURCE_PATHS = ['/home/rocky/in/sample1.txt', '/home/rocky/bon/in/sample3.txt']
DEST_PATHS = ['/home/rocky/in/sample1.txt', '/home/rocky/bon/in/sample3.txt']

def ssh_run(host, user, cmd):
    """Run SSH command"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, key_filename=SSH_KEY)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode().strip()
    if stdout.channel.recv_exit_status() != 0:
        raise Exception(stderr.read().decode())
    ssh.close()
    return output

def file_size(host, user, path):
    """Get file size or None"""
    try:
        result = ssh_run(host, user, f"stat -c%s {path} 2>/dev/null || echo 'NONE'")
        return None if result == 'NONE' else int(result)
    except:
        return None

@dag(
    dag_id='S06_02_sensor_ftp_processing',
    schedule_interval=None,  # Triggered by sensor
    start_date=datetime(2024, 5, 1),
    catchup=False,
    default_args={'owner': 'rocky', 'retries': 0}
)
def sensor_workflow():
    
    @task.sensor(poke_interval=120, timeout=3600, mode="poke")
    def wait_for_source_files():
        """Check if any source file exists on VM2"""
        detected_files = []
        
        for src_path in SOURCE_PATHS:
            if file_size(VM2_HOST, VM2_USERNAME, src_path) is not None:
                detected_files.append(src_path)
        
        if detected_files:
            print(f"Detected files: {detected_files}")
            return PokeReturnValue(is_done=True, xcom_value=detected_files)
        else:
            print("No source files detected yet")
            return PokeReturnValue(is_done=False)
    
    @task
    def transfer_detected_files(detected_files: list):
        """Transfer only the detected files"""
        transferred = []
        
        for src_path in detected_files:
            # Find corresponding destination path
            src_index = SOURCE_PATHS.index(src_path)
            dst_path = DEST_PATHS[src_index]
            
            # Check sizes
            src_size = file_size(VM2_HOST, VM2_USERNAME, src_path)
            dst_size = file_size(VM3_HOST, VM3_USERNAME, dst_path)
            
            if dst_size == src_size:
                transferred.append(dst_path)
                continue
            elif dst_size is not None:
                raise Exception(f"Size mismatch: {src_path}")
            
            # Transfer
            ssh_run(VM3_HOST, VM3_USERNAME, f"mkdir -p {os.path.dirname(dst_path)}")
            ftp_cmd = f"lftp -u {VM2_USERNAME},{FTP_PASSWORD} {VM2_HOST} -e 'get {src_path} -o {dst_path}; quit'"
            ssh_run(VM3_HOST, VM3_USERNAME, ftp_cmd)
            transferred.append(dst_path)
        
        return transferred
    
    @task
    def check_processing(files: list):
        """Check if processing needed"""
        for f in files:
            base = f.replace('.txt', '')
            dat_exists = file_size(VM3_HOST, VM3_USERNAME, f"{base}.dat") is not None
            inv_exists = file_size(VM3_HOST, VM3_USERNAME, f"{base}.inv") is not None
            
            if dat_exists or inv_exists:
                raise Exception(f"Output files exist for {f}")
        
        return files
    
    @task
    def process_files(files: list):
        """Process files"""
        for f in files:
            cmd = f"python3 /home/{VM3_USERNAME}/scripts/simple_file_manager.py {f}"
            ssh_run(VM3_HOST, VM3_USERNAME, cmd)
        
        return len(files)
    
    # Workflow: sensor detects -> transfer -> check -> process
    detected = wait_for_source_files()
    transferred = transfer_detected_files(detected)
    checked = check_processing(transferred)
    result = process_files(checked)
    
    return result

# Create DAG
dag_instance = sensor_workflow()
