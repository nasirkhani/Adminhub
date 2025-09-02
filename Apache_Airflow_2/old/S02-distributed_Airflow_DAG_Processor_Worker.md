# Distributed Apache Airflow Setup - Complete Walkthrough

This guide provides a comprehensive walkthrough for setting up a distributed Apache Airflow 2.9.0 architecture with separate components across multiple VMs.

## Architecture Overview

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

## Prerequisites

- All VMs running Rocky Linux 9
- Python 3.9 installed on all VMs
- Network connectivity between all VMs
- SSH key-based authentication from VM1 to all other VMs

## Phase 1: Configure Firewall Rules

### VM1 (Main Airflow) Firewall Configuration

```bash
# Services that need to be accessible from other VMs
sudo firewall-cmd --add-port=5432/tcp --permanent   # PostgreSQL
sudo firewall-cmd --add-port=5672/tcp --permanent   # RabbitMQ
sudo firewall-cmd --add-port=15672/tcp --permanent  # RabbitMQ Management
sudo firewall-cmd --add-port=8080/tcp --permanent   # Webserver
sudo firewall-cmd --add-port=5555/tcp --permanent   # Flower
sudo firewall-cmd --reload
```

### VM2 (NFS + DAG Processor) Firewall Configuration

```bash
# NFS and FTP services
sudo firewall-cmd --add-service=nfs --permanent
sudo firewall-cmd --add-service=rpc-bind --permanent
sudo firewall-cmd --add-service=mountd --permanent
sudo firewall-cmd --add-port=21/tcp --permanent     # FTP (if needed)
sudo firewall-cmd --reload
```

### VM4 (Worker) Firewall Configuration

```bash
# Worker log server
sudo firewall-cmd --add-port=8793/tcp --permanent   # Log server
sudo firewall-cmd --reload
```

## Phase 2: Set up NFS Server on VM2

### Step 2.1: Install NFS Server

```bash
# SSH into VM2
ssh rocky@192.168.83.132

# Install NFS packages
sudo dnf install -y nfs-utils
sudo systemctl enable --now nfs-server
sudo systemctl start rpcbind
sudo systemctl enable rpcbind
```

### Step 2.2: Create and Configure NFS Share

```bash
# Create the directory to be shared
sudo mkdir -p /srv/airflow/dags
sudo chown -R rocky:rocky /srv/airflow
chmod 755 /srv/airflow/dags

# Configure NFS exports
sudo vi /etc/exports
```

Add this line:
```
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
```

Apply configuration:
```bash
sudo exportfs -arv
sudo systemctl restart nfs-server
sudo exportfs -v  # Verify exports
```

## Phase 3: Configure NFS Client on VM1

### Step 3.1: Install NFS Client and Mount

```bash
# SSH into VM1
ssh rocky@192.168.83.129

# Install NFS utilities
sudo dnf install -y nfs-utils

# Backup existing DAGs
cd /home/rocky/airflow
tar -czf dags_backup_$(date +%Y%m%d).tar.gz dags/

# Rename existing dags folder and create mount point
mv dags dags_local_backup
mkdir dags

# Mount NFS
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags

# Make mount permanent
sudo vi /etc/fstab
```

Add to /etc/fstab:
```
192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags nfs defaults,_netdev 0 0
```

Test and copy DAGs:
```bash
sudo umount /home/rocky/airflow/dags
sudo mount -a
cp -r dags_local_backup/* dags/
ls -la dags/
```

### Step 3.2: Update /etc/hosts for hostname resolution

```bash
sudo vi /etc/hosts
```

Add:
```
192.168.83.131 worker1
192.168.83.132 ftp
192.168.83.133 card1
```

## Phase 4: Install and Configure VM4 (Worker)

### Step 4.1: System Setup

```bash
# SSH into VM4
ssh rocky@192.168.83.131

# Update system and install dependencies
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ 
sudo dnf install -y postgresql-devel nfs-utils

# Create airflow directory and set environment
mkdir -p ~/airflow
cd ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc
```

### Step 4.2: Install Airflow with Constraints

```bash
# Install Airflow with proper constraints
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# Install additional required packages
pip3 install paramiko
```

### Step 4.3: Mount NFS on VM4

```bash
# Create mount point
mkdir -p ~/airflow/dags

# Mount NFS
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags

# Make permanent
sudo vi /etc/fstab
```

Add to /etc/fstab:
```
192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags nfs defaults,_netdev 0 0
```

Test mount:
```bash
sudo mount -a
ls -la ~/airflow/dags/
```

### Step 4.4: Configure Airflow

Copy configuration from VM1:
```bash
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
```

