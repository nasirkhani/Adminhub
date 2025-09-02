## Architecture Overview

```
Normal State (VM2 Active):
VM2 (192.168.83.132) - MASTER:
├── NFS Server + VIP (192.168.83.220)
├── DAG Processor  
├── lsyncd (VM2 → VM12)
└── Keepalived (Priority 110)

VM12 (192.168.83.150) - BACKUP:
├── NFS Server (stopped)
├── DAG Processor (stopped)
├── lsyncd (stopped)
└── Keepalived (Priority 100)

Failover State (VM12 Active):
VM2 (192.168.83.132) - BACKUP:
├── NFS Server (stopped)
├── DAG Processor (stopped)
├── lsyncd (stopped)
└── Keepalived (Priority 110, but in BACKUP)

VM12 (192.168.83.150) - MASTER:
├── NFS Server + VIP (192.168.83.220)
├── DAG Processor
├── lsyncd (VM12 → VM2) [Reverse Sync]
└── Keepalived (Priority 100, but ACTIVE)
```

---

## Step 4.1: Install Keepalived on VM2 and VM12

```bash
# On VM2 and VM12
sudo dnf install -y keepalived

# Configure firewall for VRRP
sudo firewall-cmd --permanent --add-protocol=vrrp
sudo firewall-cmd --reload
```

## Step 4.2: Set Up SSH Authentication for lsyncd

### Generate SSH Keys for Root on Both VMs

```bash
# On VM2
sudo su -
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""

# On VM12
sudo su -
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
```

### Copy SSH Public Keys Between VMs

```bash
# On VM2 (copy root's public key to VM12's root authorized_keys)
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@192.168.83.150

# On VM12 (copy root's public key to VM2's root authorized_keys)
sudo ssh-copy-id -i /root/.ssh/id_rsa.pub root@192.168.83.132
```

### Verify Passwordless SSH

```bash
# On VM2
sudo su -
ssh root@192.168.83.150 "echo 'SSH from VM2 to VM12 successful'"
exit

# On VM12
sudo su -
ssh root@192.168.83.132 "echo 'SSH from VM12 to VM2 successful'"
exit
```

## Step 4.3: Create Health Check Script

### On VM2 and VM12 - Create Comprehensive Health Check

```bash
# Create health check script that monitors all three services
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

# Check DAG processor is running
if ! systemctl is-active --quiet airflow-dag-processor; then
    log_msg "HEALTH CHECK FAILED: DAG processor not running"
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

## Step 4.4: Create Service Management Scripts

### On VM2 - Create MASTER (Active) Script

```bash
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

# Start DAG processor
log_msg "Starting DAG processor..."
systemctl start airflow-dag-processor

# Configure lsyncd for VM2 → VM12 sync
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

sudo chmod +x /usr/local/bin/nfs-become-master.sh
```

### On VM2 - Create BACKUP (Standby) Script

```bash
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

log_msg "Stopping DAG processor..."
systemctl stop airflow-dag-processor

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM2 is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-backup.sh
```

### On VM12 - Create MASTER (Active) Script

```bash
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

# Start DAG processor
log_msg "Starting DAG processor..."
systemctl start airflow-dag-processor

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

sudo chmod +x /usr/local/bin/nfs-become-master.sh
```

### On VM12 - Create BACKUP (Standby) Script

```bash
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

log_msg "Stopping DAG processor..."
systemctl stop airflow-dag-processor

log_msg "Stopping NFS services..."
systemctl stop nfs-server

log_msg "VM12 is now BACKUP - All services stopped"
EOF

