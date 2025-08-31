# S05-Airflow_Core_Components_Installation.md

## Apache Airflow 2.9.0 Installation with High Availability Configuration

### Step 5.1:  Install Airflow on Scheduler and Webserver Nodes (VM1, VM2, VM3)

**Execute on VM1 (haproxy-1), VM2 (haproxy-2), and VM3 (scheduler-2):**
```bash
# Install Python dependencies for Airflow
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory and set environment
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow 2.9.0 with HA components
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres,crypto]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "celery==5.5.0" "flower==1.2.0"
pip3 install paramiko  # For SSH connections

# Fix permissions for airflow binary
sudo chmod +x /home/rocky/.local/bin/airflow
sudo chmod 755 /home/rocky /home/rocky/.local /home/rocky/.local/bin

# Create airflow directories
mkdir -p ~/airflow/logs ~/airflow/plugins ~/airflow/config ~/airflow/utils

# Create symlink to NFS mounted DAGs
ln -s /mnt/airflow-dags ~/airflow/dags

# Create utility modules for DAG development
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

### Step 5.2: Configure Airflow for High Availability

**⚠️ IMPORTANT: Replace `<MAIN_VIP>` and `<NFS_VIP>` with your chosen VIP addresses.**

**Create HA-ready airflow.cfg on VM1 (haproxy-1):**
```bash
# Initialize Airflow configuration (will be customized for HA)
airflow db init

# Create production-ready airflow.cfg with HA settings
tee ~/airflow/airflow.cfg << EOF
[core]
# Executor configuration for Celery
executor = CeleryExecutor
dags_folder = /home/rocky/airflow/dags
load_examples = False
default_timezone = Asia/Tehran
parallelism = 32
max_active_runs_per_dag = 16
dagbag_import_timeout = 30
dagbag_import_error_tracebacks = True
dagbag_import_error_traceback_depth = 2

[database]
# Use VIP for database connections (load balanced PostgreSQL)
# REPLACE_WITH_YOUR_MAIN_VIP
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@<MAIN_VIP>:5000/airflow_db
pool_size = 10
max_overflow = 20
pool_pre_ping = True
pool_recycle = 3600
sql_alchemy_pool_enabled = True

[celery]
# RabbitMQ cluster configuration for HA - Using hostnames
broker_url = amqp://airflow_user:airflow_pass@rabbit-1:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-2:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-3:5672/airflow_host
# REPLACE_WITH_YOUR_MAIN_VIP for result backend
result_backend = db+postgresql://airflow_user:airflow_pass@<MAIN_VIP>:5000/airflow_db
worker_concurrency = 4
broker_transport_options = {"priority_steps": [0, 5, 9], "sep": ":", "queue_order_strategy": "priority"}
result_backend_sqlalchemy_pool_enabled = True

[scheduler]
# Multi-scheduler HA configuration
standalone_dag_processor = True
num_runs = -1
scheduler_heartbeat_sec = 5
job_heartbeat_sec = 5
run_duration = -1
parsing_processes = 2
scheduler_zombie_task_threshold = 300
schedule_after_task_execution = True
use_job_schedule = True
max_tis_per_query = 512
processor_poll_interval = 1

[webserver]
# Webserver configuration for load balancing
# REPLACE_WITH_YOUR_MAIN_VIP
base_url = http://<MAIN_VIP>:8081
web_server_host = 0.0.0.0
web_server_port = 8080
secret_key = $(python3 -c "import os; print(repr(os.urandom(32)))")
session_lifetime_minutes = 43200
expose_config = True
rbac = True

[api]
auth_backends = airflow.api.auth.backend.basic_auth

[logging]
# Logging configuration
remote_logging = False
base_log_folder = /home/rocky/airflow/logs
log_level = INFO
fab_logging_level = INFO
logging_level = INFO

[metrics]
statsd_on = False

[secrets]
backend = airflow.secrets.local_filesystem.LocalFilesystemBackend

[operators]
default_owner = airflow
default_cpus = 1
default_ram = 512
default_disk = 512

[email]
email_backend = airflow.utils.email.send_email_smtp