Edit airflow.cfg to ensure these settings:
```bash
vi ~/airflow/airflow.cfg
```

Key configurations:
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

[logging]
remote_logging = False
base_log_folder = /home/rocky/airflow/logs
```

### Step 4.5: Copy SSH Keys and Python Modules

```bash
# Copy SSH keys
mkdir -p ~/.ssh
scp rocky@192.168.83.129:/home/rocky/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519

# Copy Python modules
scp -r rocky@192.168.83.129:/home/rocky/airflow/config ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/utils ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/__init__.py ~/airflow/

# Create __init__.py files
touch ~/airflow/__init__.py
touch ~/airflow/config/__init__.py
touch ~/airflow/utils/__init__.py
```

### Step 4.6: Create SystemD Service for Worker

```bash
sudo vi /etc/systemd/system/airflow-worker.service
```

Content:
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

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-worker
sudo systemctl start airflow-worker
sudo systemctl status airflow-worker
```

## Phase 5: Install and Configure VM2 (DAG Processor)

### Step 5.1: Install Airflow on VM2

```bash
# SSH into VM2
ssh rocky@192.168.83.132

# Install dependencies
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory and set environment
mkdir -p ~/airflow
cd ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with constraints
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# Install SSH provider and paramiko for DAG parsing
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"
```

### Step 5.2: Configure Airflow on VM2

Copy configuration from VM1:
```bash
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
```

Create symbolic link to DAGs:
```bash
ln -s /srv/airflow/dags /home/rocky/airflow/dags
```

Copy Python modules (needed for DAG parsing):
```bash
rsync -av rocky@192.168.83.129:/home/rocky/airflow/config/ ~/airflow/config/
rsync -av rocky@192.168.83.129:/home/rocky/airflow/utils/ ~/airflow/utils/

# Create __init__.py files
touch ~/airflow/__init__.py
touch ~/airflow/config/__init__.py
touch ~/airflow/utils/__init__.py
```

### Step 5.3: Create DAG Processor Service

```bash
sudo vi /etc/systemd/system/airflow-dag-processor.service
```

Content:
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
ExecStart=/bin/bash -c 'source /home/rocky/.bashrc && exec /home/rocky/.local/bin/airflow dag-processor'
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airflow-dag-processor
LimitNOFILE=65536
LimitNPROC=4096

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

## Phase 6: Reconfigure VM1 Scheduler

### Step 6.1: Update Airflow Configuration

```bash
# SSH into VM1
ssh rocky@192.168.83.129

# Edit configuration
vi ~/airflow/airflow.cfg
```

Add/update:
```ini
[scheduler]
standalone_dag_processor = True
```

### Step 6.2: Restart Services

```bash
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
sudo systemctl status airflow-scheduler
```

## Phase 7: Verification

### Check All Services

On VM1:
```bash
sudo systemctl status airflow-scheduler airflow-webserver airflow-flower
```

On VM2:
```bash
sudo systemctl status airflow-dag-processor
ls -la /srv/airflow/dags/
```

On VM4:
```bash
sudo systemctl status airflow-worker
python3 -c "import sys; sys.path.insert(0, '/home/rocky/airflow'); from utils.simple_ssh import execute_ssh_command; print('Modules OK')"
```

### Test Distributed Setup

Create test DAG on VM2:
```bash
vi /srv/airflow/dags/S12_distributed_test.py
```

```python
from datetime import datetime
from airflow.decorators import dag, task
import socket

@dag(
    dag_id='S12_distributed_test',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False
)
def test_distributed():
    @task
    def show_worker():
        return f"Running on: {socket.gethostname()}"
    
    result = show_worker()

dag = test_distributed()
```

Access Airflow UI at http://192.168.83.129:8080 and trigger the test DAG.

## Troubleshooting Common Issues

### Permission Denied Errors
- Use bash wrapper in ExecStart: `/bin/bash -c 'exec /path/to/command'`
- Check file ownership and permissions

### Worker Can't Connect to PostgreSQL/RabbitMQ
- Ensure firewall ports are open on VM1
- Test connectivity: `telnet 192.168.83.129 5432`

### DAG Processor Import Errors
- Install all required providers on VM2
- Copy Python modules from VM1
- Ensure PYTHONPATH is set correctly

### Log Viewing Issues
- Add worker hostnames to /etc/hosts on VM1
- Ensure port 8793 is open on worker VMs
- Check worker log directory permissions

## Summary

You now have a fully distributed Airflow setup with:
- Centralized services on VM1
- DAG files and processor on VM2 (NFS)
- Dedicated worker on VM4
- Clean target VM3 for task execution

This architecture provides better scalability, security, and resource utilization compared to a single-machine setup.
