# 🔧 Simple Active-Passive NFS + DAG Processor HA Setup

## **🎯 Architecture Overview - Option A**

### **Simple Active-Passive Model:**
```
VM2 (192.168.83.132) - PRIMARY:
├── NFS Server (ACTIVE)
├── DAG Processor (ACTIVE)
├── DAG Files (MASTER COPY)
└── Real-time sync to VM12

VM12 (192.168.83.150) - STANDBY:
├── NFS Server (STOPPED)
├── DAG Processor (STOPPED) 
├── DAG Files (SYNCED COPY)
└── Ready to take over manually or automatically
```

### **Key Benefits:**
- ✅ **Simple setup** - No complex clustering
- ✅ **Easy maintenance** - Clear active/passive roles
- ✅ **File sync** - Real-time replication with rsync/lsyncd
- ✅ **Manual failover** - Controlled switching when needed
- ✅ **No split-brain** - Only one active at a time

---

## **🛠️ PHASE 1: Setup VM12 (Standby Node)**

### **Step 1.1: Prepare VM12 Basic Setup**

```bash
# SSH into VM12
ssh rocky@192.168.83.150

# Set hostname
sudo nmcli general hostname nfs2
sudo reboot

# After reboot, SSH back
ssh rocky@192.168.83.150

# Update system
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel
sudo dnf install -y nfs-utils rsync lsyncd

# Update /etc/hosts
sudo tee -a /etc/hosts << EOF
192.168.83.129 airflow
192.168.83.131 worker1
192.168.83.132 ftp
192.168.83.133 card1
192.168.83.146 worker2
192.168.83.150 nfs2
EOF
```

### **Step 1.2: Install Airflow on VM12**

```bash
# Create airflow directory and set environment
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with same version as VM2
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"

# Copy configuration and modules from VM2
scp rocky@192.168.83.132:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@192.168.83.132:/home/rocky/airflow/config ~/airflow/
scp -r rocky@192.168.83.132:/home/rocky/airflow/utils ~/airflow/

# Create __init__.py files
touch ~/airflow/__init__.py
touch ~/airflow/config/__init__.py
touch ~/airflow/utils/__init__.py
```

### **Step 1.3: Create NFS Directory Structure on VM12**

```bash
# Create identical directory structure as VM2
sudo mkdir -p /srv/airflow/dags
sudo mkdir -p /srv/airflow/logs
sudo chown -R rocky:rocky /srv/airflow
sudo chmod 755 /srv/airflow/dags
sudo chmod 755 /srv/airflow/logs

# Create symlink for airflow dags (same as VM2)
ln -s /srv/airflow/dags /home/rocky/airflow/dags
```

---

## **🔄 PHASE 2: Setup File Synchronization**

### **Step 2.1: SSH Key Setup for Passwordless Sync**

**On VM2 (Primary):**
```bash
# Generate SSH key if not exists
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
fi

# Copy public key to VM12
ssh-copy-id rocky@192.168.83.150

# Test passwordless connection
ssh rocky@192.168.83.150 "echo 'SSH connection successful'"
```

**On VM12 (Standby):**
```bash
# Generate SSH key for reverse sync if needed
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
fi

# Copy public key to VM2 (for reverse sync capability)
ssh-copy-id rocky@192.168.83.132
```

### **Step 2.2: Setup Lsyncd for Real-time Sync on VM2**

**On VM2 (Primary):**
```bash
# Install lsyncd
sudo dnf install -y lsyncd

# Create lsyncd configuration
sudo tee /etc/lsyncd.conf << EOF
settings {
    logfile = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd-status.log",
    statusInterval = 20,
    pidfile = "/var/run/lsyncd.pid"
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/dags",
    host = "192.168.83.150",
    targetdir = "/srv/airflow/dags",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true
    },
    ssh = {
        port = 22,
        options = {"-o", "StrictHostKeyChecking=no"}
    }
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/logs",
    host = "192.168.83.150", 
    targetdir = "/srv/airflow/logs",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true
    },
    ssh = {
        port = 22,
        options = {"-o", "StrictHostKeyChecking=no"}
    }
}
EOF

# Set proper permissions
sudo chmod 644 /etc/lsyncd.conf

# Enable and start lsyncd
sudo systemctl enable lsyncd
sudo systemctl start lsyncd
sudo systemctl status lsyncd
```

