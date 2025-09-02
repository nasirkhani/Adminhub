

# 🚀 **PHASE 1: Scheduler HA Implementation (after debug)**

**Goal**: Add VM13 as dedicated scheduler for HA with VM1

## 📋 **Step 1.1: Prepare VM13 (New Scheduler Node)**

### **Basic Setup:**
```bash
# SSH into VM13
ssh rocky@192.168.83.151

# Disable SELinux for simplified setup
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Set hostname
sudo nmcli general hostname scheduler2
sudo reboot

# After reboot, SSH back
ssh rocky@192.168.83.151

# Update system
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel nfs-utils
```

### **Configure Firewall:**
```bash
# Open ports for scheduler communication
sudo firewall-cmd --permanent --add-port=8793/tcp   # Log server
sudo firewall-cmd --reload
```

### **Mount NFS for DAGs:**
```bash
# Create mount point and mount NFS
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /mnt/airflow-dags

# Make permanent
echo "192.168.83.132:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/
```

## 📋 **Step 1.2: Install Airflow on VM13**

```bash
# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with same version
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${AIRFLOW_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres,crypto]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install paramiko

# Ensure the binary is executable and directories are accessible
sudo chmod +x /home/rocky/.local/bin/airflow
sudo chmod 755 /home/rocky /home/rocky/.local /home/rocky/.local/bin

# Create symlinks and directories
ln -s /mnt/airflow-dags ~/airflow/dags
mkdir -p ~/airflow/logs ~/airflow/plugins

# Copy configuration and modules from VM1
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/config ~/airflow/ 2>/dev/null || mkdir ~/airflow/config
scp -r rocky@192.168.83.129:/home/rocky/airflow/utils ~/airflow/ 2>/dev/null || mkdir ~/airflow/utils

# Copy SSH keys for task execution
mkdir -p ~/.ssh
scp rocky@192.168.83.129:/home/rocky/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519

# Create utility modules
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

## 📋 **Step 1.3: Configure Multi-Scheduler Mode (Both VM1 and VM13)**

### **Update airflow.cfg on both nodes:**
```bash
# On VM1 - Add multi-scheduler specific settings
cat >> ~/airflow/airflow.cfg << EOF

[scheduler]
# Multi-scheduler settings
num_runs = -1
scheduler_heartbeat_sec = 5
job_heartbeat_sec = 5
run_duration = -1
# Enable multi-scheduler mode
parsing_processes = 2
scheduler_zombie_task_threshold = 300
schedule_after_task_execution = True
use_job_schedule = True
EOF
```

```bash
# On VM13 - Same configuration updates
cat >> ~/airflow/airflow.cfg << EOF

[scheduler]
# Multi-scheduler settings
num_runs = -1
scheduler_heartbeat_sec = 5
job_heartbeat_sec = 5
run_duration = -1
# Enable multi-scheduler mode
parsing_processes = 2
scheduler_zombie_task_threshold = 300
schedule_after_task_execution = True
use_job_schedule = True
EOF
```

## 📋 **Step 1.4: Create Scheduler Service on VM13**

```bash
# On VM13 - Create scheduler service
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

## 📋 **Step 1.5: Test Database Connectivity from VM13**

```bash
# On VM13 - Test database connection
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'VM13 DB connection: SUCCESS';"

# Test Airflow DB connection
airflow db check
```

## 📋 **Step 1.6: Start Second Scheduler**

### **Stop VM1 Scheduler Temporarily:**
```bash
# On VM1 - Stop scheduler for safe startup
sudo systemctl stop airflow-scheduler
```

### **Start VM13 Scheduler:**
```bash
# On VM13 - Start scheduler
sudo systemctl start airflow-scheduler

# Check status
sudo systemctl status airflow-scheduler

# Check logs for multi-scheduler coordination
sudo journalctl -u airflow-scheduler -f --lines=20
```

### **Start VM1 Scheduler Again:**
```bash
# On VM1 - Start scheduler (both will run together)
sudo systemctl start airflow-scheduler

# Check status
sudo systemctl status airflow-scheduler

# Check logs for coordination
sudo journalctl -u airflow-scheduler -f --lines=20
```

## 📋 **Step 1.7: Verification and Testing**

### **Check Both Schedulers are Running:**
```bash
# On VM1
echo "=== VM1 Scheduler Status ==="
sudo systemctl status airflow-scheduler --no-pager
ps aux | grep airflow-scheduler

# On VM13  
echo "=== VM13 Scheduler Status ==="
sudo systemctl status airflow-scheduler --no-pager
ps aux | grep airflow-scheduler
```

### **Verify Database Coordination:**
```bash
# On VM1 - Check scheduler jobs in database
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT hostname, state, latest_heartbeat, job_type 
FROM job 
WHERE job_type = 'SchedulerJob' 
ORDER BY latest_heartbeat DESC;
"
```

