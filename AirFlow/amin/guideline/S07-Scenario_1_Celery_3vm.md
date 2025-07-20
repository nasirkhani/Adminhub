# Scenario 1: Single Machine Celery with SSH-Based Remote Execution

Based on your setup with systemd services and 3 target VMs, here's the complete solution for **Scenario 1** (everything on the main Airflow machine).

## Part 1: VM Configuration and Queue Strategy

### Step 1: Define Target VM Configuration

Create `~/airflow/config/target_vms.py`:

```python
# target_vms.py - Configuration for target VMs

# Target VM definitions with queue mapping
TARGET_VMS = {
    'vm1': {
        'host': '192.168.83.131',
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519',
        'queue': 'vm1_queue',
        'description': 'Target VM 1'
    },
    'vm2': {
        'host': '192.168.83.132', 
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519',
        'queue': 'vm2_queue',
        'description': 'Target VM 2'
    },
    'vm3': {
        'host': '192.168.83.133',
        'username': 'rocky', 
        'ssh_key': '/home/rocky/.ssh/id_ed25519',
        'queue': 'vm3_queue',
        'description': 'Target VM 3'
    }
}

# Queue definitions for different purposes
SPECIALIZED_QUEUES = {
    'vm1_queue': 'Tasks for VM1 (192.168.83.131)',
    'vm2_queue': 'Tasks for VM2 (192.168.83.132)', 
    'vm3_queue': 'Tasks for VM3 (192.168.83.133)',
    'all_vms_queue': 'Tasks that can run on any VM',
    'file_transfer_queue': 'File transfer tasks between VMs',
    'default': 'Default queue for local tasks'
}

# SSH connection settings
SSH_TIMEOUT = 30
MAX_RETRIES = 3
```

### Step 2: Create SSH Execution Utilities

Create `~/airflow/utils/ssh_executor.py`:

```python
# ssh_executor.py - SSH execution utilities for Celery tasks

import paramiko
import threading
import time
from typing import Dict, Any, Optional

class SSHExecutor:
    """Handles SSH connections and command execution for Celery tasks"""
    
    def __init__(self):
        self._connections = {}  # Cache connections
        self._locks = {}       # Thread locks per host
    
    def execute_command(self, host: str, username: str, ssh_key: str, 
                       command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute command on remote host via SSH"""
        
        # Get or create lock for this host
        if host not in self._locks:
            self._locks[host] = threading.Lock()
        
        with self._locks[host]:
            try:
                # Create SSH connection
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host,
                    username=username, 
                    key_filename=ssh_key,
                    timeout=timeout
                )
                
                # Execute command
                stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
                
                # Get results
                output = stdout.read().decode('utf-8').strip()
                error = stderr.read().decode('utf-8').strip() 
                exit_code = stdout.channel.recv_exit_status()
                
                # Close connection
                ssh.close()
                
                # Return structured result
                return {
                    'host': host,
                    'command': command,
                    'exit_code': exit_code,
                    'output': output,
                    'error': error,
                    'success': exit_code == 0,
                    'timestamp': time.time()
                }
                
            except Exception as e:
                return {
                    'host': host,
                    'command': command,
                    'exit_code': -1,
                    'output': '',
                    'error': str(e),
                    'success': False,
                    'timestamp': time.time()
                }

# Global SSH executor instance
ssh_executor = SSHExecutor()
```

## Part 2: Celery Tasks for SSH Execution

### Step 3: Create SSH-Based Celery Tasks

Create `~/airflow/tasks/remote_tasks.py`:

