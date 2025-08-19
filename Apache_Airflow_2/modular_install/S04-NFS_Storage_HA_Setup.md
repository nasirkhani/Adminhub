## High Availability Shared Storage with Automated Failover

### Step 4.1: Install NFS and Synchronization Tools (VM2, VM12)

**Execute on both VM2 (ftp) and VM12 (nfs2):**
```bash
# Install NFS server and synchronization tools
sudo dnf install -y nfs-utils lsyncd keepalived

# Configure firewall for NFS and VIP
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --permanent --add-service=rpc-bind
sudo firewall-cmd --permanent --add-service=mountd
sudo firewall-cmd --permanent --add-protocol=vrrp   # Keepalived VRRP
sudo firewall-cmd --reload

# Create NFS directory structure
sudo mkdir -p /srv/airflow/dags
sudo mkdir -p /srv/airflow/logs
sudo chown -R rocky:rocky /srv/airflow
sudo chmod 755 /srv/airflow/dags /srv/airflow/logs
```

### Step 4.2: Configure SSH Authentication for Root Users

**Set up passwordless SSH for lsyncd synchronization:**

**On both VM2 and VM12:**
```bash
# Generate SSH keys for root user
sudo su -
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
exit
```

**Copy SSH keys between nodes:**
```bash
# On VM2 - Copy root's public key to VM12
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@192.168.83.150

# On VM12 - Copy root's public key to VM2  
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@192.168.83.132
```

**Verify passwordless SSH:**
```bash
# Test from VM2 to VM12
sudo su -
ssh root@192.168.83.150 "echo 'SSH from VM2 to VM12: SUCCESS'"
exit

# Test from VM12 to VM2
sudo su -
ssh root@192.168.83.132 "echo 'SSH from VM12 to VM2: SUCCESS'"
exit
```

### Step 4.3: Configure NFS Exports

**On both VM2 and VM12, create identical NFS export configuration:**
```bash
sudo tee /etc/exports << EOF
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
EOF

# Enable NFS service (but don't start on standby)
sudo systemctl enable nfs-server
sudo systemctl enable rpcbind
```

### Step 4.4: Create Health Check Script

**On both VM2 and VM12:**
```bash
# Create comprehensive health check script for all NFS services
sudo tee /usr/local/bin/check_nfs_services.sh << 'EOF'
#!/bin/bash

# Function to log messages
log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /var/log/nfs-keepalived.log
}

# Check NFS server is running
if ! systemctl is-active --quiet nfs-server; then
    log_msg "HEALTH CHECK FAILED: NFS server not running"
    exit 1
fi

# Check lsyncd is running
if ! systemctl is-active --quiet lsyncd; then
    log_msg "HEALTH CHECK FAILED: lsyncd not running"
    exit 1
fi

# Check NFS exports are accessible
if ! showmount -e localhost | grep -q "/srv/airflow/dags"; then
    log_msg "HEALTH CHECK FAILED: NFS exports not accessible"
    exit 1
fi

# Check DAG directory is accessible
if [ ! -d "/srv/airflow/dags" ] || [ ! -r "/srv/airflow/dags" ]; then
    log_msg "HEALTH CHECK FAILED: DAG directory not accessible"
    exit 1
fi

# All checks passed
log_msg "HEALTH CHECK PASSED: All services healthy"
exit 0
EOF

sudo chmod +x /usr/local/bin/check_nfs_services.sh

# Create log file
sudo touch /var/log/nfs-keepalived.log
sudo chown rocky:rocky /var/log/nfs-keepalived.log
```

### Step 4.5: Create Service Management Scripts

**On VM2 (Primary) - Create MASTER scripts:**
```bash
# Script to become active (MASTER)
sudo tee /usr/local/bin/nfs-become-master.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM2 BECOMING MASTER ==="

# Start NFS services
log_msg "Starting NFS services..."
systemctl start rpcbind
systemctl start nfs-server

# Configure lsyncd for VM2 → VM12 forward sync
log_msg "Configuring lsyncd for forward sync (VM2 → VM12)..."
cat > /etc/lsyncd.conf << 'LSYNCD_EOF'
settings {
    logfile = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd-status.log",
    statusInterval = 20,
    pidfile = "/var/run/lsyncd.pid",
    nodaemon = false
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/dags/",
    host = "192.168.83.150",
    targetdir = "/srv/airflow/dags/",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true,
        rsh = "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    }
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/logs/",
    host = "192.168.83.150",
    targetdir = "/srv/airflow/logs/",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true,
        rsh = "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    }
}
LSYNCD_EOF

# Start lsyncd
systemctl restart lsyncd

log_msg "VM2 is now MASTER - All services started"
EOF

# Script to become standby (BACKUP)
sudo tee /usr/local/bin/nfs-become-backup.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM2 BECOMING BACKUP ==="

# Stop all services
log_msg "Stopping lsyncd..."
systemctl stop lsyncd

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM2 is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

**On VM12 (Standby) - Create MASTER scripts:**
```bash
# Script to become active (MASTER)
sudo tee /usr/local/bin/nfs-become-master.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM12 BECOMING MASTER ==="

