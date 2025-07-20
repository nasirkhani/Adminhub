implement advanced distributed Airflow setup step by step.

## Final Architecture Confirmation:

```
VM1 (192.168.83.129) - Main Airflow:
├── Airflow Scheduler (without DAG processing)
├── Airflow Webserver
├── PostgreSQL
├── RabbitMQ
└── Mounts VM2's NFS for DAG files

VM2 (192.168.83.132) - NFS + DAG Processor:
├── NFS Server (shares DAG folder)
├── FTP Server (existing)
├── Standalone DAG Processor
└── DAG files (source of truth)

VM3 (192.168.83.133) - Target VM:
└── SSH only (no changes)

VM4 (192.168.83.131) - Worker:
├── Celery Workers
├── Airflow installation (no scheduler/webserver)
└── Mounts VM2's NFS for DAG files
```

Let's start implementation:

## Phase 1: Set up NFS Server on VM2

### Step 1.1: Install NFS Server on VM2

SSH into VM2:
```bash
ssh rocky@192.168.83.132
```

Install NFS packages:
```bash
sudo dnf install -y nfs-utils
sudo systemctl enable --now nfs-server
sudo systemctl start rpcbind
sudo systemctl enable rpcbind
```

### Step 1.2: Create DAG Directory on VM2

```bash
# Create the directory that will be shared
sudo mkdir -p /srv/airflow/dags
sudo chown -R rocky:rocky /srv/airflow
chmod 755 /srv/airflow/dags

# Copy existing DAGs from VM1 (we'll do this after setting up mount)
```

### Step 1.3: Configure NFS Exports

```bash
sudo vi /etc/exports
```

Add this line:
```
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
```

Apply the configuration:
```bash
sudo exportfs -arv
sudo systemctl restart nfs-server

# Verify exports
sudo exportfs -v
```

### Step 1.4: Configure Firewall on VM2

```bash
# If firewall is enabled, allow NFS
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --permanent --add-service=rpc-bind
sudo firewall-cmd --permanent --add-service=mountd
sudo firewall-cmd --reload

# Or if you disabled firewall before, skip this
```

## Phase 2: Mount NFS on VM1 (Main Airflow)

### Step 2.1: Install NFS Client on VM1

SSH into VM1:
```bash
ssh rocky@192.168.83.129
```

Install NFS utilities:
```bash
sudo dnf install -y nfs-utils
```

### Step 2.2: Create Mount Point and Mount NFS

```bash
# Backup existing DAGs first
cd /home/rocky/airflow
tar -czf dags_backup_$(date +%Y%m%d).tar.gz dags/

# Create mount point (rename existing)
mv dags dags_local_backup

# Mount NFS
mkdir dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags

# Verify mount
df -h | grep airflow
mount | grep airflow
```

### Step 2.3: Make Mount Permanent

```bash
sudo vi /etc/fstab
```

Add this line:
```
192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags nfs defaults,_netdev 0 0
```

Test the fstab entry:
```bash
sudo umount /home/rocky/airflow/dags
sudo mount -a
df -h | grep airflow
```

### Step 2.4: Copy DAGs to NFS

```bash
# Copy your existing DAGs to the NFS share
cp -r dags_local_backup/* dags/

# Verify files are visible
ls -la dags/
```

## Phase 3: Install Airflow on VM4 (Worker Only)

### Step 3.1: Initial Setup on VM4

SSH into VM4:
```bash
ssh rocky@192.168.83.131
```

Update system and install dependencies:
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ 
sudo dnf install -y postgresql-devel
sudo dnf install -y nfs-utils
```

### Step 3.2: Create Airflow User Environment

```bash
# Create airflow directory
mkdir -p ~/airflow
cd ~/airflow

# Set AIRFLOW_HOME
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc
```

### Step 3.3: Install Airflow with Constraints

```bash
# Install Airflow with constraints file for Python 3.9
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# Install additional dependencies
pip3 install "celery==5.3.4" "flower==2.0.1" paramiko
```

### Step 3.4: Mount NFS on VM4

```bash
# Create mount point
mkdir -p ~/airflow/dags

# Mount NFS
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags

# Make permanent
sudo vi /etc/fstab
```

Add:
```
192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags nfs defaults,_netdev 0 0
```

Test:
```bash
sudo mount -a
ls -la ~/airflow/dags/
```

### Step 3.5: Configure Airflow on VM4

Copy airflow.cfg from VM1:
```bash
# From VM1, copy the config
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
```

Edit the configuration:
```bash
vi ~/airflow/airflow.cfg
```

Key settings to verify/update:
```ini
[core]
executor = CeleryExecutor
load_examples = False
dags_folder = /home/rocky/airflow/dags

[database]
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

[celery]
broker_url = amqp://airflow_user:airflow_pass@192.168.83.129:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

[celery_broker_transport_options]
visibility_timeout = 21600
```

### Step 3.6: Copy SSH Keys for Target VMs

```bash
# Copy SSH keys from VM1
mkdir -p ~/.ssh
scp rocky@192.168.83.129:/home/rocky/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519
```

### Step 3.7: Copy Python Modules

```bash
# Copy your custom modules from VM1
scp -r rocky@192.168.83.129:/home/rocky/airflow/config ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/utils ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/__init__.py ~/airflow/