```python
# remote_tasks.py - Celery tasks for remote VM execution

from celery import Celery
from airflow.utils.ssh_executor import ssh_executor
from airflow.config.target_vms import TARGET_VMS
import json

# Initialize Celery app (uses existing Airflow Celery configuration)
app = Celery('remote_tasks')
app.config_from_object('airflow.providers.celery.executors.default_celery')

@app.task(bind=True, name='remote_tasks.execute_on_vm')
def execute_on_vm(self, vm_name: str, command: str) -> dict:
    """Execute command on specific target VM"""
    
    if vm_name not in TARGET_VMS:
        raise ValueError(f"Unknown VM: {vm_name}")
    
    vm_config = TARGET_VMS[vm_name]
    
    try:
        result = ssh_executor.execute_command(
            host=vm_config['host'],
            username=vm_config['username'],
            ssh_key=vm_config['ssh_key'],
            command=command
        )
        
        if not result['success']:
            # Log error but don't raise exception (let Airflow handle retries)
            self.retry(countdown=60, max_retries=3)
        
        return result
        
    except Exception as e:
        # Celery task failure
        raise self.retry(exc=e, countdown=60, max_retries=3)

@app.task(bind=True, name='remote_tasks.execute_on_all_vms')
def execute_on_all_vms(self, command: str) -> dict:
    """Execute command on all target VMs"""
    
    results = {}
    
    for vm_name, vm_config in TARGET_VMS.items():
        try:
            result = ssh_executor.execute_command(
                host=vm_config['host'],
                username=vm_config['username'],
                ssh_key=vm_config['ssh_key'], 
                command=command
            )
            results[vm_name] = result
            
        except Exception as e:
            results[vm_name] = {
                'host': vm_config['host'],
                'success': False,
                'error': str(e),
                'command': command
            }
    
    return results

@app.task(bind=True, name='remote_tasks.file_transfer')
def file_transfer(self, source_vm: str, dest_vm: str, source_path: str, dest_path: str) -> dict:
    """Transfer file between VMs using SCP"""
    
    if source_vm not in TARGET_VMS or dest_vm not in TARGET_VMS:
        raise ValueError("Invalid VM names")
    
    source_config = TARGET_VMS[source_vm]
    dest_config = TARGET_VMS[dest_vm]
    
    # Build SCP command
    scp_command = (
        f"scp -i {source_config['ssh_key']} "
        f"{source_config['username']}@{source_config['host']}:{source_path} "
        f"{dest_config['username']}@{dest_config['host']}:{dest_path}"
    )
    
    # Execute SCP from Airflow machine
    import subprocess
    try:
        result = subprocess.run(
            scp_command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300
        )
        
        return {
            'source_vm': source_vm,
            'dest_vm': dest_vm,
            'source_path': source_path,
            'dest_path': dest_path,
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
        
    except Exception as e:
        raise self.retry(exc=e, countdown=60, max_retries=3)

@app.task(bind=True, name='remote_tasks.check_vm_status')
def check_vm_status(self, vm_name: str) -> dict:
    """Check status of specific VM"""
    
    if vm_name not in TARGET_VMS:
        raise ValueError(f"Unknown VM: {vm_name}")
    
    vm_config = TARGET_VMS[vm_name]
    
    # Execute multiple system commands
    commands = {
        'hostname': 'hostname',
        'uptime': 'uptime',
        'disk_usage': 'df -h /',
        'memory': 'free -m',
        'load': 'cat /proc/loadavg'
    }
    
    results = {}
    
    for check_name, command in commands.items():
        try:
            result = ssh_executor.execute_command(
                host=vm_config['host'],
                username=vm_config['username'],
                ssh_key=vm_config['ssh_key'],
                command=command
            )
            results[check_name] = result
            
        except Exception as e:
            results[check_name] = {
                'success': False,
                'error': str(e)
            }
    
    return {
        'vm_name': vm_name,
        'host': vm_config['host'],
        'checks': results,
        'overall_status': all(r.get('success', False) for r in results.values())
    }
```

## Part 3: Update Systemd Services for Queue Management

### Step 4: Modify Celery Worker Services

Since you already have systemd services, we need to update them to handle different queues:

**Update the existing worker service:**

```bash
# Stop current worker
sudo systemctl stop airflow-celery-worker

# Edit the service file
sudo nano /etc/systemd/system/airflow-celery-worker.service
```

**Replace with multiple queue workers:**

Create `/etc/systemd/system/airflow-worker-vm1.service`:

```ini
[Unit]
Description=Airflow Celery Worker for VM1 Queue
After=network.target airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
ExecStart=/home/rocky/.local/bin/celery -A airflow.tasks.remote_tasks worker --queues vm1_queue,default --hostname vm1_worker --concurrency 2
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-worker-vm1
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/airflow-worker-vm2.service`:

```ini
[Unit]
Description=Airflow Celery Worker for VM2 Queue
After=network.target airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
ExecStart=/home/rocky/.local/bin/celery -A airflow.tasks.remote_tasks worker --queues vm2_queue,default --hostname vm2_worker --concurrency 2
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-worker-vm2
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/airflow-worker-vm3.service`:

```ini
[Unit]
Description=Airflow Celery Worker for VM3 Queue
After=network.target airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
ExecStart=/home/rocky/.local/bin/celery -A airflow.tasks.remote_tasks worker --queues vm3_queue,default --hostname vm3_worker --concurrency 2
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-worker-vm3
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/airflow-worker-general.service`:

