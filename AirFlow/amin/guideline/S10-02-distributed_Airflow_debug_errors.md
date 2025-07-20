## Issue 1: Firewall Ports Configuration

you need specific ports open on each VM based on their roles:

### VM1 (Main Airflow - 192.168.83.129):
```bash
# These services need to be accessible from other VMs
sudo firewall-cmd --add-port=5432/tcp --permanent  # PostgreSQL (for VM2, VM4)
sudo firewall-cmd --add-port=5672/tcp --permanent  # RabbitMQ (for VM2, VM4)
sudo firewall-cmd --add-port=15672/tcp --permanent # RabbitMQ Management
sudo firewall-cmd --add-port=8080/tcp --permanent  # Webserver (external access)
sudo firewall-cmd --add-port=5555/tcp --permanent  # Flower (external access)
sudo firewall-cmd --reload
```

### VM2 (NFS + DAG Processor - 192.168.83.132):
```bash
# NFS and FTP services
sudo firewall-cmd --add-service=nfs --permanent
sudo firewall-cmd --add-service=rpc-bind --permanent
sudo firewall-cmd --add-service=mountd --permanent
sudo firewall-cmd --add-port=21/tcp --permanent    # FTP
sudo firewall-cmd --reload
```

### VM4 (Worker - 192.168.83.131):
```bash
# Worker needs to serve logs
sudo firewall-cmd --add-port=8793/tcp --permanent  # Log server
sudo firewall-cmd --reload
```

## Issue 2: Fix Permission Error on VM4

The systemd service can't execute the airflow binary. Let's fix it:

```bash
# On VM4
# Check if airflow exists and is executable
ls -la /home/rocky/.local/bin/airflow
which airflow

# If using pip install --user, the path might be different
find /home -name airflow -type f 2>/dev/null

# Update the systemd service with the correct path
sudo vi /etc/systemd/system/airflow-worker.service
```

Update the ExecStart line with the full path found above, or use the shell to find it:
```ini
[Unit]
Description=Airflow Celery Worker
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/bin/bash -c 'exec /home/rocky/.local/bin/airflow celery worker --queues remote_tasks,default --concurrency 4'
Restart=on-failure
RestartSec=10s
SyslogIdentifier=airflow-worker

[Install]
WantedBy=multi-user.target
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-worker
sudo systemctl status airflow-worker
```

## Issue 3: Fix Log Serving

The worker needs to serve logs on port 8793. The error "Name or service not known" means the webserver can't resolve the worker's hostname.

### Step 1: Update /etc/hosts on VM1
```bash
# On VM1 (Main Airflow)
sudo vi /etc/hosts
```

Add:
```
192.168.83.131 worker1
192.168.83.132 ftp
192.168.83.133 card1
```

### Step 2: Configure Worker Hostname in airflow.cfg on VM4
```bash
# On VM4
vi ~/airflow/airflow.cfg
```

Add/update:
```ini
[logging]
remote_logging = False
remote_base_log_folder = 
remote_log_conn_id = 
hostname_callable = socket.getfqdn

[celery]
worker_log_server_port = 8793
```

### Step 3: Ensure Log Directory Exists
```bash
# On VM4
mkdir -p ~/airflow/logs
chmod 755 ~/airflow/logs
```

## Issue 4: Rename DAG to Follow Convention

Update the test DAG on VM2:
```bash
# On VM2
cd /srv/airflow/dags
mv distributed_test_dag.py S10_distributed_system_test.py
vi S10_distributed_system_test.py
```

Update the dag_id in the file:
```python
@dag(
    dag_id='S10_distributed_system_test',  # Changed from 'distributed_system_test'
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={'owner': 'rocky'}
)
```

## Issue 5: Create a New Test DAG (S11)

Let's create a comprehensive test DAG that shows the distributed architecture:

```bash
# On VM2
vi /srv/airflow/dags/S11_distributed_architecture_test.py
```

```python
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
```

## How Logs Work in Distributed Airflow

### Log Flow:
1. **Task Execution**: Worker writes logs locally to `~/airflow/logs/`
2. **Log Serving**: Worker runs a small HTTP server on port 8793
3. **Web UI Request**: When you view logs, webserver connects to `worker1:8793`
4. **Log Retrieval**: Webserver fetches logs from worker's HTTP server

### The Problem:
- Webserver couldn't resolve hostname "worker1"
- Port 8793 might be blocked by firewall
- Worker's log directory might not be accessible

## Final Verification Steps

After making all changes:

```bash
# On VM1 - Test hostname resolution
ping worker1
curl http://worker1:8793/log/test

# On VM4 - Check log server
sudo ss -tlnp | grep 8793
ls -la ~/airflow/logs/

# Restart all services
# VM1:
sudo systemctl restart airflow-scheduler airflow-webserver

# VM2:
sudo systemctl restart airflow-dag-processor

# VM4:
sudo systemctl restart airflow-worker
```

Then trigger the `S11_distributed_architecture_test` DAG to verify everything is working!



===================================================================================================


You're absolutely right! The DAG processor needs to have all the dependencies that your DAGs use, including `paramiko` and `apache-airflow-providers-ssh`. Let me fix both issues.

## Issue 1: Install Missing Dependencies on VM2

On VM2 (NFS + DAG Processor), install the missing packages:

```bash
# On VM2
cd ~/airflow

# Install SSH provider and paramiko with constraints
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# Install the SSH provider (this will also install paramiko as a dependency)
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"

# Verify installation
pip3 list | grep -E "ssh|paramiko"
```

You should see:
- `apache-airflow-providers-ssh 4.0.0`
- `paramiko` (version from constraint file)
- `sshtunnel` (version from constraint file)

## Issue 2: Fix DAG Processor SystemD Service

The service is failing because the environment isn't properly set. Let's update the service file:

```bash
# On VM2
sudo vi /etc/systemd/system/airflow-dag-processor.service
```

Replace with this improved version:

```ini
[Unit]
Description=Airflow Standalone DAG Processor
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment="AIRFLOW_HOME=/home/rocky/airflow"
Environment="PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/rocky/airflow:/home/rocky/.local/lib/python3.9/site-packages"
Environment="LANG=en_US.UTF-8"
Environment="LC_ALL=en_US.UTF-8"
WorkingDirectory=/home/rocky/airflow

# Use bash to ensure proper environment loading
ExecStart=/bin/bash -c 'source /home/rocky/.bashrc && exec /home/rocky/.local/bin/airflow dag-processor'

Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airflow-dag-processor

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

Now reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-dag-processor
sudo systemctl status airflow-dag-processor

# Check logs
sudo journalctl -u airflow-dag-processor -f
```

## Additional Dependencies Check

Let's also make sure VM2 has all the Python modules that your DAGs might need:

```bash
# On VM2
# Copy Python modules from VM1 (if not already done)
rsync -av rocky@192.168.83.129:/home/rocky/airflow/config/ ~/airflow/config/
rsync -av rocky@192.168.83.129:/home/rocky/airflow/utils/ ~/airflow/utils/

# Create __init__.py files
touch ~/airflow/__init__.py
touch ~/airflow/config/__init__.py
touch ~/airflow/utils/__init__.py

# Test import
python3 -c "import sys; sys.path.insert(0, '/home/rocky/airflow'); from utils.simple_ssh import execute_ssh_command; print('Imports OK')"
```

## Complete Dependency List for VM2

To ensure the DAG processor can parse all DAGs, install these on VM2:

```bash
# Install all common Airflow providers that your DAGs might use
pip3 install "apache-airflow-providers-ssh==4.0.0" \
             "apache-airflow-providers-http" \
             "apache-airflow-providers-ftp" \
             "paramiko" \
             --constraint "${CONSTRAINT_URL}"
```

## Verify DAG Processor is Working

After making these changes:

```bash
# Check if service is running
sudo systemctl status airflow-dag-processor

# Check if it's processing DAGs
sudo journalctl -u airflow-dag-processor | grep -i "processing.*dag"

# Check for any remaining import errors
sudo journalctl -u airflow-dag-processor | grep -i "error"

# Verify it's updating the database
# On VM1, check serialized DAGs
airflow dags list
```

## Alternative: Debug Mode

If the service still has issues, let's run it in debug mode first:

```bash
# Stop the service
sudo systemctl stop airflow-dag-processor

# Run manually with verbose logging
cd ~/airflow
export AIRFLOW__LOGGING__LOGGING_LEVEL=DEBUG
/home/rocky/.local/bin/airflow dag-processor -v
```

This will show detailed information about what's happening and help identify any remaining issues.

## Note About DAG Dependencies

The DAG processor needs to be able to import and parse all DAGs, which means:
1. It needs all Python packages that any DAG imports
2. It needs access to custom modules (config/, utils/)
3. It needs the same Python path configuration as workers

If you add new dependencies to your DAGs in the future, remember to also install them on VM2 where the DAG processor runs.