### **Create Test DAG for Multi-Scheduler:**
```bash
# On VM2 - Create scheduler HA test DAG
tee /srv/airflow/dags/test_scheduler_ha.py << 'EOF'
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import socket

@dag(
    dag_id='test_scheduler_ha',
    schedule_interval=timedelta(minutes=2),  # Run every 2 minutes
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        'owner': 'admin',
        'retries': 1,
        'retry_delay': timedelta(minutes=1),
    },
    tags=['test', 'scheduler-ha']
)
def test_scheduler_ha():
    """
    Test DAG to verify scheduler HA coordination
    """
    
    @task
    def check_scheduler_processing():
        """Check which scheduler is processing this task"""
        import os
        from airflow.models import DagRun
        from airflow.utils.session import provide_session
        
        # Get current hostname
        hostname = socket.gethostname()
        
        # Get some scheduler info
        return {
            'processed_by_host': hostname,
            'timestamp': str(datetime.now()),
            'scheduler_test': 'SUCCESS'
        }
    
    @task 
    def verify_coordination():
        """Verify schedulers are coordinating properly"""
        return f"Scheduler coordination test at {datetime.now()}"
    
    # Task flow
    check_result = check_scheduler_processing()
    coordination_result = verify_coordination()
    
    check_result >> coordination_result

# Create DAG instance
dag_instance = test_scheduler_ha()
EOF

# Wait for DAG to be parsed
sleep 30
```

### **Test Scheduler HA:**
```bash
# On VM1 - Enable and trigger test DAG
airflow dags unpause test_scheduler_ha

# Wait for automatic execution (2-minute interval)
sleep 120

# Check which scheduler processed the DAG
airflow tasks states-for-dag-run test_scheduler_ha $(date +%Y-%m-%d)T$(date +%H:%M:%S)+00:00

# Check logs to see coordination
echo "=== VM1 Scheduler Logs ==="
sudo journalctl -u airflow-scheduler --since "5 minutes ago" | grep -i "test_scheduler_ha"

echo "=== VM13 Scheduler Logs ==="
ssh rocky@192.168.83.151 "sudo journalctl -u airflow-scheduler --since '5 minutes ago' | grep -i 'test_scheduler_ha'"
```

## 📋 **Step 1.8: Test Scheduler Failover**

### **Test 1: Stop VM1 Scheduler**
```bash
# On VM1 - Stop scheduler
sudo systemctl stop airflow-scheduler

# Wait 1 minute and check if VM13 continues processing
sleep 60

# Check VM13 is still processing
ssh rocky@192.168.83.151 "sudo journalctl -u airflow-scheduler --since '2 minutes ago' | tail -10"

# Restart VM1 scheduler
sudo systemctl start airflow-scheduler
```

### **Test 2: Stop VM13 Scheduler**
```bash
# On VM13 - Stop scheduler
sudo systemctl stop airflow-scheduler

# Wait 1 minute and check if VM1 continues processing
sleep 60

# Check VM1 is still processing
sudo journalctl -u airflow-scheduler --since "2 minutes ago" | tail -10

# Restart VM13 scheduler
sudo systemctl start airflow-scheduler
```

## ✅ **Phase 1 Verification Checklist**

Run these commands to verify Phase 1 completion:

```bash
# 1. Both schedulers running locally
echo "=== VM1 Scheduler Status ==="
sudo systemctl is-active airflow-scheduler  # On VM1

echo "=== VM13 Scheduler Status ==="
# Check VM13 from VM13 itself (login separately)
# ssh rocky@192.168.83.151
# sudo systemctl is-active airflow-scheduler

# 2. Database shows both schedulers
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT hostname, state, latest_heartbeat, job_type 
FROM job 
WHERE job_type = 'SchedulerJob' 
ORDER BY latest_heartbeat DESC 
LIMIT 5;
"

# 3. Test DAG is running
airflow dags state test_scheduler_ha $(date +%Y-%m-%d)

# 4. Both schedulers can process DAGs (check locally on each)
sudo journalctl -u airflow-scheduler --since "10 minutes ago" | grep -c "test_scheduler_ha"
# ssh rocky@192.168.83.151 "sudo journalctl -u airflow-scheduler --since '10 minutes ago' | grep -c 'test_scheduler_ha'"
```

## 🎯 **Expected Results**

✅ **VM1**: airflow-scheduler service active  
✅ **VM13**: airflow-scheduler service active  
✅ **Database**: Shows 2 active SchedulerJob entries  
✅ **DAG Processing**: Both schedulers coordinate DAG execution  
✅ **Failover**: If one scheduler stops, the other continues  

---

## 🚦 **Ready for Phase 2?**


1. Setup VM14 with HAProxy + Keepalived
2. Configure VIP (192.168.83.210) 
3. Test HAProxy failover
4. Update all services to use VIP

**Please run the verification checklist above before proceed to **Phase 2: Load Balancer HA**.**