### **Step 2.3: Initial Sync from VM2 to VM12**

```bash
# On VM2 - Do initial full sync
rsync -avz --delete /srv/airflow/dags/ rocky@192.168.83.150:/srv/airflow/dags/
rsync -avz --delete /srv/airflow/logs/ rocky@192.168.83.150:/srv/airflow/logs/

# Verify sync on VM12
ssh rocky@192.168.83.150 "ls -la /srv/airflow/dags/"
ssh rocky@192.168.83.150 "ls -la /srv/airflow/logs/"
```

---

## **🔧 PHASE 3: Configure Services on VM12**

### **Step 3.1: Setup NFS Server on VM12 (Disabled by Default)**

```bash
# On VM12 - Install and configure NFS but don't start
sudo dnf install -y nfs-utils

# Configure exports identical to VM2
sudo tee /etc/exports << EOF
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
EOF

# Enable but don't start (standby mode)
sudo systemctl enable nfs-server
sudo systemctl enable rpcbind
# Don't start - will start during failover
```

### **Step 3.2: Setup DAG Processor Service on VM12 (Disabled by Default)**

```bash
# On VM12 - Create DAG processor service
sudo tee /etc/systemd/system/airflow-dag-processor.service << EOF
[Unit]
Description=Airflow Standalone DAG Processor (Standby)
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
SyslogIdentifier=airflow-dag-processor-standby
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
# Don't start - will start during failover
```

---

## **🚀 PHASE 4: Create Failover Scripts**

### **Step 4.1: Create Failover Scripts on VM2 (Primary)**

```bash
# On VM2 - Create script to gracefully become standby
sudo tee /usr/local/bin/nfs-become-standby.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM2 becoming STANDBY" >> $LOG

# Stop services gracefully
systemctl stop airflow-dag-processor
systemctl stop nfs-server
systemctl stop lsyncd

# Final sync to standby
echo "$(date): Final sync to VM12" >> $LOG
rsync -avz --delete /srv/airflow/dags/ rocky@192.168.83.150:/srv/airflow/dags/
rsync -avz --delete /srv/airflow/logs/ rocky@192.168.83.150:/srv/airflow/logs/

echo "$(date): VM2 is now STANDBY" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-standby.sh
```

```bash
# On VM2 - Create script to become active again
sudo tee /usr/local/bin/nfs-become-active.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM2 becoming ACTIVE" >> $LOG

# Sync any changes from VM12 back to VM2
echo "$(date): Syncing changes from VM12" >> $LOG
rsync -avz rocky@192.168.83.150:/srv/airflow/dags/ /srv/airflow/dags/
rsync -avz rocky@192.168.83.150:/srv/airflow/logs/ /srv/airflow/logs/

# Start services
systemctl start nfs-server
systemctl start airflow-dag-processor
systemctl start lsyncd

echo "$(date): VM2 is now ACTIVE" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-active.sh
```

### **Step 4.2: Create Failover Scripts on VM12 (Standby)**

```bash
# On VM12 - Create script to become active
sudo tee /usr/local/bin/nfs-become-active.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM12 becoming ACTIVE" >> $LOG

# Start services
systemctl start rpcbind
systemctl start nfs-server
systemctl start airflow-dag-processor

# Setup reverse sync to VM2 (if VM2 comes back)
echo "$(date): VM12 is now ACTIVE" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-active.sh
```

```bash
# On VM12 - Create script to become standby
sudo tee /usr/local/bin/nfs-become-standby.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM12 becoming STANDBY" >> $LOG

# Stop services
systemctl stop airflow-dag-processor
systemctl stop nfs-server

echo "$(date): VM12 is now STANDBY" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-standby.sh
```

---

## **🔍 PHASE 5: Testing and Validation**

### **Step 5.1: Test File Synchronization**

```bash
# On VM2 - Create test file
echo "Test sync $(date)" > /srv/airflow/dags/sync_test.txt

# Wait 5 seconds for lsyncd
sleep 5

# Check on VM12 - should be identical
ssh rocky@192.168.83.150 "cat /srv/airflow/dags/sync_test.txt"

# Clean up test
rm /srv/airflow/dags/sync_test.txt
```

### **Step 5.2: Test Manual Failover**