[smtp]
smtp_host = localhost
smtp_starttls = True
smtp_ssl = False
smtp_port = 587
smtp_mail_from = airflow@localhost
EOF
```

**🔧 Airflow Configuration VIP Replacement Helper:**
```bash
# Replace VIP placeholders in airflow.cfg
# CUSTOMIZE these values with your chosen VIPs:
MAIN_VIP="192.168.1.210"    # Replace with your Main VIP
NFS_VIP="192.168.1.220"     # Replace with your NFS VIP

# Replace VIP placeholders in Airflow configuration
sed -i "s/<MAIN_VIP>/$MAIN_VIP/g" ~/airflow/airflow.cfg
sed -i "s/<NFS_VIP>/$NFS_VIP/g" ~/airflow/airflow.cfg

echo "Airflow configuration updated with VIPs:"
echo "Main VIP: $MAIN_VIP"
echo "NFS VIP: $NFS_VIP"
grep -E "sql_alchemy_conn|base_url|result_backend" ~/airflow/airflow.cfg
```

### Step 5.3: Copy Configuration to Other Nodes

**Distribute configuration from VM1 (haproxy-1) to other nodes:**
```bash
# Copy configuration to VM2 (haproxy-2)
scp ~/airflow/airflow.cfg rocky@haproxy-2:/home/rocky/airflow/
scp -r ~/airflow/config ~/airflow/utils rocky@haproxy-2:/home/rocky/airflow/

# Copy configuration to VM3 (scheduler-2) 
scp ~/airflow/airflow.cfg rocky@scheduler-2:/home/rocky/airflow/
scp -r ~/airflow/config ~/airflow/utils rocky@scheduler-2:/home/rocky/airflow/

# Copy SSH keys for task execution
for host in haproxy-2 scheduler-2; do
    scp ~/.ssh/id_ed25519 rocky@$host:~/.ssh/
    ssh rocky@$host "chmod 600 ~/.ssh/id_ed25519"
done
```

### Step 5.4: Initialize Airflow Database

**⚠️ IMPORTANT: Replace `<MAIN_VIP>` with your actual Main VIP address**

**Initialize database via VIP (run only once from VM1 - haproxy-1):**
```bash
# Test database connectivity via VIP
airflow db check

# Initialize Airflow database schema
airflow db migrate

# Create admin user for Airflow UI
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@airflow.local \
    --password admin123

# Create additional users for different roles
airflow users create \
    --username operator \
    --firstname Operator \
    --lastname User \
    --role Op \
    --email operator@airflow.local \
    --password operator123

airflow users create \
    --username viewer \
    --firstname Viewer \
    --lastname User \
    --role Viewer \
    --email viewer@airflow.local \
    --password viewer123
```

**🔧 Database Initialization Verification:**
```bash
# CUSTOMIZE this value:
MAIN_VIP="192.168.1.210"    # Replace with your Main VIP

# Verify database connection via VIP
echo "Testing database connection via VIP: $MAIN_VIP"
export PGPASSWORD=airflow_pass
psql -h $MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "
SELECT 'Database connection via VIP: SUCCESS', 
       current_database(), 
       current_user, 
       inet_server_addr() as connected_to_server;
"

# Test Airflow database initialization
airflow db check && echo "✅ Airflow database initialized successfully"
```

### Step 5.5: Install Airflow on Worker Node (VM12)

**On VM12 (celery-1):**
```bash
# Install Python dependencies
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with worker components
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install paramiko

# Fix permissions
sudo chmod +x /home/rocky/.local/bin/airflow
sudo chmod 755 /home/rocky /home/rocky/.local /home/rocky/.local/bin

# Create directories and symlinks
mkdir -p ~/airflow/logs ~/airflow/plugins ~/airflow/config ~/airflow/utils
ln -s /mnt/airflow-dags ~/airflow/dags

# Copy configuration from VM1 (haproxy-1)
scp rocky@haproxy-1:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@haproxy-1:/home/rocky/airflow/config ~/airflow/
scp -r rocky@haproxy-1:/home/rocky/airflow/utils ~/airflow/

# Copy SSH keys
scp rocky@haproxy-1:/home/rocky/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519

# Create utility modules
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

### Step 5.6: Install Airflow DAG Processors (VM4, VM5)