```ini
[Unit]
Description=Airflow Celery Worker for General Tasks
After=network.target airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
ExecStart=/home/rocky/.local/bin/celery -A airflow.tasks.remote_tasks worker --queues all_vms_queue,file_transfer_queue,default --hostname general_worker --concurrency 3
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-worker-general
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

**Enable and start the new services:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start new workers
sudo systemctl enable airflow-worker-vm1 airflow-worker-vm2 airflow-worker-vm3 airflow-worker-general
sudo systemctl start airflow-worker-vm1 airflow-worker-vm2 airflow-worker-vm3 airflow-worker-general

# Check status
sudo systemctl status airflow-worker-vm1
sudo systemctl status airflow-worker-vm2
sudo systemctl status airflow-worker-vm3
sudo systemctl status airflow-worker-general
```

## Part 4: TaskFlow DAGs for Remote Execution

### Step 5: Create Remote Execution DAGs

Create `~/airflow/dags/remote_execution_dag.py`:

```python
# remote_execution_dag.py - TaskFlow DAG for remote VM execution

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from celery import Celery
from airflow.config.target_vms import TARGET_VMS

# Initialize Celery app for task submission
celery_app = Celery('remote_tasks')
celery_app.config_from_object('airflow.providers.celery.executors.default_celery')

@dag(
    dag_id='remote_vm_execution',
    schedule_interval=None,
    start_date=datetime(2024, 5, 1),
    catchup=False,
    default_args={'owner': 'rocky', 'retries': 0}
)
def remote_vm_workflow():
    
    @task
    def check_all_vms():
        """Check status of all target VMs"""
        results = {}
        
        for vm_name in TARGET_VMS.keys():
            # Send task to appropriate queue
            queue_name = TARGET_VMS[vm_name]['queue']
            
            task_result = celery_app.send_task(
                'remote_tasks.check_vm_status',
                args=[vm_name],
                queue=queue_name
            )
            
            # Wait for result
            result = task_result.get(timeout=60)
            results[vm_name] = result
        
        return results
    
    @task
    def execute_on_specific_vm(vm_name: str, command: str):
        """Execute command on specific VM"""
        queue_name = TARGET_VMS[vm_name]['queue']
        
        task_result = celery_app.send_task(
            'remote_tasks.execute_on_vm',
            args=[vm_name, command],
            queue=queue_name
        )
        
        return task_result.get(timeout=120)
    
    @task
    def parallel_execution():
        """Execute different commands on different VMs in parallel"""
        tasks = [
            ('vm1', 'hostname && date'),
            ('vm2', 'df -h'),
            ('vm3', 'ps aux | wc -l')
        ]
        
        # Submit all tasks
        task_results = []
        for vm_name, command in tasks:
            queue_name = TARGET_VMS[vm_name]['queue']
            
            task_result = celery_app.send_task(
                'remote_tasks.execute_on_vm',
                args=[vm_name, command],
                queue=queue_name
            )
            task_results.append((vm_name, task_result))
        
        # Collect all results
        results = {}
        for vm_name, task_result in task_results:
            results[vm_name] = task_result.get(timeout=120)
        
        return results
    
    @task
    def file_transfer_test():
        """Test file transfer between VMs"""
        # Create test file on VM1
        create_task = celery_app.send_task(
            'remote_tasks.execute_on_vm',
            args=['vm1', 'echo "test content $(date)" > /tmp/test_file.txt'],
            queue='vm1_queue'
        )
        create_result = create_task.get(timeout=60)
        
        if not create_result['success']:
            raise Exception(f"Failed to create test file: {create_result['error']}")
        
        # Transfer file from VM1 to VM2
        transfer_task = celery_app.send_task(
            'remote_tasks.file_transfer',
            args=['vm1', 'vm2', '/tmp/test_file.txt', '/tmp/received_file.txt'],
            queue='file_transfer_queue'
        )
        transfer_result = transfer_task.get(timeout=180)
        
        # Verify file on VM2
        verify_task = celery_app.send_task(
            'remote_tasks.execute_on_vm',
            args=['vm2', 'cat /tmp/received_file.txt'],
            queue='vm2_queue'
        )
        verify_result = verify_task.get(timeout=60)
        
        return {
            'create': create_result,
            'transfer': transfer_result, 
            'verify': verify_result
        }
    
    @task
    def cleanup_test_files():
        """Clean up test files on all VMs"""
        cleanup_command = 'rm -f /tmp/test_file.txt /tmp/received_file.txt'
        
        results = {}
        for vm_name in ['vm1', 'vm2']:
            queue_name = TARGET_VMS[vm_name]['queue']
            
            task_result = celery_app.send_task(
                'remote_tasks.execute_on_vm',
                args=[vm_name, cleanup_command],
                queue=queue_name
            )
            results[vm_name] = task_result.get(timeout=60)
        
        return results
    
    # Define workflow
    vm_status = check_all_vms()
    
    # Specific VM tasks
    vm1_task = execute_on_specific_vm('vm1', 'hostname && uptime')
    vm2_task = execute_on_specific_vm('vm2', 'df -h /')
    vm3_task = execute_on_specific_vm('vm3', 'free -m')
    
    # Parallel execution
    parallel_results = parallel_execution()
    
    # File transfer workflow
    transfer_results = file_transfer_test()
    cleanup_results = cleanup_test_files()
    
    # Set dependencies
    vm_status >> [vm1_task, vm2_task, vm3_task] >> parallel_results >> transfer_results >> cleanup_results

# Create DAG
dag_instance = remote_vm_workflow()
```

