# S04-NFS_Storage_HA_Setup.md

## High Availability Shared Storage with Automated Failover

### Step 4.1:  Install NFS and Synchronization Tools (VM4, VM5)

**Execute on both VM4 (nfs-1) and VM5 (nfs-2):**
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

**On both VM4 (nfs-1) and VM5 (nfs-2):**
```bash
# Generate SSH keys for root user
sudo su -
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
exit
```

**Copy SSH keys between nodes:**
```bash
# On VM4 (nfs-1) - Copy root's public key to VM5 (nfs-2)
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@nfs-2

# On VM5 (nfs-2) - Copy root's public key to VM4 (nfs-1)  
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@nfs-1
```

**🔧 Alternative SSH Key Distribution (using IP addresses):**
```bash
# If hostname resolution isn't working yet, use IP addresses
# CUSTOMIZE these values:
NFS_1_IP="192.168.1.13"  # Replace with VM4 IP
NFS_2_IP="192.168.1.14"  # Replace with VM5 IP

# On VM4 - copy to VM5 using IP
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@$NFS_2_IP

# On VM5 - copy to VM4 using IP
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@$NFS_1_IP
```

## or - make it by hand in both vms

```bash
cat <<EOF | sudo tee -a /root/.ssh/authorized_keys
<your_public_key_of_another_vm>
EOF
```


**Verify passwordless SSH:**
```bash
# Test from VM4 (nfs-1) to VM5 (nfs-2)
sudo su -
ssh root@nfs-2 "echo 'SSH from VM4 to VM5: SUCCESS'"
exit

# Test from VM5 (nfs-2) to VM4 (nfs-1)
sudo su -
ssh root@nfs-1 "echo 'SSH from VM5 to VM4: SUCCESS'"
exit
```

### Step 4.3: Configure NFS Exports

**⚠️ IMPORTANT: Replace `<NETWORK_SUBNET>` with your actual network subnet (e.g., 192.168.1.0/24)**

**On both VM4 (nfs-1) and VM5 (nfs-2), create identical NFS export configuration:**
```bash
sudo tee /etc/exports << EOF
# REPLACE_WITH_YOUR_NETWORK_SUBNET - Update the network range
/srv/airflow/dags <NETWORK_SUBNET>(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs <NETWORK_SUBNET>(rw,sync,no_root_squash,no_subtree_check)
EOF

# Enable NFS service (but don't start on standby)
sudo systemctl enable nfs-server
sudo systemctl enable rpcbind
```

**🔧 Network Subnet Replacement Helper:**
```bash
# Replace network subnet placeholder
# CUSTOMIZE this value with your actual network subnet:
NETWORK_SUBNET="192.168.1.0/24"  # Replace with your network subnet

# Replace placeholder in NFS exports
sudo sed -i "s/<NETWORK_SUBNET>/$NETWORK_SUBNET/g" /etc/exports

echo "NFS exports configuration updated:"
cat /etc/exports
```

### Step 4.4: Create Health Check Script

**On both VM4 (nfs-1) and VM5 (nfs-2):**
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

**⚠️ IMPORTANT: Replace `<NFS_*_IP>` placeholders with your actual NFS VM IP addresses**

**On VM4 (nfs-1 Primary) - Create MASTER scripts:**
```bash
# Script to become active (MASTER)
sudo tee /usr/local/bin/nfs-become-master.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM4 (nfs-1) BECOMING MASTER ==="

# Start NFS services
log_msg "Starting NFS services..."
systemctl start rpcbind
systemctl start nfs-server


# Start DAG processor
log_msg "Starting DAG processor..."
systemctl start airflow-dag-processor

# Configure lsyncd for VM4 → VM5 forward sync
log_msg "Configuring lsyncd for forward sync (nfs-1 → nfs-2)..."
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
    host = "<NFS_2_IP>",
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
    host = "<NFS_2_IP>",
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

log_msg "VM4 (nfs-1) is now MASTER - All services started"
EOF

# Script to become standby (BACKUP)
sudo tee /usr/local/bin/nfs-become-backup.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM4 (nfs-1) BECOMING BACKUP ==="

# Stop all services
log_msg "Stopping lsyncd..."
systemctl stop lsyncd

log_msg "Stopping DAG processor..."
systemctl stop airflow-dag-processor

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM4 (nfs-1) is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

**On VM5 (nfs-2 Standby) - Create MASTER scripts:**
```bash
# Script to become active (MASTER)
sudo tee /usr/local/bin/nfs-become-master.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM5 (nfs-2) BECOMING MASTER ==="