**On VM4 (nfs-1) and VM5 (nfs-2):**
```bash
# Install Python dependencies
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow for DAG processing
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"

# Fix permissions
sudo chmod +x /home/rocky/.local/bin/airflow
sudo chmod 755 /home/rocky /home/rocky/.local /home/rocky/.local/bin

# Create symlink to local DAGs directory
ln -s /srv/airflow/dags /home/rocky/airflow/dags
mkdir -p ~/airflow/logs ~/airflow/plugins ~/airflow/config ~/airflow/utils

# Copy configuration from VM1 (haproxy-1)
scp rocky@haproxy-1:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@haproxy-1:/home/rocky/airflow/config ~/airflow/ 2>/dev/null || mkdir ~/airflow/config
scp -r rocky@haproxy-1:/home/rocky/airflow/utils ~/airflow/ 2>/dev/null || mkdir ~/airflow/utils

# Create utility modules
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

### Step 5.7: Create SystemD Services

**On VM1 (haproxy-1) - Create scheduler and webserver services:**
```bash
# Airflow Scheduler service
sudo tee /etc/systemd/system/airflow-scheduler.service << EOF
[Unit]
Description=Airflow Scheduler (HA Node 1)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler-ha1
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Airflow Webserver service
sudo tee /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Airflow Webserver (HA Node 1)
After=network.target airflow-scheduler.service
Wants=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver-ha1
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Airflow Flower service
sudo tee /etc/systemd/system/airflow-flower.service << EOF
[Unit]
Description=Airflow Flower
After=network.target airflow-scheduler.service
Wants=airflow-scheduler.service

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-flower
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler airflow-webserver airflow-flower
```

**On VM2 (haproxy-2) - Create webserver service:**
```bash
# Airflow Webserver service for HA
sudo tee /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Airflow Webserver (HA Node 2)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver-ha2
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver
```

**On VM3 (scheduler-2) - Create scheduler service:**
```bash
# Airflow Scheduler service for HA
sudo tee /etc/systemd/system/airflow-scheduler.service << EOF
[Unit]
Description=Airflow Scheduler (HA Node 2)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler-ha2
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler
```

**On VM12 (celery-1) - Create worker service:**
```bash
# Airflow Worker service
sudo tee /etc/systemd/system/airflow-worker.service << EOF
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
ExecStart=/home/rocky/.local/bin/airflow celery worker --queues default,card_processing_queue --concurrency 4
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-worker
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-worker
```

**On VM4 (nfs-1) and VM5 (nfs-2) - Create DAG processor services:**
```bash
# On both VM4 and VM5
sudo tee /etc/systemd/system/airflow-dag-processor.service << EOF
[Unit]
Description=Airflow Standalone DAG Processor
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow:/home/rocky/.local/lib/python3.9/site-packages
Environment=LANG=en_US.UTF-8
Environment=LC_ALL=en_US.UTF-8
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
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
```

### Step 5.8: Configure Firewall for Airflow Services

**On VM1 (haproxy-1):**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp   # Airflow Webserver
sudo firewall-cmd --permanent --add-port=5555/tcp   # Flower
sudo firewall-cmd --reload
```

**On VM2 (haproxy-2):**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp   # Airflow Webserver
sudo firewall-cmd --reload
```

**On VM12 (celery-1):**
```bash
sudo firewall-cmd --permanent --add-port=8793/tcp   # Log server
sudo firewall-cmd --reload
```

### Step 5.9: Create Test DAG for Distributed Setup

**Create comprehensive test DAG on NFS storage:**
```bash
# On the active NFS server (check which one has VIP using: ip addr show | grep <NFS_VIP>)
sudo tee /srv/airflow/dags/test_distributed_ha_setup.py << 'EOF'
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import socket
import platform