sudo chmod +x /usr/local/bin/nfs-become-backup.sh
```

## Step 4.5: Configure Keepalived

### On VM2 (Primary) - Keepalived Configuration

```bash
# Get network interface
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Interface: $INTERFACE"

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
sudo systemctl start keepalived
```

### On VM12 (Standby) - Keepalived Configuration

```bash
# Get network interface
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Interface: $INTERFACE"

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
sudo systemctl start keepalived
```

## Step 4.6: Restart Services to Apply SSH Configuration

```bash
# On VM2 and VM12
sudo systemctl daemon-reload
sudo systemctl restart lsyncd
sudo systemctl restart keepalived
```

## Step 4.7: Update All Client Mounts to Use NFS VIP

### Update VM1 (airflow)

```bash
# On VM1 - Update mount to use VIP
sudo umount /mnt/airflow-dags

# Update fstab
sudo sed -i 's|192.168.83.132:/srv/airflow/dags|192.168.83.220:/srv/airflow/dags|g' /etc/fstab

# Mount with new VIP
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Verify mount
ls -la /mnt/airflow-dags/
```

### Update VM13 (scheduler2)

```bash
# On VM13 - Update mount to use VIP
sudo umount /mnt/airflow-dags

# Update fstab
sudo sed -i 's|192.168.83.132:/srv/airflow/dags|192.168.83.220:/srv/airflow/dags|g' /etc/fstab

# Mount with new VIP
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Verify mount
ls -la /mnt/airflow-dags/
```

### Update VM14 (haproxy2)

```bash
# On VM14 - Update mount to use VIP
sudo umount /mnt/airflow-dags

# Update fstab
sudo sed -i 's|192.168.83.132:/srv/airflow/dags|192.168.83.220:/srv/airflow/dags|g' /etc/fstab

# Mount with new VIP
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Verify mount
ls -la /mnt/airflow-dags/
```

### Update VM4 (worker1)

```bash
# On VM4 - Update mount to use VIP
sudo umount /mnt/airflow-dags

# Update fstab
sudo sed -i 's|192.168.83.132:/srv/airflow/dags|192.168.83.220:/srv/airflow/dags|g' /etc/fstab

# Mount with new VIP
sudo mount -t nfs 192.168.83.220:/srv/airflow/dags /mnt/airflow-dags

# Verify mount
ls -la /mnt/airflow-dags/
```

## Step 4.8: Test Automated Failover

### Verify Initial State

```bash
# Check VIP location
ping -c 3 192.168.83.220

# Check which VM has VIP
ip addr show | grep 192.168.83.220 && echo "VIP on VM2" || echo "VIP NOT on VM2"
ssh rocky@192.168.83.150 "ip addr show | grep 192.168.83.220 && echo 'VIP on VM12' || echo 'VIP NOT on VM12'"

# Check services on VM2
sudo systemctl status nfs-server airflow-dag-processor lsyncd

# Check all clients can access NFS via VIP
ls -la /mnt/airflow-dags/ && echo "VM1 NFS access: OK"
ssh rocky@192.168.83.151 "ls -la /mnt/airflow-dags/ && echo 'VM13 NFS access: OK'"
ssh rocky@192.168.83.154 "ls -la /mnt/airflow-dags/ && echo 'VM14 NFS access: OK'"
ssh rocky@192.168.83.131 "ls -la /mnt/airflow-dags/ && echo 'VM4 NFS access: OK'"
```

### Test 1: NFS Service Failure

```bash
# On VM2 - Stop NFS service to trigger failover
sudo systemctl stop nfs-server

# Wait for failover (should be fast)
sleep 15

# Check VIP moved to VM12
ssh rocky@192.168.83.150 "ip addr show | grep 192.168.83.220 && echo 'Failover: VIP moved to VM12' || echo 'Failover: FAILED'"

# Check all clients still have NFS access
ls -la /mnt/airflow-dags/ && echo "VM1 NFS after failover: OK"

# Check VM12 is now running all services
ssh rocky@192.168.83.150 "sudo systemctl status nfs-server airflow-dag-processor lsyncd"

# Manual recovery test - restart NFS on VM2 to trigger failback
sudo systemctl start nfs-server
sleep 15