# Start NFS services
log_msg "Starting NFS services..."
systemctl start rpcbind
systemctl start nfs-server

# Start DAG processor
log_msg "Starting DAG processor..."
systemctl start airflow-dag-processor

# Configure lsyncd for VM5 → VM4 reverse sync
log_msg "Configuring lsyncd for reverse sync (nfs-2 → nfs-1)..."
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
    host = "<NFS_1_IP>",
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
    host = "<NFS_1_IP>",
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

log_msg "VM5 (nfs-2) is now MASTER - All services started with reverse sync"
EOF

# Script to become standby (BACKUP)
sudo tee /usr/local/bin/nfs-become-backup.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-keepalived.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG
}

log_msg "=== VM5 (nfs-2) BECOMING BACKUP ==="

# Stop all services
log_msg "Stopping lsyncd..."
systemctl stop lsyncd

log_msg "Stopping DAG processor..."
systemctl stop airflow-dag-processor

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM5 (nfs-2) is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

**🔧 IP Replacement Helper for Service Management Scripts:**
```bash
# Run this on both VM4 and VM5 after creating the scripts
# CUSTOMIZE these values with your actual NFS VM IPs:
NFS_1_IP="192.168.1.13"  # Replace with VM4 IP
NFS_2_IP="192.168.1.14"  # Replace with VM5 IP

# Replace IP placeholders in management scripts
sudo sed -i "s/<NFS_1_IP>/$NFS_1_IP/g" /usr/local/bin/nfs-become-*.sh
sudo sed -i "s/<NFS_2_IP>/$NFS_2_IP/g" /usr/local/bin/nfs-become-*.sh

echo "Service management scripts updated with IPs:"
echo "NFS_1_IP: $NFS_1_IP"
echo "NFS_2_IP: $NFS_2_IP"
```

### Step 4.6: Configure Keepalived for NFS VIP

**⚠️ IMPORTANT: Replace `<NFS_VIP>` with your chosen NFS VIP address**

**On VM4 (nfs-1 Primary NFS):**
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
        # REPLACE_WITH_YOUR_NFS_VIP
        <NFS_VIP>/24 dev $INTERFACE
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

**On VM5 (nfs-2 Standby NFS):**
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
        # REPLACE_WITH_YOUR_NFS_VIP
        <NFS_VIP>/24 dev $INTERFACE
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

**🔧 NFS VIP Replacement Helper:**
```bash
# Replace NFS VIP placeholder in keepalived configuration
# CUSTOMIZE this value with your chosen NFS VIP:
NFS_VIP="192.168.1.220"  # Replace with your chosen NFS VIP

# Replace placeholder in keepalived configuration
sudo sed -i "s/<NFS_VIP>/$NFS_VIP/g" /etc/keepalived/keepalived.conf

echo "Keepalived configuration updated. Verifying NFS VIP:"
grep -A 1 -B 1 "virtual_ipaddress" /etc/keepalived/keepalived.conf
```

### Step 4.7: Start NFS HA Services

**On VM4 (nfs-1 Primary) - Start as MASTER:**
```bash
# Start keepalived to trigger MASTER state
sudo systemctl start keepalived

# Verify VIP assignment
sleep 10
# REPLACE <NFS_VIP> with your actual NFS VIP address
ip addr show | grep <NFS_VIP> && echo "NFS VIP assigned to VM4: SUCCESS" || echo "VIP assignment: FAILED"

# Check services are running
sudo systemctl status nfs-server --no-pager
sudo systemctl status lsyncd --no-pager
sudo systemctl status keepalived --no-pager
```