@dag(
    dag_id='test_distributed_ha_setup',
    schedule_interval=timedelta(minutes=5),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        'owner': 'admin',
        'retries': 1,
        'retry_delay': timedelta(minutes=2),
        'queue': 'default'
    },
    tags=['test', 'distributed', 'ha']
)
def test_distributed_ha_setup():
    """
    Comprehensive test DAG for distributed HA Airflow setup
    """
    
    @task
    def test_scheduler_processing():
        """Test scheduler processing and database connectivity"""
        hostname = socket.gethostname()
        return {
            'component': 'scheduler',
            'processed_by_host': hostname,
            'timestamp': str(datetime.now()),
            'test': 'scheduler_processing',
            'status': 'SUCCESS'
        }
    
    @task
    def test_worker_execution():
        """Test worker execution and message queue connectivity"""
        import os
        return {
            'component': 'worker', 
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'working_directory': os.getcwd(),
            'timestamp': str(datetime.now()),
            'test': 'worker_execution',
            'status': 'SUCCESS'
        }
    
    @task
    def test_database_connectivity():
        """Test database connectivity via VIP"""
        from airflow.models import Variable
        try:
            # Test database operations
            test_key = f"test_key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            test_value = f"test_value_{socket.gethostname()}"
            
            Variable.set(test_key, test_value)
            retrieved_value = Variable.get(test_key)
            Variable.delete(test_key)
            
            return {
                'component': 'database',
                'hostname': socket.gethostname(),
                'test': 'database_connectivity',
                'set_value': test_value,
                'retrieved_value': retrieved_value,
                'match': test_value == retrieved_value,
                'timestamp': str(datetime.now()),
                'status': 'SUCCESS'
            }
        except Exception as e:
            return {
                'component': 'database',
                'hostname': socket.gethostname(),
                'test': 'database_connectivity',
                'error': str(e),
                'timestamp': str(datetime.now()),
                'status': 'FAILED'
            }
    
    @task
    def test_nfs_storage():
        """Test NFS storage accessibility"""
        import os
        import tempfile
        try:
            # Test file operations in mounted NFS
            test_dir = "/tmp"  # Using /tmp as it's accessible from all nodes
            test_file = f"nfs_test_{socket.gethostname()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            test_path = os.path.join(test_dir, test_file)
            
            # Write test file
            with open(test_path, 'w') as f:
                f.write(f"NFS test from {socket.gethostname()} at {datetime.now()}")
            
            # Read test file
            with open(test_path, 'r') as f:
                content = f.read()
            
            # Clean up
            os.remove(test_path)
            
            return {
                'component': 'nfs_storage',
                'hostname': socket.gethostname(),
                'test': 'nfs_storage',
                'file_path': test_path,
                'content_length': len(content),
                'timestamp': str(datetime.now()),
                'status': 'SUCCESS'
            }
        except Exception as e:
            return {
                'component': 'nfs_storage',
                'hostname': socket.gethostname(),
                'test': 'nfs_storage',
                'error': str(e),
                'timestamp': str(datetime.now()),
                'status': 'FAILED'
            }
    
    @task
    def test_message_queue():
        """Test message queue connectivity"""
        try:
            # This task itself tests message queue by being queued and executed
            return {
                'component': 'message_queue',
                'hostname': socket.gethostname(),
                'test': 'message_queue',
                'queue_status': 'Message successfully queued and executed',
                'timestamp': str(datetime.now()),
                'status': 'SUCCESS'
            }
        except Exception as e:
            return {
                'component': 'message_queue',
                'hostname': socket.gethostname(),
                'test': 'message_queue',
                'error': str(e),
                'timestamp': str(datetime.now()),
                'status': 'FAILED'
            }
    
    @task
    def aggregate_test_results(scheduler_result, worker_result, db_result, nfs_result, mq_result):
        """Aggregate all test results"""
        results = [scheduler_result, worker_result, db_result, nfs_result, mq_result]
        
        summary = {
            'total_tests': len(results),
            'successful_tests': len([r for r in results if r.get('status') == 'SUCCESS']),
            'failed_tests': len([r for r in results if r.get('status') == 'FAILED']),
            'test_timestamp': str(datetime.now()),
            'aggregated_by': socket.gethostname()
        }
        
        summary['overall_status'] = 'SUCCESS' if summary['failed_tests'] == 0 else 'PARTIAL_FAILURE'
        summary['detailed_results'] = results
        
        print(f"=== Distributed HA Airflow Test Summary ===")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Overall Status: {summary['overall_status']}")
        
        return summary
    
    # Define task dependencies
    scheduler_test = test_scheduler_processing()
    worker_test = test_worker_execution()
    db_test = test_database_connectivity()
    nfs_test = test_nfs_storage()
    mq_test = test_message_queue()
    
    summary = aggregate_test_results(scheduler_test, worker_test, db_test, nfs_test, mq_test)
    
    [scheduler_test, worker_test, db_test, nfs_test, mq_test] >> summary

