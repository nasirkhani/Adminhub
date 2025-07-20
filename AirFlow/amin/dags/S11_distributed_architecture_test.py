from datetime import datetime, timedelta
from airflow.decorators import dag, task
import socket
import os
import subprocess

@dag(
    dag_id='S11_distributed_architecture_test',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        'owner': 'rocky',
        'retries': 0
    }
)
def distributed_architecture_test():
    
    @task
    def show_worker_info():
        """Display information about the worker executing this task"""
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        # Get worker process info
        pid = os.getpid()
        uid = os.getuid()
        
        # Check if logs directory is accessible
        log_dir = '/home/rocky/airflow/logs'
        log_accessible = os.path.exists(log_dir) and os.access(log_dir, os.W_OK)
        
        return {
            'worker_hostname': hostname,
            'worker_ip': ip,
            'process_id': pid,
            'user_id': uid,
            'airflow_home': os.environ.get('AIRFLOW_HOME', 'Not set'),
            'python_path': os.environ.get('PYTHONPATH', 'Not set'),
            'logs_writable': log_accessible,
            'current_directory': os.getcwd()
        }
    
    @task
    def check_nfs_mount():
        """Verify NFS mount is working"""
        dags_path = '/home/rocky/airflow/dags'
        
        # List files in DAGs folder
        try:
            files = os.listdir(dags_path)
            dag_files = [f for f in files if f.endswith('.py')]
            
            # Check if this DAG file exists
            this_dag = 'S11_distributed_architecture_test.py'
            has_this_dag = this_dag in dag_files
            
            return {
                'nfs_mounted': True,
                'dags_path': dags_path,
                'total_files': len(files),
                'dag_files': len(dag_files),
                'has_this_dag': has_this_dag,
                'mount_info': subprocess.check_output(['mount | grep airflow'], shell=True).decode().strip()
            }
        except Exception as e:
            return {
                'nfs_mounted': False,
                'error': str(e)
            }
    
    @task
    def test_ssh_connections():
        """Test SSH connectivity to all target VMs"""
        import sys
        sys.path.insert(0, '/home/rocky/airflow')
        
        results = {}
        
        try:
            from utils.simple_ssh import execute_ssh_command
            
            # Test SSH to each configured VM
            from config.simple_vms import TARGET_VMS
            
            for vm_name, vm_config in TARGET_VMS.items():
                try:
                    result = execute_ssh_command(vm_name, 'hostname')
                    results[vm_name] = {
                        'success': True,
                        'hostname': result['output'],
                        'host': vm_config['host']
                    }
                except Exception as e:
                    results[vm_name] = {
                        'success': False,
                        'error': str(e),
                        'host': vm_config['host']
                    }
                    
        except Exception as e:
            results['import_error'] = str(e)
            
        return results
    
    @task
    def verify_log_server():
        """Check if log server is running on port 8793"""
        try:
            # Check if port 8793 is listening
            result = subprocess.check_output(['ss', '-tln', '| grep :8793'], shell=True).decode()
            
            return {
                'log_server_running': True,
                'port_info': result.strip()
            }
        except:
            return {
                'log_server_running': False,
                'message': 'Port 8793 not listening'
            }
    
    @task
    def summarize_results(worker_info, nfs_info, ssh_results, log_server):
        """Summarize all test results"""
        print("=== DISTRIBUTED ARCHITECTURE TEST RESULTS ===")
        
        print(f"\n1. WORKER INFORMATION:")
        print(f"   - Hostname: {worker_info['worker_hostname']}")
        print(f"   - IP: {worker_info['worker_ip']}")
        print(f"   - Logs writable: {worker_info['logs_writable']}")
        
        print(f"\n2. NFS MOUNT STATUS:")
        print(f"   - Mounted: {nfs_info.get('nfs_mounted', False)}")
        print(f"   - DAG files found: {nfs_info.get('dag_files', 0)}")
        
        print(f"\n3. SSH CONNECTIVITY:")
        for vm, result in ssh_results.items():
            if vm != 'import_error':
                status = "✓" if result.get('success') else "✗"
                print(f"   - {vm} ({result.get('host')}): {status}")
        
        print(f"\n4. LOG SERVER:")
        print(f"   - Running: {log_server['log_server_running']}")
        
        return "Test completed"
    
    # Execute tests
    worker = show_worker_info()
    nfs = check_nfs_mount()
    ssh = test_ssh_connections()
    logs = verify_log_server()
    
    summary = summarize_results(worker, nfs, ssh, logs)
    
    [worker, nfs, ssh, logs] >> summary

dag = distributed_architecture_test()