### Step 6: Create Your FTP Processing DAG with Remote Execution

Update your original FTP processing to use remote execution:

```python
# remote_ftp_processing_dag.py - FTP processing with remote execution

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from celery import Celery

# Configuration
VM2_HOST = '192.168.83.132'  # FTP server (vm2)
VM3_HOST = '192.168.83.133'  # Processing server (vm3)

SOURCE_PATHS = ['/home/rocky/in/sample1.txt', '/home/rocky/bon/in/sample3.txt']
DEST_PATHS = ['/home/rocky/in/sample1.txt', '/home/rocky/bon/in/sample3.txt']

celery_app = Celery('remote_tasks')
celery_app.config_from_object('airflow.providers.celery.executors.default_celery')

@dag(
    dag_id='remote_ftp_processing',
    schedule_interval=None,
    start_date=datetime(2024, 5, 1), 
    catchup=False,
    default_args={'owner': 'rocky', 'retries': 0}
)
def remote_ftp_workflow():
    
    @task.sensor(poke_interval=120, timeout=3600, mode="poke")
    def wait_for_source_files():
        """Check for files on VM2 via remote execution"""
        detected_files = []
        
        for src_path in SOURCE_PATHS:
            # Check file exists on VM2
            check_task = celery_app.send_task(
                'remote_tasks.execute_on_vm',
                args=['vm2', f'test -f {src_path} && echo "EXISTS" || echo "NOT_FOUND"'],
                queue='vm2_queue'
            )
            
            result = check_task.get(timeout=30)
            if result['success'] and 'EXISTS' in result['output']:
                detected_files.append(src_path)
        
        if detected_files:
            return PokeReturnValue(is_done=True, xcom_value=detected_files)
        else:
            return PokeReturnValue(is_done=False)
    
    @task
    def transfer_files(detected_files: list):
        """Transfer files from VM2 to VM3"""
        transferred = []
        
        for src_path in detected_files:
            src_index = SOURCE_PATHS.index(src_path)
            dest_path = DEST_PATHS[src_index]
            
            # Transfer via file_transfer task
            transfer_task = celery_app.send_task(
                'remote_tasks.file_transfer',
                args=['vm2', 'vm3', src_path, dest_path],
                queue='file_transfer_queue'
            )
            
            result = transfer_task.get(timeout=300)
            if result['success']:
                transferred.append(dest_path)
            else:
                raise Exception(f"Transfer failed: {result['error']}")
        
        return transferred
    
    @task
    def process_files(transferred_files: list):
        """Process files on VM3"""
        for file_path in transferred_files:
            # Run processing script on VM3
            process_task = celery_app.send_task(
                'remote_tasks.execute_on_vm',
                args=['vm3', f'python3 /home/rocky/scripts/simple_file_manager.py {file_path}'],
                queue='vm3_queue'
            )
            
            result = process_task.get(timeout=300)
            if not result['success']:
                raise Exception(f"Processing failed: {result['error']}")
        
        return len(transferred_files)
    
    # Workflow
    detected = wait_for_source_files()
    transferred = transfer_files(detected)
    processed = process_files(transferred)
    
    return processed

# Create DAG
dag_instance = remote_ftp_workflow()
```

## Part 5: Monitoring and Testing

### Step 7: Monitor the System