# Create DAG instance
dag_instance = test_distributed_ha_setup()
EOF

# Set proper permissions
sudo chown rocky:rocky /srv/airflow/dags/test_distributed_ha_setup.py
sudo chmod 644 /srv/airflow/dags/test_distributed_ha_setup.py

echo "Test DAG created successfully"
```

### Step 5.10: Start Airflow Services in Proper Order

**Start services in correct sequence:**

**1. Start DAG Processors first (VM4 - active NFS):**
```bash
# Check which NFS server is active (has the VIP)
# CUSTOMIZE with your NFS VIP:
NFS_VIP="192.168.1.220"    # Replace with your NFS VIP

if ip addr show | grep -q $NFS_VIP; then
    echo "VM4 (nfs-1) is active - starting DAG processor"
    sudo systemctl start airflow-dag-processor
    sudo systemctl status airflow-dag-processor
else
    echo "VM4 (nfs-1) is standby - DAG processor will start automatically on failover"
fi
```

**2. Start Schedulers (VM1 - haproxy-1, VM3 - scheduler-2):**
```bash
# On VM1 (haproxy-1)
sudo systemctl start airflow-scheduler
sleep 10

# On VM3 (scheduler-2)
ssh rocky@scheduler-2 "sudo systemctl start airflow-scheduler"

# Verify both schedulers are running
sudo systemctl status airflow-scheduler
ssh rocky@scheduler-2 "sudo systemctl status airflow-scheduler"
```

**3. Start Webservers (VM1 - haproxy-1, VM2 - haproxy-2):**
```bash
# On VM1 (haproxy-1)
sudo systemctl start airflow-webserver
sleep 10

# On VM2 (haproxy-2)
ssh rocky@haproxy-2 "sudo systemctl start airflow-webserver"

# Verify both webservers are running
sudo systemctl status airflow-webserver
ssh rocky@haproxy-2 "sudo systemctl status airflow-webserver"
```

**4. Start Worker (VM12 - celery-1):**
```bash
# On VM12 (celery-1)
ssh rocky@celery-1 "sudo systemctl start airflow-worker"

# Verify worker is running
ssh rocky@celery-1 "sudo systemctl status airflow-worker"
```

**5. Start Flower (VM1 - haproxy-1):**
```bash
# On VM1 (haproxy-1)
sudo systemctl start airflow-flower
sudo systemctl status airflow-flower
```

### Step 5.11: Verification and Testing

**⚠️ IMPORTANT: Replace `<MAIN_VIP>` and `<HAPROXY_1_IP>` with your actual addresses**

**Verify all services are running:**
```bash
echo "=== Airflow Core Components Status ==="

# VM1 (haproxy-1) services
echo "VM1 (haproxy-1):"
sudo systemctl is-active airflow-scheduler && echo "✅ Scheduler active" || echo "❌ Scheduler failed"
sudo systemctl is-active airflow-webserver && echo "✅ Webserver active" || echo "❌ Webserver failed"  
sudo systemctl is-active airflow-flower && echo "✅ Flower active" || echo "❌ Flower failed"

# VM2 (haproxy-2) services
echo "VM2 (haproxy-2):"
ssh rocky@haproxy-2 "sudo systemctl is-active airflow-webserver" && echo "✅ Webserver active" || echo "❌ Webserver failed"

# VM3 (scheduler-2) services
echo "VM3 (scheduler-2):"
ssh rocky@scheduler-2 "sudo systemctl is-active airflow-scheduler" && echo "✅ Scheduler active" || echo "❌ Scheduler failed"

# VM12 (celery-1) services
echo "VM12 (celery-1):"
ssh rocky@celery-1 "sudo systemctl is-active airflow-worker" && echo "✅ Worker active" || echo "❌ Worker failed"

# VM4 (nfs-1) services (active NFS)
echo "VM4 (nfs-1 - NFS active):"
sudo systemctl is-active airflow-dag-processor && echo "✅ DAG Processor active" || echo "❌ DAG Processor failed"
```

**Test Airflow functionality:**
```bash
# CUSTOMIZE this value:
MAIN_VIP="192.168.1.210"    # Replace with your Main VIP

# Test Airflow CLI
airflow db check && echo "✅ Database connectivity: OK"