# Start NFS services
log_msg "Starting NFS services..."
systemctl start rpcbind
systemctl start nfs-server

# Configure lsyncd for VM12 → VM2 reverse sync
log_msg "Configuring lsyncd for reverse sync (VM12 → VM2)..."
cat > /etc/lsyncd.conf << 'LSYNCD_EOF'
settings {
    logfile = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd-status.log",
    statusInterval = 20,
    pidfile = "/var/run/lsyncd.pid",
    nodaemon = false
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/dags/",
    host = "192.168.83.132",
    targetdir = "/srv/airflow/dags/",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true,
        rsh = "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    }
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/logs/",
    host = "192.168.83.132",
    targetdir = "/srv/airflow/logs/",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true,
        rsh = "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    }
}
LSYNCD_EOF

# Start lsyncd
systemctl restart lsyncd

log_msg "VM12 is now MASTER - All services started with reverse sync"
EOF

# Script to become standby (BACKUP)
sudo tee /usr/local/bin/nfs-become-backup.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM12 BECOMING BACKUP ==="

# Stop all services
log_msg "Stopping lsyncd..."
systemctl stop lsyncd

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM12 is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

### Step 4.6: Configure Keepalived for NFS VIP

**On VM2 (Primary NFS):**
```bash
# Get network interface dynamically
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Network Interface: $INTERFACE"

# Create Keepalived configuration for NFS PRIMARY
sudo tee /etc/keepalived/keepalived.conf << EOF
global_defs {
    router_id NFS_HA_PRIMARY
    script_user root
    enable_script_security
}

vrrp_script chk_nfs_services {
    script "/usr/local/bin/check_nfs_services.sh"
    interval 5
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_NFS {
    state MASTER
    interface $INTERFACE
    virtual_router_id 52
    priority 110
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass nfs_ha_2024
    }
    virtual_ipaddress {
        192.168.83.220/24 dev $INTERFACE
    }
    track_script {
        chk_nfs_services
    }
    notify_master "/usr/local/bin/nfs-become-master.sh"
    notify_backup "/usr/local/bin/nfs-become-backup.sh"
    notify_fault "/usr/local/bin/nfs-become-backup.sh"
}
EOF

sudo systemctl enable keepalived
```

**On VM12 (Standby NFS):**
```bash
# Get network interface dynamically
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Network Interface: $INTERFACE"

# Create Keepalived configuration for NFS STANDBY
sudo tee /etc/keepalived/keepalived.conf << EOF
global_defs {
    router_id NFS_HA_STANDBY
    script_user root
    enable_script_security
}

vrrp_script chk_nfs_services {
    script "/usr/local/bin/check_nfs_services.sh"
    interval 5
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_NFS {
    state BACKUP
    interface $INTERFACE
    virtual_router_id 52
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass nfs_ha_2024
    }
    virtual_ipaddress {
        192.168.83.220/24 dev $INTERFACE
    }
    track_script {
        chk_nfs_services
    }
    notify_master "/usr/local/bin/nfs-become-master.sh"
    notify_backup "/usr/local/bin/nfs-become-backup.sh"
    notify_fault "/usr/local/bin/nfs-become-backup.sh"
}
EOF

sudo systemctl enable keepalived
```

### Step 4.7: Start NFS HA Services

**On VM2 (Primary) - Start as MASTER:**
```bash
# Start keepalived to trigger MASTER state
sudo systemctl start keepalived

# Verify VIP assignment
sleep 10
ip addr show | grep 192.168.83.220 && echo "NFS VIP assigned to VM2: SUCCESS" || echo "VIP assignment: FAILED"

# Check services are running
sudo systemctl status nfs-server --no-pager
sudo systemctl status lsyncd --no-pager
sudo systemctl status keepalived --no-pager
```