```bash
# Check all systemd services
sudo systemctl status airflow-*

# Monitor Celery workers via Flower
# Access: http://192.168.83.129:5555

# Check worker logs
journalctl -u airflow-worker-vm1 -f
journalctl -u airflow-worker-vm2 -f
journalctl -u airflow-worker-vm3 -f

# Test SSH connectivity to all VMs
ssh -i /home/rocky/.ssh/id_ed25519 rocky@192.168.83.131 "hostname"
ssh -i /home/rocky/.ssh/id_ed25519 rocky@192.168.83.132 "hostname"  
ssh -i /home/rocky/.ssh/id_ed25519 rocky@192.168.83.133 "hostname"
```

### Step 8: Test the System

```bash
# Test Celery tasks directly
cd ~/airflow
python3 -c "
from celery import Celery
app = Celery('remote_tasks')
app.config_from_object('airflow.providers.celery.executors.default_celery')

# Test VM1
result = app.send_task('remote_tasks.execute_on_vm', ['vm1', 'hostname'], queue='vm1_queue')
print('VM1 result:', result.get(timeout=30))

# Test VM2  
result = app.send_task('remote_tasks.execute_on_vm', ['vm2', 'hostname'], queue='vm2_queue')
print('VM2 result:', result.get(timeout=30))

# Test VM3
result = app.send_task('remote_tasks.execute_on_vm', ['vm3', 'hostname'], queue='vm3_queue')
print('VM3 result:', result.get(timeout=30))
"
```

This solution gives you:
- ✅ **No installation on target VMs** (only SSH access needed)
- ✅ **Distributed task execution** via Celery queues
- ✅ **Queue-based VM targeting** (vm1_queue, vm2_queue, vm3_queue)
- ✅ **Integrated DAG processor** (runs with scheduler, no standalone process)
- ✅ **SystemD service management** for all components
- ✅ **TaskFlow API** for clean DAG definitions
- ✅ **Monitoring via Flower** and systemd logs

The system scales easily - just add more VMs to the configuration and create additional worker services!





======================================================================   

# Scenario 1: Component Logic and Workflow Trace

Let me explain the **exact workflow** and **component relationships** in simple terms.