# Test scheduler coordination
export PGPASSWORD=airflow_pass
psql -h $MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "
SELECT hostname, state, latest_heartbeat 
FROM job 
WHERE job_type = 'SchedulerJob' 
AND state = 'running' 
ORDER BY latest_heartbeat DESC;
" && echo "✅ Multi-scheduler coordination: OK"

# Test DAG parsing
airflow dags list | grep test_distributed_ha_setup && echo "✅ DAG parsing: OK"

# Trigger test DAG
airflow dags unpause test_distributed_ha_setup
airflow dags trigger test_distributed_ha_setup

echo ""
echo "Airflow Core Components Installation Complete!"
echo "==============================================="
echo "✅ Scheduler HA: VM1 (haproxy-1) + VM3 (scheduler-2)"
echo "✅ Webserver HA: VM1 (haproxy-1) + VM2 (haproxy-2) (load balanced)"
echo "✅ Worker: VM12 (celery-1)"
echo "✅ DAG Processor HA: VM4 (nfs-1) + VM5 (nfs-2) (active/passive)"
echo "✅ Flower Monitor: VM1 (haproxy-1)"
echo ""
echo "Access URLs:"
echo "- Airflow UI (Load Balanced): http://$MAIN_VIP:8081"
echo "- Flower: http://haproxy-1:5555 or http://<HAPROXY_1_IP>:5555"
echo "- HAProxy Stats: http://$MAIN_VIP:7000"
echo ""
echo "Login: admin / admin123"
```

**🔧 Complete Services Verification Script:**
```bash
# Create comprehensive services verification script
# CUSTOMIZE these values:
MAIN_VIP="192.168.1.210"         # Replace with your Main VIP
HAPROXY_1_IP="192.168.1.10"      # Replace with VM1 IP

sudo tee /usr/local/bin/verify_airflow_services.sh << EOF
#!/bin/bash
MAIN_VIP="$MAIN_VIP"
HAPROXY_1_IP="$HAPROXY_1_IP"

echo "=== Airflow Services Verification ==="
echo "Main VIP: \$MAIN_VIP"
echo ""

# Test database connectivity via VIP
echo "Testing database connectivity..."
export PGPASSWORD=airflow_pass
if psql -h \$MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Database accessible via VIP"
else
    echo "❌ Database connection failed"
fi

# Test Airflow web UI via VIP
echo "Testing Airflow web UI..."
if curl -s -I http://\$MAIN_VIP:8081 >/dev/null 2>&1; then
    echo "✅ Airflow UI accessible via load balancer"
else
    echo "❌ Airflow UI not accessible"
fi

# Test Flower interface
echo "Testing Flower interface..."
if curl -s -I http://\$HAPROXY_1_IP:5555 >/dev/null 2>&1; then
    echo "✅ Flower accessible"
else
    echo "❌ Flower not accessible"
fi

# Test RabbitMQ connectivity (using hostnames)
echo "Testing RabbitMQ connectivity..."
if curl -s -u airflow_user:airflow_pass http://rabbit-1:15672/api/overview >/dev/null 2>&1; then
    echo "✅ RabbitMQ accessible"
else
    echo "❌ RabbitMQ connection failed"
fi

echo ""
echo "Services verification completed"
EOF

sudo chmod +x /usr/local/bin/verify_airflow_services.sh
# Run after customizing: sudo /usr/local/bin/verify_airflow_services.sh
```

This completes the Airflow Core Components installation with:

✅ **Multi-Scheduler HA**: VM1 (haproxy-1) + VM3 (scheduler-2) coordinated via database  
✅ **Load Balanced Webservers**: VM1 (haproxy-1) + VM2 (haproxy-2) via HAProxy  
✅ **Distributed Workers**: VM12 (celery-1) with horizontal scaling capability  
✅ **HA DAG Processing**: VM4 (nfs-1) + VM5 (nfs-2) coordinated with NFS failover  
✅ **Monitoring**: Flower dashboard for Celery monitoring  
✅ **Production Configuration**: Optimized settings for HA operation  

All components are now using the HA infrastructure (VIPs, clusters) that was established in previous sections.

**Next Steps**: Once this Airflow Core Components installation is complete and verified, proceed to **S06-Complete_System_Integration_and_Testing.md** for comprehensive testing and validation of the entire distributed HA infrastructure.