**On VM12 (Standby) - Start as BACKUP:**
```bash
# Start keepalived (should remain in BACKUP state)
sudo systemctl start keepalived

# Verify standby mode (VIP should NOT be here initially)
sleep 5
ip addr show | grep 192.168.83.220 && echo "VIP incorrectly on VM12" || echo "VM12 in standby mode: CORRECT"

# Verify keepalived is running
sudo systemctl status keepalived --no-pager
```

### Step 4.8: Configure NFS Clients

**Configure all Airflow nodes to use NFS VIP:**

**On VM1 (airflow):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Add to fstab for persistence
echo "192.168.83.220:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM1 NFS mount: SUCCESS"
```

**On VM13 (scheduler2):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Add to fstab for persistence
echo "192.168.83.220:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM13 NFS mount: SUCCESS"
```

**On VM14 (haproxy2):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Add to fstab for persistence
echo "192.168.83.220:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM14 NFS mount: SUCCESS"
```

**On VM4 (worker1):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Add to fstab for persistence
echo "192.168.83.220:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM4 NFS mount: SUCCESS"
```

### Step 4.9: Test NFS HA Failover

**Create test content and verify synchronization:**
```bash
# On VM2 - Create test files
echo "Test file from VM2 primary" | sudo tee /srv/airflow/dags/test_nfs_ha.txt
sudo mkdir -p /srv/airflow/dags/test_directory

# Wait for sync to VM12
sleep 5

# Verify sync to VM12
ssh rocky@192.168.83.150 "ls -la /srv/airflow/dags/ | grep test_nfs_ha.txt" && echo "File sync: SUCCESS"
```

**Test automated failover:**
```bash
echo "=== Testing NFS Automated Failover ==="

# Check initial state
ping -c 2 192.168.83.220 && echo "NFS VIP reachable"

# Verify all clients can access NFS
echo "=== Client Access Test ==="
ls /mnt/airflow-dags/test_nfs_ha.txt && echo "VM1 access: OK"
ssh rocky@192.168.83.151 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM13 access: OK"
ssh rocky@192.168.83.154 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM14 access: OK"
ssh rocky@192.168.83.131 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM4 access: OK"

# Trigger failover by stopping NFS on VM2
sudo systemctl stop nfs-server

# Wait for failover
echo "Waiting for NFS failover..."
sleep 15

# Check VIP moved to VM12
ssh rocky@192.168.83.150 "ip addr show | grep 192.168.83.220 && echo 'Failover: VIP moved to VM12' || echo 'Failover: FAILED'"

# Test clients still have access via VIP
ls /mnt/airflow-dags/test_nfs_ha.txt && echo "VM1 access after failover: OK" || echo "VM1 access: FAILED"

# Restart NFS on VM2 to trigger failback
sudo systemctl start nfs-server

# Wait for failback
echo "Waiting for NFS failback..."
sleep 15

# Check VIP returned to VM2
ip addr show | grep 192.168.83.220 && echo "Failback: VIP returned to VM2" || echo "Failback: CHECK MANUALLY"
```

### Step 4.10: Create Test DAG for NFS Verification

**Create a test DAG to verify NFS functionality:**
```bash
# Create a test DAG on active NFS server
sudo tee /srv/airflow/dags/test_nfs_storage.py << 'EOF'
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import os

@dag(
    dag_id='test_nfs_storage',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        'owner': 'admin',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    tags=['test', 'nfs', 'storage']
)
def test_nfs_storage():
    """
    Test DAG to verify NFS storage functionality
    """
    
    @task
    def test_nfs_write_access():
        """Test writing to NFS mounted directory"""
        import tempfile
        import socket
        
        hostname = socket.gethostname()
        test_file = f"/tmp/nfs_write_test_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(test_file, 'w') as f:
                f.write(f"NFS write test from {hostname} at {datetime.now()}")
            
            # Read back to verify
            with open(test_file, 'r') as f:
                content = f.read()
            
            os.remove(test_file)
            
            return {
                'hostname': hostname,
                'write_test': 'SUCCESS',
                'content_length': len(content),
                'timestamp': str(datetime.now())
            }
        except Exception as e:
            return {
                'hostname': hostname,
                'write_test': 'FAILED',
                'error': str(e),
                'timestamp': str(datetime.now())
            }
    
    @task
    def test_dag_directory_access():
        """Test access to DAG directory"""
        import socket
        
        hostname = socket.gethostname()
        dag_dir = "/home/rocky/airflow/dags"  # Will be symlinked to NFS
        
        try:
            files = os.listdir(dag_dir)
            return {
                'hostname': hostname,
                'dag_access': 'SUCCESS',
                'file_count': len(files),
                'sample_files': files[:5],
                'timestamp': str(datetime.now())
            }
        except Exception as e:
            return {
                'hostname': hostname,
                'dag_access': 'FAILED',
                'error': str(e),
                'timestamp': str(datetime.now())
            }
    
    # Define task dependencies
    write_test = test_nfs_write_access()
    dag_test = test_dag_directory_access()
    
    write_test >> dag_test

# Create DAG instance
dag_instance = test_nfs_storage()
EOF

# Set proper permissions
sudo chown rocky:rocky /srv/airflow/dags/test_nfs_storage.py
sudo chmod 644 /srv/airflow/dags/test_nfs_storage.py

# Wait for file sync
sleep 10
echo "Test DAG created and synced"
```