**On VM5 (nfs-2 Standby) - Start as BACKUP:**
```bash
# Start keepalived (should remain in BACKUP state)
sudo systemctl start keepalived

# Verify standby mode (VIP should NOT be here initially)
sleep 5
# REPLACE <NFS_VIP> with your actual NFS VIP address
ip addr show | grep <NFS_VIP> && echo "VIP incorrectly on VM5" || echo "VM5 in standby mode: CORRECT"

# Verify keepalived is running
sudo systemctl status keepalived --no-pager
```

### Step 4.8: Configure NFS Clients

**⚠️ IMPORTANT: Replace `<NFS_VIP>` with your chosen NFS VIP address**

**Configure all Airflow nodes to use NFS VIP:**

**On VM1 (haproxy-1):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
# REPLACE_WITH_YOUR_NFS_VIP
sudo mount -t nfs <NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags
sudo mount -t nfs <NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs


# Add to fstab for persistence
echo "<NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "<NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM1 NFS mount: SUCCESS"
ls -la /mnt/airflow-logs/ && echo "VM1 NFS mount: SUCCESS"

```

**On VM2 (haproxy-2):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
# REPLACE_WITH_YOUR_NFS_VIP
sudo mount -t nfs <NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags
sudo mount -t nfs <NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs

# Add to fstab for persistence
echo "<NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "<NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM2 NFS mount: SUCCESS"
ls -la /mnt/airflow-logs/ && echo "VM2 NFS mount: SUCCESS"

```

**On VM3 (scheduler-2):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
# REPLACE_WITH_YOUR_NFS_VIP
sudo mount -t nfs <NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags
sudo mount -t nfs <NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs

# Add to fstab for persistence
echo "<NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "<NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM3 NFS mount: SUCCESS"
ls -la /mnt/airflow-logs/ && echo "VM3 NFS mount: SUCCESS"

```

**On VM12 (celery-1):**
```bash
# Create mount point and mount NFS via VIP
sudo mkdir -p /mnt/airflow-dags
# REPLACE_WITH_YOUR_NFS_VIP
sudo mount -t nfs <NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags
sudo mount -t nfs <NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs

# Add to fstab for persistence
echo "<NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "<NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Verify mount
ls -la /mnt/airflow-dags/ && echo "VM12 NFS mount: SUCCESS"
ls -la /mnt/airflow-logs/ && echo "VM12 NFS mount: SUCCESS"

```

**🔧 Automated NFS Client Configuration Script: (this dosent conclude /mnt/airflow-logs and is inmoplete)**
```bash
# Create script to configure NFS clients with your VIP
# CUSTOMIZE this value:
NFS_VIP="192.168.1.220"  # Replace with your chosen NFS VIP

# Create client configuration script
sudo tee /tmp/configure_nfs_clients.sh << EOF
#!/bin/bash
NFS_VIP="$NFS_VIP"

echo "Configuring NFS client with VIP: \$NFS_VIP"

# Create mount point
sudo mkdir -p /mnt/airflow-dags

# Mount NFS share
if sudo mount -t nfs \$NFS_VIP:/srv/airflow/dags /mnt/airflow-dags; then
    echo "✅ NFS mounted successfully"
    
    # Add to fstab
    if ! grep -q "\$NFS_VIP:/srv/airflow/dags" /etc/fstab; then
        echo "\$NFS_VIP:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
        echo "✅ Added to /etc/fstab"
    fi
    
    # Verify mount
    ls -la /mnt/airflow-dags/ && echo "✅ NFS access verified"
else
    echo "❌ NFS mount failed"
fi
EOF