# Check VIP moved back to VM2 (higher priority)
ip addr show | grep 192.168.83.220 && echo "Failback: VIP back on VM2" || echo "Failback: FAILED"
```

### Test 2: DAG Processor Failure

```bash
# On VM2 - Stop DAG processor to trigger failover
sudo systemctl stop airflow-dag-processor

# Wait for failover
sleep 15

# Check VIP moved to VM12
ssh rocky@192.168.83.150 "ip addr show | grep 192.168.83.220 && echo 'DAG processor failover: SUCCESS'"

# Restart DAG processor to trigger failback
sudo systemctl start airflow-dag-processor
sleep 15

# Check failback
ip addr show | grep 192.168.83.220 && echo "DAG processor failback: SUCCESS"
```

### Test 3: lsyncd Failure

```bash
# On VM2 - Stop lsyncd to trigger failover
sudo systemctl stop lsyncd

# Wait for failover
sleep 15

# Check VIP moved to VM12
ssh rocky@192.168.83.150 "ip addr show | grep 192.168.83.220 && echo 'lsyncd failover: SUCCESS'"

# Restart lsyncd to trigger failback
sudo systemctl start lsyncd
sleep 15

# Check failback
ip addr show | grep 192.168.83.220 && echo "lsyncd failback: SUCCESS"
```

## Step 4.9: Monitor Logs

```bash
# Monitor keepalived logs on both VMs
echo "=== VM2 Keepalived Logs ==="
sudo journalctl -u keepalived --since "10 minutes ago" | grep -E "(MASTER|BACKUP|VIP|transition)"

echo "=== VM12 Keepalived Logs ==="
ssh rocky@192.168.83.150 "sudo journalctl -u keepalived --since '10 minutes ago' | grep -E '(MASTER|BACKUP|VIP|transition)'"

# Check custom logs
echo "=== NFS HA Logs ==="
tail -20 /var/log/nfs-keepalived.log
ssh rocky@192.168.83.150 "tail -20 /var/log/nfs-keepalived.log"

# Monitor lsyncd logs
sudo journalctl -u lsyncd -f
```

## Step 4.10: Service Monitoring Setup

### Simple Service Monitor Command

```bash
watch -n 1 'printf "%-20s %s\n" "airflow-dag:" "$(systemctl is-active airflow-dag-processor.service)" \
"lsyncd:" "$(systemctl is-active lsyncd.service)" \
"keepalived:" "$(systemctl is-active keepalived.service)" \
"nfs-server:" "$(systemctl is-active nfs-server.service)"'
```

### TMUX Service Monitor Setup

```bash
# Start new session
tmux new-session -s "service_monitor"

# Split panes using:
# Ctrl+B %       - Vertical split
# Ctrl+B "       - Horizontal split
# Ctrl+B Arrow   - Switch panes

# Run in each pane:
watch -n 1 "systemctl status SERVICE | grep -E 'Active|service'"

# TMUX commands:
# Ctrl+B d          - Detach session
# tmux attach -t service_monitor  - Reattach
# Ctrl+B x          - Kill pane
```

## Phase 4 Complete Verification

```bash
# 1. VIP responds
ping -c 3 192.168.83.220

# 2. All clients using VIP
mount | grep 192.168.83.220

# 3. Health checks working
sudo /usr/local/bin/check_nfs_services.sh && echo "Health check: PASSED"

# 4. SSH authentication working
sudo su -
ssh root@192.168.83.150 "echo 'SSH test successful'"
exit

# 5. lsyncd configuration correct
sudo systemctl status lsyncd --no-pager

echo "PHASE 4 COMPLETE: Automated NFS + DAG Processor HA"
echo "=================================="
echo "NFS VIP: 192.168.83.220"
echo "Automatic failover on: NFS, DAG processor, or lsyncd failure"
echo "Automatic failback when services recover"
echo "Bidirectional sync maintains data consistency"
```

---