## Component Architecture (Single Machine)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VM_MAIN (192.168.83.129)                        │
│                      Airflow Machine                               │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │  Scheduler  │   │ Webserver   │   │ PostgreSQL  │              │
│  │             │   │             │   │             │              │
│  │ - Reads DAGs│   │ - Shows UI  │   │ - Stores    │              │
│  │ - Creates   │   │ - Triggers  │   │   metadata  │              │
│  │   tasks     │   │   DAGs      │   │ - Task      │              │
│  │             │   │             │   │   states    │              │
│  └─────────────┘   └─────────────┘   └─────────────┘              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    RabbitMQ                                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │   │
│  │  │ vm1_queue   │ │ vm2_queue   │ │ vm3_queue   │          │   │
│  │  │             │ │             │ │             │          │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Worker-VM1  │ │ Worker-VM2  │ │ Worker-VM3  │ │Worker-General│  │
│  │             │ │             │ │             │ │             │   │
│  │Listens to:  │ │Listens to:  │ │Listens to:  │ │Listens to:  │   │
│  │vm1_queue    │ │vm2_queue    │ │vm3_queue    │ │default      │   │
│  │default      │ │default      │ │default      │ │all_vms_queue│   │
│  │             │ │             │ │             │ │file_transfer│   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                               SSH Commands
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌─────────────┐            ┌─────────────┐            ┌─────────────┐
│    VM1      │            │    VM2      │            │    VM3      │
│192.168.83.131│           │192.168.83.132│           │192.168.83.133│
│             │            │             │            │             │
│ SSH Server  │            │ SSH Server  │            │ SSH Server  │
│ Only!       │            │ Only!       │            │ Only!       │
│ No Airflow  │            │ No Airflow  │            │ No Airflow  │
│ No Celery   │            │ No Celery   │            │ No Celery   │
└─────────────┘            └─────────────┘            └─────────────┘
```

## Step-by-Step Workflow Trace

Let's trace what happens when you trigger a DAG that executes `hostname` command on VM2:

### **Step 1: DAG Trigger**
```python
# In your DAG
execute_on_specific_vm('vm2', 'hostname')
```

**What happens:**
- User clicks "Trigger DAG" in Airflow UI (or sensor detects something)
- **Airflow Webserver** sends trigger signal to **PostgreSQL**
- **PostgreSQL** stores: DAG run created, status = "running"

### **Step 2: Scheduler Picks Up Task**
**Airflow Scheduler process** (running on main machine):
- Reads PostgreSQL every few seconds
- Sees new DAG run needs to be executed
- Creates task instance: `execute_on_specific_vm` with status = "queued"
- Passes task to **CeleryExecutor**

### **Step 3: CeleryExecutor Converts Task**
**CeleryExecutor** (part of scheduler process):
- Converts Airflow task into Celery task
- Determines this task should go to `vm2_queue` (because vm_name='vm2')
- Sends message to **RabbitMQ** `vm2_queue`

**Message content:**
```json
{
  "task": "remote_tasks.execute_on_vm",
  "args": ["vm2", "hostname"],
  "queue": "vm2_queue"
}
```

### **Step 4: Celery Worker Picks Up Task**
**Worker-VM2** process (systemd service on main machine):
- Continuously listens to `vm2_queue` in RabbitMQ
- Sees new message in queue
- Pulls message: "Execute hostname command on vm2"
- Worker says: "I'll handle this!"

### **Step 5: SSH Execution**
**Worker-VM2** executes Python code:
```python
# Inside the worker process
ssh_executor.execute_command(
    host='192.168.83.132',      # VM2's IP
    username='rocky',
    ssh_key='/home/rocky/.ssh/id_ed25519',
    command='hostname'
)
```

**What happens technically:**
1. Worker creates SSH connection to 192.168.83.132
2. Authenticates using SSH key
3. Executes `hostname` command on VM2
4. Gets result: `vm2-hostname`
5. Closes SSH connection

### **Step 6: Result Reporting**
**Worker-VM2** sends result back:
- Stores result in **PostgreSQL**: task status = "success", result = "vm2-hostname"
- **RabbitMQ** marks message as "acknowledged" (processed)

### **Step 7: UI Updates**
**Airflow Webserver**:
- Reads updated task status from PostgreSQL
- Shows green success box in DAG view
- Displays result in task logs

## Key Relationships Explained

### **1. Queue → Worker Mapping**
```
vm1_queue    →    Worker-VM1    →    SSH to 192.168.83.131
vm2_queue    →    Worker-VM2    →    SSH to 192.168.83.132  
vm3_queue    →    Worker-VM3    →    SSH to 192.168.83.133
default      →    All Workers   →    Local execution
```

### **2. Why Multiple Workers on Same Machine?**
- **Specialization**: Each worker knows which VM to connect to
- **Parallel Execution**: VM1 and VM2 tasks can run simultaneously
- **Queue Isolation**: VM1 tasks don't interfere with VM2 tasks
- **Resource Management**: Each worker handles 2 concurrent SSH connections

### **3. Data Flow Pattern**
```
TaskFlow DAG → Scheduler → CeleryExecutor → RabbitMQ → Worker → SSH → Target VM
     ↑                                                                      ↓
PostgreSQL ← Webserver ← Result Storage ← Worker ← SSH Response ← Target VM
```

## Simple Example with Timeline

**T=0 seconds**: User triggers DAG  
**T=1 second**: Scheduler creates task in PostgreSQL  
**T=2 seconds**: CeleryExecutor sends message to `vm2_queue`  
**T=3 seconds**: Worker-VM2 pulls message from queue  
**T=4 seconds**: Worker-VM2 opens SSH to 192.168.83.132  
**T=5 seconds**: SSH executes `hostname` on VM2  
**T=6 seconds**: VM2 returns `vm2-hostname`  
**T=7 seconds**: Worker-VM2 stores result in PostgreSQL  
**T=8 seconds**: Webserver shows task as successful  

## Why This Design Works

### **✅ Advantages:**
1. **No software on targets** - Only SSH needed
2. **Distributed processing** - Multiple tasks run in parallel
3. **Queue-based routing** - Tasks automatically go to right worker
4. **Fault tolerance** - If one worker fails, others continue
5. **Scalable** - Add more workers for more concurrent SSH connections

### **🔄 Load Balancing Example:**
If you send 10 tasks to `vm2_queue`:
- Worker-VM2 (concurrency=2) takes 2 tasks immediately
- Executes 2 SSH connections to VM2 in parallel
- When one finishes, worker takes next task from queue
- Continues until all 10 tasks complete

### **📊 Resource Usage:**
- **Main Machine**: Runs all Airflow components + 4 Celery workers
- **Target VMs**: Just receive SSH connections (minimal overhead)
- **Network**: Only SSH traffic (port 22)
- **Memory**: ~500MB per Celery worker on main machine

This design gives you **enterprise distributed execution** without installing anything on target machines!