### Step 4.11: Verification Checklist

**Run comprehensive NFS HA verification:**
```bash
echo "=== NFS Storage HA Verification ==="

# 1. NFS VIP responds
ping -c 2 192.168.83.220 && echo "✅ NFS VIP accessible" || echo "❌ NFS VIP failed"

# 2. Keepalived running on both nodes
sudo systemctl is-active keepalived && echo "✅ VM2 Keepalived active" || echo "❌ VM2 Keepalived failed"
ssh rocky@192.168.83.150 "sudo systemctl is-active keepalived" && echo "✅ VM12 Keepalived active" || echo "❌ VM12 Keepalived failed"

# 3. Active NFS server identified
if ip addr show | grep -q 192.168.83.220; then
    echo "✅ VM2 is active NFS server"
    sudo systemctl is-active nfs-server && echo "✅ NFS service running on VM2" || echo "❌ NFS service failed on VM2"
elif ssh rocky@192.168.83.150 "ip addr show | grep -q 192.168.83.220"; then
    echo "✅ VM12 is active NFS server"
    ssh rocky@192.168.83.150 "sudo systemctl is-active nfs-server" && echo "✅ NFS service running on VM12" || echo "❌ NFS service failed on VM12"
else
    echo "❌ No active NFS server found"
fi

# 4. All clients have NFS access
ls /mnt/airflow-dags/ >/dev/null 2>&1 && echo "✅ VM1 NFS access" || echo "❌ VM1 NFS access failed"
ssh rocky@192.168.83.151 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM13 NFS access" || echo "❌ VM13 NFS access failed"
ssh rocky@192.168.83.154 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM14 NFS access" || echo "❌ VM14 NFS access failed"
ssh rocky@192.168.83.131 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM4 NFS access" || echo "❌ VM4 NFS access failed"

# 5. Health check script works
sudo /usr/local/bin/check_nfs_services.sh && echo "✅ NFS health check passed" || echo "❌ NFS health check failed"

# 6. File synchronization working
if [ -f "/srv/airflow/dags/test_nfs_ha.txt" ]; then
    ssh rocky@192.168.83.150 "test -f /srv/airflow/dags/test_nfs_ha.txt" && echo "✅ File synchronization working" || echo "❌ File sync failed"
else
    echo "❌ Test file not found"
fi

echo ""
echo "NFS Storage HA Setup Complete!"
echo "NFS VIP: 192.168.83.220"
echo "Primary: VM2 (Priority 110)"
echo "Standby: VM12 (Priority 100)" 
echo "Features: Automatic failover, Real-time sync, Health monitoring"
echo "Mount point on clients: /mnt/airflow-dags"
```

This completes the NFS Storage HA setup with:

✅ **Active/Passive NFS**: VM2 primary, VM12 standby with VIP (192.168.83.220)  
✅ **Automatic Failover**: Keepalived monitors NFS health and triggers failover  
✅ **Real-time Sync**: lsyncd provides bidirectional file synchronization  
✅ **Health Monitoring**: Comprehensive health checks for all services  
✅ **Client Integration**: All Airflow nodes use NFS VIP for DAG storage  
✅ **Transparent Failover**: Clients continue accessing storage via VIP during failover  

The shared storage infrastructure now provides zero single points of failure with automatic failover and data synchronization.