**Simulate VM2 failure:**
```bash
# On VM2 - Simulate going down
sudo /usr/local/bin/nfs-become-standby.sh

# On VM12 - Take over as active
sudo /usr/local/bin/nfs-become-active.sh

# Update client mounts to point to VM12
# On VM1, VM4, VM11 - temporarily update mounts:
sudo umount /home/rocky/airflow/dags
sudo mount -t nfs 192.168.83.150:/srv/airflow/dags /home/rocky/airflow/dags

# Verify DAGs still accessible
ls -la /home/rocky/airflow/dags/
```

**Restore VM2 as primary:**
```bash
# On VM12 - Become standby again
sudo /usr/local/bin/nfs-become-standby.sh

# On VM2 - Become active again
sudo /usr/local/bin/nfs-become-active.sh

# Update client mounts back to VM2
# On VM1, VM4, VM11:
sudo umount /home/rocky/airflow/dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /home/rocky/airflow/dags
```

### **Step 5.3: Test DAG Processing HA**

```bash
# Create test DAG on VM2
sudo tee /srv/airflow/dags/test_dag_processor_ha.py << 'EOF'
from datetime import datetime
from airflow.decorators import dag, task

@dag(
    dag_id='test_dag_processor_ha',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False
)
def test_dag_processor_ha():
    
    @task
    def simple_task():
        return "DAG Processor HA test successful!"
    
    result = simple_task()

dag = test_dag_processor_ha()
EOF

# Wait for sync and DAG processor to pick up
sleep 10

# Check if DAG appears in Airflow UI
airflow dags list | grep test_dag_processor_ha
```

---

## **📊 PHASE 6: Monitoring and Maintenance**

### **Step 6.1: Monitoring Commands**

```bash
# Check sync status
sudo tail -f /var/log/lsyncd.log

# Check which node is active
systemctl is-active nfs-server  # On both VM2 and VM12

# Verify file sync
diff -r /srv/airflow/dags/ <(ssh rocky@192.168.83.150 "find /srv/airflow/dags -type f -exec cat {} \;")
```

### **Step 6.2: Health Check Script**

```bash
# On VM2 - Create health monitoring
sudo tee /usr/local/bin/nfs-health-check.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-health.log"

# Check essential services
if ! systemctl is-active --quiet nfs-server; then
    echo "$(date): WARNING - NFS server not running" >> $LOG
fi

if ! systemctl is-active --quiet airflow-dag-processor; then
    echo "$(date): WARNING - DAG processor not running" >> $LOG
fi

if ! systemctl is-active --quiet lsyncd; then
    echo "$(date): WARNING - File sync not running" >> $LOG
fi

# Check connectivity to standby
if ! ping -c 1 192.168.83.150 > /dev/null 2>&1; then
    echo "$(date): WARNING - Cannot reach standby VM12" >> $LOG
fi
EOF

sudo chmod +x /usr/local/bin/nfs-health-check.sh

# Add to crontab for regular health checks
echo "*/5 * * * * /usr/local/bin/nfs-health-check.sh" | sudo crontab -
```

---

## **✅ Final Architecture Status**

### **Normal Operation:**
```
VM2 (192.168.83.132) - ACTIVE:
├── ✅ NFS Server (serving clients)
├── ✅ DAG Processor (processing DAGs)
├── ✅ Lsyncd (syncing to VM12)
└── ✅ All client connections

VM12 (192.168.83.150) - STANDBY:
├── ❌ NFS Server (stopped)
├── ❌ DAG Processor (stopped)
├── ✅ Files (synced and ready)
└── ⏳ Ready for manual failover
```

### **Failover Benefits:**
- ✅ **Simple maintenance** - Clear scripts for switching
- ✅ **No data loss** - Real-time file synchronization
- ✅ **Manual control** - You decide when to failover
- ✅ **Easy troubleshooting** - Clear active/passive roles
- ✅ **Quick recovery** - 30-60 second failover time

### **Manual Failover Process:**
```bash
# Planned maintenance on VM2:
1. sudo /usr/local/bin/nfs-become-standby.sh    # On VM2
2. sudo /usr/local/bin/nfs-become-active.sh     # On VM12
3. Update client mounts to VM12
4. Perform maintenance on VM2
5. Reverse process when ready
```

**Your NFS + DAG Processor now has simple, reliable HA protection! 🎉**