chmod +x /tmp/configure_nfs_clients.sh
# Run this script on each client VM after customizing NFS_VIP
```

### Step 4.9: Test NFS HA Failover

**Create test content and verify synchronization (run from active NFS server):**
```bash
# On VM4 (nfs-1) - Create test files
echo "Test file from VM4 (nfs-1) primary" | sudo tee /srv/airflow/dags/test_nfs_ha.txt
sudo mkdir -p /srv/airflow/dags/test_directory

# Wait for sync to VM5
sleep 5

# Verify sync to VM5 (nfs-2)
ssh rocky@nfs-2 "ls -la /srv/airflow/dags/ | grep test_nfs_ha.txt" && echo "File sync: SUCCESS"
```

**Test automated failover:**
```bash
# CUSTOMIZE with your actual NFS VIP:
NFS_VIP="192.168.1.220"  # Replace with your actual NFS VIP

echo "=== Testing NFS Automated Failover ==="

# Check initial state
ping -c 2 $NFS_VIP && echo "NFS VIP reachable"

# Verify all clients can access NFS
echo "=== Client Access Test ==="
ls /mnt/airflow-dags/test_nfs_ha.txt && echo "VM1 access: OK"
ssh rocky@haproxy-2 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM2 access: OK"
ssh rocky@scheduler-2 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM3 access: OK"
ssh rocky@celery-1 "ls /mnt/airflow-dags/test_nfs_ha.txt" && echo "VM12 access: OK"

# Trigger failover by stopping NFS on VM4 (nfs-1)
sudo systemctl stop nfs-server

# Wait for failover
echo "Waiting for NFS failover..."
sleep 15

# Check VIP moved to VM5 (nfs-2)
ssh rocky@nfs-2 "ip addr show | grep $NFS_VIP && echo 'Failover: VIP moved to VM5' || echo 'Failover: FAILED'"

# Test clients still have access via VIP
ls /mnt/airflow-dags/test_nfs_ha.txt && echo "VM1 access after failover: OK" || echo "VM1 access: FAILED"

# Restart NFS on VM4 (nfs-1) to trigger failback
sudo systemctl start nfs-server

# Wait for failback
echo "Waiting for NFS failback..."
sleep 15

# Check VIP returned to VM4 (nfs-1)
ip addr show | grep $NFS_VIP && echo "Failback: VIP returned to VM4" || echo "Failback: CHECK MANUALLY"
```

### Step 4.10: Create Test DAG for NFS Verification

**Create a test DAG on active NFS server:**
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

**Run comprehensive NFS HA verification (customize VIP addresses first):**
```bash
# CUSTOMIZE this value:
NFS_VIP="192.168.1.220"  # Replace with your actual NFS VIP

echo "=== NFS Storage HA Verification ==="

# 1. NFS VIP responds
ping -c 2 $NFS_VIP && echo "✅ NFS VIP accessible" || echo "❌ NFS VIP failed"

# 2. Keepalived running on both nodes
sudo systemctl is-active keepalived && echo "✅ VM4 Keepalived active" || echo "❌ VM4 Keepalived failed"
ssh rocky@nfs-2 "sudo systemctl is-active keepalived" && echo "✅ VM5 Keepalived active" || echo "❌ VM5 Keepalived failed"

# 3. Active NFS server identified
if ip addr show | grep -q $NFS_VIP; then
    echo "✅ VM4 (nfs-1) is active NFS server"
    sudo systemctl is-active nfs-server && echo "✅ NFS service running on VM4" || echo "❌ NFS service failed on VM4"
elif ssh rocky@nfs-2 "ip addr show | grep -q $NFS_VIP"; then
    echo "✅ VM5 (nfs-2) is active NFS server"
    ssh rocky@nfs-2 "sudo systemctl is-active nfs-server" && echo "✅ NFS service running on VM5" || echo "❌ NFS service failed on VM5"
else
    echo "❌ No active NFS server found"
fi

