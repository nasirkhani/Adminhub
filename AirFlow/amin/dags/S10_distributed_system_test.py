from datetime import datetime
from airflow.decorators import dag, task
import socket

@dag(
    dag_id='S10_distributed_system_test',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={'owner': 'rocky'}
)
def test_distributed():
    
    @task
    def identify_worker():
        """Shows which worker is running this task"""
        return {
            'hostname': socket.gethostname(),
            'ip': socket.gethostbyname(socket.gethostname()),
            'message': 'Task executed successfully'
        }
    
    @task
    def test_ssh_to_vm3():
        """Test SSH to target VM"""
        import sys
        sys.path.insert(0, '/home/rocky/airflow')
        from utils.simple_ssh import execute_ssh_command
        
        result = execute_ssh_command('vm1', 'hostname')
        return f"SSH Result: {result}"
    
    worker_info = identify_worker()
    ssh_result = test_ssh_to_vm3()
    
    worker_info >> ssh_result

dag = test_distributed()