# Ensure __init__.py exists
touch ~/airflow/__init__.py
touch ~/airflow/config/__init__.py
touch ~/airflow/utils/__init__.py
```

### Step 3.8: Create SystemD Service for Worker

```bash
sudo vi /etc/systemd/system/airflow-worker.service
```

Add:
```ini
[Unit]
Description=Airflow Celery Worker
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery worker --queues remote_tasks,default --concurrency 4
Restart=on-failure
RestartSec=10s
SyslogIdentifier=airflow-worker

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-worker
sudo systemctl start airflow-worker
sudo systemctl status airflow-worker
```

## Phase 4: Install DAG Processor on VM2

### Step 4.1: Install Airflow on VM2

SSH into VM2:
```bash
ssh rocky@192.168.83.132
```

Install dependencies:
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel
```

### Step 4.2: Install Airflow on VM2

```bash
# Create airflow directory
mkdir -p ~/airflow
cd ~/airflow

# Set AIRFLOW_HOME
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with constraints
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
```

### Step 4.3: Configure Airflow on VM2

Copy configuration from VM1:
```bash
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
```

Create symbolic link to DAGs:
```bash
ln -s /srv/airflow/dags /home/rocky/airflow/dags
```

### Step 4.4: Create DAG Processor Service

```bash
sudo vi /etc/systemd/system/airflow-dag-processor.service
```

Add:
```ini
[Unit]
Description=Airflow Standalone DAG Processor
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow dag-processor
Restart=on-failure
RestartSec=10s
SyslogIdentifier=airflow-dag-processor

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
sudo systemctl start airflow-dag-processor
sudo systemctl status airflow-dag-processor
```

## Phase 5: Reconfigure VM1 Scheduler

### Step 5.1: Update Airflow Configuration on VM1

SSH into VM1:
```bash
ssh rocky@192.168.83.129
```

Edit configuration:
```bash
vi ~/airflow/airflow.cfg
```

Add/update this setting:
```ini
[scheduler]
standalone_dag_processor = True
```

### Step 5.2: Restart Scheduler

```bash
sudo systemctl restart airflow-scheduler
sudo systemctl status airflow-scheduler

# Check logs
sudo journalctl -u airflow-scheduler -f
```

## Phase 6: Verification and Testing

### Step 6.1: Verify All Services

On VM1:
```bash
# Check services
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver
sudo systemctl status airflow-flower

# Check that scheduler is NOT processing DAGs
sudo journalctl -u airflow-scheduler | grep -i "standalone"
```

On VM2:
```bash
# Check DAG processor
sudo systemctl status airflow-dag-processor
sudo journalctl -u airflow-dag-processor -f

# Verify it's processing DAGs
ls -la /srv/airflow/dags/
```

On VM4:
```bash
# Check worker
sudo systemctl status airflow-worker
sudo journalctl -u airflow-worker -f

# Test Python module access
python3 -c "import sys; sys.path.insert(0, '/home/rocky/airflow'); from utils.simple_ssh import execute_ssh_command; print('Modules OK')"
```

### Step 6.2: Test the Complete Setup

1. **Create a test DAG on VM2**:
```bash
# On VM2
vi /srv/airflow/dags/distributed_test_dag.py
```

Add:
```python
from datetime import datetime
from airflow.decorators import dag, task
import socket

@dag(
    dag_id='distributed_system_test',
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
```

2. **Add VM3 to config on VM2**:
```bash
vi /srv/airflow/dags/config/simple_vms.py
```

Update to include VM3:
```python
TARGET_VMS = {
    'vm1': {
        'host': '192.168.83.131',
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519'
    },
    'vm3': {
        'host': '192.168.83.133',
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519'
    }
}
```

3. **Trigger and Monitor**:
- Access Airflow UI: http://192.168.83.129:8080
- Trigger the `distributed_system_test` DAG
- Check task logs to verify it runs on VM4 worker
- Monitor in Flower: http://192.168.83.129:5555

### Step 6.3: Verify Architecture Components

```bash
# Check where components are running
echo "=== Component Locations ==="
echo "Scheduler: VM1 (192.168.83.129)"
echo "Webserver: VM1 (192.168.83.129)"
echo "DAG Processor: VM2 (192.168.83.132)"
echo "Worker: VM4 (192.168.83.131)"
echo "DAG Files: VM2 (192.168.83.132) via NFS"
```

## Summary

You now have a fully distributed Airflow architecture:
- **VM1**: Runs scheduler (without DAG processing), webserver, database, and message broker
- **VM2**: Hosts DAG files via NFS and runs standalone DAG processor
- **VM3**: Target VM (unchanged)
- **VM4**: Dedicated Celery worker

This architecture provides:
- Better scalability (can add more workers easily)
- Improved security (DAG processor isolated)
- Centralized DAG management (edit on VM2)
- Reduced scheduler load (no DAG parsing)

The system is now ready for production workloads!