# 4. All clients have NFS access
ls /mnt/airflow-dags/ >/dev/null 2>&1 && echo "✅ VM1 NFS access" || echo "❌ VM1 NFS access failed"
ssh rocky@haproxy-2 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM2 NFS access" || echo "❌ VM2 NFS access failed"
ssh rocky@scheduler-2 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM3 NFS access" || echo "❌ VM3 NFS access failed"
ssh rocky@celery-1 "ls /mnt/airflow-dags/" >/dev/null 2>&1 && echo "✅ VM12 NFS access" || echo "❌ VM12 NFS access failed"

# 5. Health check script works
sudo /usr/local/bin/check_nfs_services.sh && echo "✅ NFS health check passed" || echo "❌ NFS health check failed"

# 6. File synchronization working
if [ -f "/srv/airflow/dags/test_nfs_ha.txt" ]; then
    ssh rocky@nfs-2 "test -f /srv/airflow/dags/test_nfs_ha.txt" && echo "✅ File synchronization working" || echo "❌ File sync failed"
else
    echo "❌ Test file not found"
fi

echo ""
echo "NFS Storage HA Setup Complete!"
echo "NFS VIP: $NFS_VIP"
echo "Primary: VM4 (nfs-1) - Priority 110"
echo "Standby: VM5 (nfs-2) - Priority 100" 
echo "Features: Automatic failover, Real-time sync, Health monitoring"
echo "Mount point on clients: /mnt/airflow-dags"
```

**🔧 Complete NFS Verification Script:**
```bash
# Create comprehensive NFS verification script
# CUSTOMIZE this value:
NFS_VIP="192.168.1.220"  # Replace with your actual NFS VIP

sudo tee /usr/local/bin/verify_nfs_ha.sh << EOF
#!/bin/bash
NFS_VIP="$NFS_VIP"

echo "=== NFS HA Verification Script ==="
echo "NFS VIP: \$NFS_VIP"
echo ""

# Test NFS VIP accessibility
if ping -c 2 \$NFS_VIP >/dev/null 2>&1; then
    echo "✅ NFS VIP accessible"
    
    # Test NFS mount
    if showmount -e \$NFS_VIP | grep -q "/srv/airflow/dags"; then
        echo "✅ NFS exports available"
    else
        echo "❌ NFS exports not available"
    fi
else
    echo "❌ NFS VIP not accessible"
fi

# Check which node has the VIP
if ip addr show | grep -q \$NFS_VIP; then
    echo "✅ VM4 (nfs-1) has NFS VIP"
elif ssh -o ConnectTimeout=5 rocky@nfs-2 "ip addr show | grep -q \$NFS_VIP" 2>/dev/null; then
    echo "✅ VM5 (nfs-2) has NFS VIP"
else
    echo "❌ NFS VIP not found on either node"
fi

# Test client access
if ls /mnt/airflow-dags >/dev/null 2>&1; then
    echo "✅ NFS client access working"
else
    echo "❌ NFS client access failed"
fi

echo ""
echo "Verification complete"
EOF

sudo chmod +x /usr/local/bin/verify_nfs_ha.sh
# Run after customizing: sudo /usr/local/bin/verify_nfs_ha.sh
```

This completes the NFS Storage HA setup with:

✅ **Active/Passive NFS**: VM4 (nfs-1) primary, VM5 (nfs-2) standby with VIP (`<NFS_VIP>`)  
✅ **Automatic Failover**: Keepalived monitors NFS health and triggers failover  
✅ **Real-time Sync**: lsyncd provides bidirectional file synchronization  
✅ **Health Monitoring**: Comprehensive health checks for all services  
✅ **Client Integration**: All Airflow nodes use NFS VIP for DAG storage  
✅ **Transparent Failover**: Clients continue accessing storage via VIP during failover  

The shared storage infrastructure now provides zero single points of failure with automatic failover and data synchronization.

**Next Steps**: Once this NFS Storage HA setup is complete and verified, proceed to **S05-Airflow_Core_Components_Installation.md** for Apache Airflow installation and configuration.






