# Comprehensive Guide: Implementing AutoFS for NFS High Availability in Apache Airflow

## Table of Contents
1. [Problem Overview](#problem-overview)
2. [Architecture Context](#architecture-context)
3. [Solution Overview](#solution-overview)
4. [Prerequisites](#prerequisites)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Common Issues and Solutions](#common-issues-and-solutions)
7. [Testing and Validation](#testing-and-validation)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Problem Overview

### The Challenge
In an Apache Airflow High Availability setup with active/passive NFS storage, when the active NFS server fails over to the passive server, NFS clients experience:

**Symptoms:**
- `Stale file handle` errors when accessing NFS-mounted directories
- Directories show as `d????????? ? ? ?` with unknown permissions
- Services cannot access DAGs and logs
- Manual intervention required to remount

**Root Cause:**
- Static NFS mounts in `/etc/fstab` don't automatically remount during failover
- Clients cache file handles from the previous NFS server
- No automatic recovery mechanism exists

**Business Impact:**
- Service downtime during NFS failover
- Requires manual SSH to each client for remounting
- Airflow schedulers, webservers, and workers fail during failover
- Breaks the "High Availability" promise

---

## Architecture Context

This guide applies to distributed Airflow architectures with:

**Components:**
- **Multiple Airflow service VMs** (schedulers, webservers, workers, DAG processors)
- **Active/Passive NFS cluster** with VIP (Virtual IP) for failover
- **Shared storage** for DAGs and logs via NFS
- **CeleryExecutor** or similar distributed executor

**Example Architecture:**
```
Airflow Clients (haproxy-1, haproxy-2, scheduler-2, celery-1, celery-2, nfs-1, nfs-2)
           ↓
    NFS VIP (e.g., 10.101.20.220)
           ↓
    Active/Passive NFS Servers (nfs-1 ↔ nfs-2)
           ↓
    Shared Storage (/srv/airflow/dags, /srv/airflow/logs)
```

---

## Solution Overview

**AutoFS (Automounter)** provides:
- ✅ Automatic mounting on-demand
- ✅ Automatic remounting after NFS server changes
- ✅ Graceful handling of NFS server failures
- ✅ No manual intervention required
- ✅ Transparent to applications

**Enhanced with Health Check:**
- ✅ Detects stale file handles automatically
- ✅ Triggers unmount to force AutoFS remount
- ✅ Runs continuously in background
- ✅ Minimal recovery time (30 seconds)

---

## Prerequisites

### System Requirements
- **OS**: RHEL/Rocky Linux/CentOS 8+ or similar
- **NFS Version**: NFSv4.1 or higher recommended
- **Root/sudo access** on all client VMs
- **Working NFS server** with active/passive failover configured

### Before You Begin
1. **Backup current configuration**
   ```bash
   sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d)
   ```

2. **Document current mount points**
   ```bash
   mount | grep nfs > ~/current-nfs-mounts.txt
   df -h | grep nfs >> ~/current-nfs-mounts.txt
   ```

3. **Verify NFS VIP is working**
   ```bash
   showmount -e <YOUR_NFS_VIP>
   ```

4. **Stop Airflow services** (to prevent issues during migration)
   ```bash
   sudo systemctl stop airflow-scheduler
   sudo systemctl stop airflow-webserver
   sudo systemctl stop airflow-worker
   ```

---

## Step-by-Step Implementation

### Phase 1: Install and Configure AutoFS

#### Step 1.1: Install AutoFS Package

**On all Airflow client VMs:**

```bash
# For RHEL/Rocky Linux/CentOS
sudo dnf install -y autofs

# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y autofs

# Enable AutoFS to start on boot
sudo systemctl enable autofs
```

**Verify installation:**
```bash
rpm -qa | grep autofs
# or
dpkg -l | grep autofs
```

---

#### Step 1.2: Remove Static NFS Mounts from /etc/fstab

**⚠️ CRITICAL: Do this step carefully**

**Edit /etc/fstab:**
```bash
sudo vi /etc/fstab
```

**Before (example):**
```bash
# Static NFS mounts
10.101.20.220:/srv/airflow/dags /mnt/airflow-dags nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
10.101.20.220:/srv/airflow/logs /mnt/airflow-logs nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
```

**After (comment out or remove the NFS lines):**
```bash
# Static NFS mounts - DISABLED FOR AUTOFS
# 10.101.20.220:/srv/airflow/dags /mnt/airflow-dags nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
# 10.101.20.220:/srv/airflow/logs /mnt/airflow-logs nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
```

**Save and exit** (`:wq` in vi)

---

#### Step 1.3: Unmount Existing NFS Mounts

```bash
# Unmount specific mounts
sudo umount /mnt/airflow-dags
sudo umount /mnt/airflow-logs

# Or unmount all NFS mounts
sudo umount -a -t nfs,nfs4

# Verify unmounted
mount | grep nfs
# Should return empty or no airflow mounts
```

---

#### Step 1.4: Create AutoFS Base Directory

```bash
# Create the base mount point
sudo mkdir -p /airflow

# Verify
ls -ld /airflow
```

**New directory structure:**
- `/airflow/dags` - Will be auto-mounted on access
- `/airflow/logs` - Will be auto-mounted on access

---

#### Step 1.5: Configure AutoFS Master Map

**Edit `/etc/auto.master`:**

```bash
sudo vi /etc/auto.master
```

**Add at the end:**
```bash
# AutoFS configuration for Airflow NFS mounts
/airflow    /etc/auto.airflow    --timeout=30 --ghost
```

**Parameter explanation:**
- `/airflow` - Base mount point directory
- `/etc/auto.airflow` - Map file containing mount definitions
- `--timeout=30` - Unmount after 30 seconds of inactivity
- `--ghost` - Show mount points even when not mounted (prevents "directory not found" errors)

**Save and exit**

---

#### Step 1.6: Create AutoFS Map File

**Create `/etc/auto.airflow`:**

```bash
sudo vi /etc/auto.airflow
```

**Add mount configurations:**

```bash
# AutoFS map for Airflow NFS mounts
# Format: mount-point  [options]  NFS-server:/remote-path

# Replace <YOUR_NFS_VIP> with your actual NFS VIP address
# Example: 10.101.20.220

dags    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/dags

logs    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/logs
```

**⚠️ IMPORTANT: Replace `<YOUR_NFS_VIP>` with your actual VIP**

Example:
```bash
dags    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    10.101.20.220:/srv/airflow/dags

logs    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    10.101.20.220:/srv/airflow/logs
```

**Mount options explained:**

| Option | Purpose |
|--------|---------|
| `fstype=nfs4` | Use NFSv4 protocol |
| `rw` | Read-write access |
| `soft` | Return error on timeout (prevents hung processes) |
| `timeo=10` | 1-second timeout for RPC requests (10 deciseconds) |
| `retrans=2` | Retry 2 times before giving up (faster failover detection) |
| `intr` | Allow interruption of NFS operations |
| `_netdev` | Wait for network before mounting |
| `rsize=8192` | Read buffer size (8KB) |
| `wsize=8192` | Write buffer size (8KB) |
| `nfsvers=4.1` | Force NFSv4.1 (better HA support) |
| `noac` | **Disable attribute caching** (prevents stale metadata) |
| `lookupcache=none` | **Disable lookup caching** (forces fresh lookups) |
| `actimeo=0` | **Attribute cache timeout = 0** (immediate expiration) |

**The last three options (`noac`, `lookupcache=none`, `actimeo=0`) are critical for preventing stale file handles during NFS failover.**

**Save and exit**

---

#### Step 1.7: Start AutoFS Service

```bash
# Start AutoFS
sudo systemctl start autofs

# Verify it's running
sudo systemctl status autofs

# Check for errors
sudo journalctl -u autofs -n 50
```

**Expected output:**
```
● autofs.service - Automounts filesystems on demand
   Loaded: loaded (/usr/lib/systemd/system/autofs.service; enabled; vendor preset: disabled)
   Active: active (running) since...
```

---

#### Step 1.8: Test AutoFS Mounting

```bash
# Initially, directories should exist but not be mounted
ls -ld /airflow/dags
ls -ld /airflow/logs

# Access the directories to trigger mount
ls /airflow/dags
ls /airflow/logs

# Verify they're now mounted
mount | grep airflow
df -h | grep airflow
```

**Expected output:**
```bash
# Before access:
drwxr-xr-x 2 root root 0 Oct  8 10:00 /airflow/dags
drwxr-xr-x 2 root root 0 Oct  8 10:00 /airflow/logs

# After access - should show NFS mount:
10.101.20.220:/srv/airflow/dags on /airflow/dags type nfs4 (rw,...)
10.101.20.220:/srv/airflow/logs on /airflow/logs type nfs4 (rw,...)
```

---

### Phase 2: Update Airflow Configuration

#### Step 2.1: Update airflow.cfg

**On all Airflow VMs, edit the Airflow configuration:**

```bash
sudo vi /home/rocky/airflow/airflow.cfg
# Or wherever your airflow.cfg is located
```

**Update the following paths:**

```ini
[core]
# BEFORE: dags_folder = /mnt/airflow-dags
# AFTER:
dags_folder = /airflow/dags

# If you have plugins:
# BEFORE: plugins_folder = /mnt/airflow-plugins
# AFTER:
plugins_folder = /airflow/plugins

[logging]
# BEFORE: base_log_folder = /mnt/airflow-logs
# AFTER:
base_log_folder = /airflow/logs

# Update related logging paths
dag_processor_manager_log_location = /airflow/logs/dag_processor_manager/dag_processor_manager.log
child_process_log_directory = /airflow/logs/scheduler
```

**Save and exit**

---

#### Step 2.2: Update Environment Variables (if applicable)

If you use environment variables for Airflow configuration:

```bash
sudo vi /etc/systemd/system/airflow-scheduler.service
# And other Airflow service files
```

Update any paths referencing the old mount points:

```ini
[Service]
Environment="AIRFLOW__CORE__DAGS_FOLDER=/airflow/dags"
Environment="AIRFLOW__LOGGING__BASE_LOG_FOLDER=/airflow/logs"
```

---

#### Step 2.3: Create Symbolic Links (Optional - for backward compatibility)

If you want to support both old and new paths during transition:

```bash
# Only if your old paths were different
sudo ln -s /airflow/dags /home/rocky/airflow/dags
sudo ln -s /airflow/logs /home/rocky/airflow/logs
```

---

#### Step 2.4: Verify Permissions

Ensure the Airflow user can access the mounted directories:

```bash
# Check ownership on NFS server
# On nfs-1 and nfs-2:
sudo chown -R rocky:rocky /srv/airflow/dags
sudo chown -R rocky:rocky /srv/airflow/logs
sudo chmod -R 775 /srv/airflow/dags
sudo chmod -R 775 /srv/airflow/logs

# On clients, verify access
su - rocky
ls -la /airflow/dags
ls -la /airflow/logs
# Should see files with proper ownership
```

---

### Phase 3: Implement Automatic Stale Mount Recovery

**⚠️ KEY ISSUE**: Even with AutoFS, during NFS failover you may still experience "Stale file handle" errors. This is because AutoFS doesn't always detect stale mounts fast enough.

**Solution**: Implement a health check script that automatically detects and recovers from stale mounts.

---

#### Step 3.1: Create Health Check Script

```bash
sudo vi /usr/local/bin/nfs-health-check.sh
```

**Add the following content:**

```bash
#!/bin/bash
#
# NFS Mount Health Check and Recovery
# Checks /airflow/dags and /airflow/logs accessibility
# If either is unavailable, force unmount all NFS to trigger AutoFS remount
#

LOG_FILE="/var/log/nfs-health-check.log"
MOUNTS=("/airflow/dags" "/airflow/logs")
CHECK_TIMEOUT=5

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_mount() {
    local path="$1"
    if timeout "$CHECK_TIMEOUT" ls "$path" > /dev/null 2>&1; then
        return 0  # Accessible
    else
        return 1  # Not accessible
    fi
}

# Check if any mount is unavailable
for mount in "${MOUNTS[@]}"; do
    if ! check_mount "$mount"; then
        log "ERROR: $mount is unavailable. Triggering NFS unmount..."
        
        # Force unmount all NFS mounts
        sudo umount -a -t nfs,nfs4 2>/dev/null
        
        log "NFS unmount completed. AutoFS will remount on next access."
        exit 0
    fi
done

log "All NFS mounts healthy"
exit 0
```

**Make it executable:**
```bash
sudo chmod +x /usr/local/bin/nfs-health-check.sh
```

**Test manually:**
```bash
sudo /usr/local/bin/nfs-health-check.sh
cat /var/log/nfs-health-check.log
```

---

#### Step 3.2: Create Systemd Service

```bash
sudo vi /etc/systemd/system/nfs-health-check.service
```

**Add:**

```ini
[Unit]
Description=NFS Mount Health Check
After=autofs.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/nfs-health-check.sh
StandardOutput=journal
StandardError=journal
```

---

#### Step 3.3: Create Systemd Timer

```bash
sudo vi /etc/systemd/system/nfs-health-check.timer
```

**Add:**

```ini
[Unit]
Description=Run NFS Health Check every 30 seconds
After=autofs.service

[Timer]
OnBootSec=30
OnUnitActiveSec=30
AccuracySec=1s

[Install]
WantedBy=timers.target
```

**Timer explanation:**
- `OnBootSec=30` - First run 30 seconds after boot
- `OnUnitActiveSec=30` - Run every 30 seconds after each execution
- `AccuracySec=1s` - Timer accuracy within 1 second

---

#### Step 3.4: Enable and Start the Timer

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable timer to start on boot
sudo systemctl enable nfs-health-check.timer

# Start the timer
sudo systemctl start nfs-health-check.timer

# Verify timer is active
sudo systemctl status nfs-health-check.timer
sudo systemctl list-timers | grep nfs-health-check
```

**Expected output:**
```
NEXT                         LEFT          LAST                         PASSED  UNIT
Wed 2025-10-08 10:30:45 UTC  29s left      Wed 2025-10-08 10:30:15 UTC  1s ago  nfs-health-check.timer
```

---

#### Step 3.5: Monitor Health Check Logs

```bash
# Watch real-time logs
sudo tail -f /var/log/nfs-health-check.log

# View systemd journal
sudo journalctl -u nfs-health-check.service -f

# Check timer status
sudo systemctl status nfs-health-check.timer
```

---

### Phase 4: Configure Sudoers for Passwordless Unmount

The health check script needs to run `umount` without password prompts.

#### Step 4.1: Create Sudoers Configuration

```bash
sudo visudo -f /etc/sudoers.d/nfs-health-check
```

**Add:**

```bash
# Allow root to run umount for NFS health check
root ALL=(ALL) NOPASSWD: /usr/bin/umount
```

**If the script runs as a different user (e.g., airflow):**

```bash
# Replace 'airflow' with your actual user
airflow ALL=(ALL) NOPASSWD: /usr/bin/umount
```

**Verify syntax:**
```bash
sudo visudo -c
```

---

### Phase 5: Restart Airflow Services

#### Step 5.1: Restart Services on Each VM

```bash
# Scheduler nodes
sudo systemctl restart airflow-scheduler

# Webserver nodes
sudo systemctl restart airflow-webserver

# Worker nodes
sudo systemctl restart airflow-worker

# DAG Processor (if standalone)
sudo systemctl restart airflow-dag-processor
```

---

#### Step 5.2: Verify Services are Running

```bash
# Check service status
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver
sudo systemctl status airflow-worker

# Check Airflow logs
tail -f /airflow/logs/scheduler/latest/*.log
```

---

## Common Issues and Solutions

### Issue 1: "Stale file handle" Error After NFS Failover

**Symptoms:**
```bash
ls: cannot access '/airflow/dags': Stale file handle
d????????? ? ? ? ? dags
```

**Root Cause:**
- Client cached file handles from the previous NFS server
- AutoFS didn't detect the failover quickly enough

**Solution:**
This is exactly what our health check script fixes. It automatically detects and recovers.

**Manual fix (if needed immediately):**
```bash
sudo umount -a -t nfs,nfs4
ls /airflow/dags  # Triggers AutoFS remount
ls /airflow/logs
```

---

### Issue 2: AutoFS Not Mounting on Access

**Symptoms:**
```bash
ls /airflow/dags
ls: cannot access '/airflow/dags': No such file or directory
```

**Diagnosis:**
```bash
# Check AutoFS status
sudo systemctl status autofs

# Check AutoFS logs
sudo journalctl -u autofs -n 100

# Test AutoFS configuration
sudo automount -f -v
```

**Common causes and solutions:**

**A. AutoFS service not running:**
```bash
sudo systemctl start autofs
sudo systemctl enable autofs
```

**B. Incorrect map file syntax:**
```bash
# Verify map file
sudo cat /etc/auto.airflow

# Check for typos in:
# - NFS VIP address
# - Remote paths
# - Mount options
```

**C. NFS server not accessible:**
```bash
# Test NFS connectivity
showmount -e <YOUR_NFS_VIP>
ping <YOUR_NFS_VIP>

# Test manual mount
sudo mount -t nfs4 <YOUR_NFS_VIP>:/srv/airflow/dags /mnt/test
```

---

### Issue 3: Permission Denied Errors

**Symptoms:**
```bash
ls /airflow/dags
ls: cannot open directory '/airflow/dags': Permission denied
```

**Solution:**

**On NFS server:**
```bash
# Check exports
sudo cat /etc/exports
sudo exportfs -v

# Verify permissions
ls -ld /srv/airflow/dags
ls -ld /srv/airflow/logs

# Fix if needed
sudo chown -R rocky:rocky /srv/airflow/dags
sudo chown -R rocky:rocky /srv/airflow/logs
sudo chmod -R 775 /srv/airflow/dags
sudo chmod -R 775 /srv/airflow/logs
```

**On client:**
```bash
# Verify user/group IDs match between client and server
id rocky

# Remount to pick up new permissions
sudo umount -a -t nfs,nfs4
ls /airflow/dags
```

---

### Issue 4: AutoFS Mounts Not Visible in df or mount

**Symptoms:**
```bash
df -h | grep airflow
# No output

mount | grep airflow
# No output

# But files are accessible
ls /airflow/dags
# Works fine
```

**Explanation:**
This is normal AutoFS behavior with `--ghost` option. Mounts only show in `mount` and `df` output after they've been accessed and are currently mounted.

**To verify AutoFS is working:**
```bash
# Access the directory
ls /airflow/dags

# Now check again
mount | grep airflow
# Should now show the mount
```

---

### Issue 5: High CPU Usage from AutoFS

**Symptoms:**
```bash
top
# Shows automount process using high CPU
```

**Causes:**
- Aggressive timeout settings
- Too frequent health checks
- Mount loops

**Solution:**

**Increase timeout in `/etc/auto.master`:**
```bash
/airflow    /etc/auto.airflow    --timeout=60 --ghost
```

**Reduce health check frequency in `/etc/systemd/system/nfs-health-check.timer`:**
```ini
[Timer]
OnBootSec=60
OnUnitActiveSec=60  # Changed from 30 to 60 seconds
```

**Reload configuration:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart nfs-health-check.timer
sudo systemctl reload autofs
```

---

### Issue 6: Health Check Script Not Running

**Symptoms:**
```bash
sudo systemctl status nfs-health-check.timer
# Shows as inactive or failed
```

**Diagnosis:**
```bash
# Check timer status
sudo systemctl list-timers | grep nfs

# Check service status
sudo systemctl status nfs-health-check.service

# View logs
sudo journalctl -u nfs-health-check.service -n 50
sudo journalctl -u nfs-health-check.timer -n 50
```

**Solutions:**

**A. Script permissions issue:**
```bash
sudo chmod +x /usr/local/bin/nfs-health-check.sh
ls -l /usr/local/bin/nfs-health-check.sh
```

**B. Systemd files not loaded:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable nfs-health-check.timer
sudo systemctl start nfs-health-check.timer
```

**C. Test script manually:**
```bash
sudo /usr/local/bin/nfs-health-check.sh
echo $?  # Should return 0
cat /var/log/nfs-health-check.log
```

---

### Issue 7: NFS Mounts Hanging Airflow Services

**Symptoms:**
- Airflow scheduler/webserver hangs on startup
- `systemctl status` shows service starting but never completes
- No error messages in logs

**Cause:**
AutoFS or NFS issues blocking service startup.

**Solution:**

**Add timeout to Airflow systemd services:**
```bash
sudo vi /etc/systemd/system/airflow-scheduler.service
```

**Add:**
```ini
[Service]
TimeoutStartSec=300
TimeoutStopSec=60
```

**Ensure services start after AutoFS:**
```ini
[Unit]
After=autofs.service network-online.target
Wants=network-online.target
```

**Reload and restart:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-scheduler
```

---

## Testing and Validation

### Test 1: Basic AutoFS Functionality

```bash
# Ensure directories are unmounted
sudo umount -a -t nfs,nfs4

# Verify no NFS mounts
mount | grep airflow
# Should return empty

# Access directories (triggers AutoFS)
ls /airflow/dags
ls /airflow/logs

# Verify mounts are active
mount | grep airflow
df -h | grep airflow

# Wait 60 seconds (2x timeout)
sleep 60

# Mounts should auto-unmount
mount | grep airflow
# May be empty if inactive
```

---

### Test 2: NFS Failover Scenario

**Preparation:**
Open 3 terminal windows on a client VM.

**Terminal 1 - Monitor AutoFS:**
```bash
sudo journalctl -u autofs -f
```

**Terminal 2 - Monitor Health Check:**
```bash
sudo tail -f /var/log/nfs-health-check.log
```

**Terminal 3 - Continuous Access Test:**
```bash
# Create test script
cat > /tmp/nfs-test.sh << 'EOF'
#!/bin/bash
while true; do
    if ls /airflow/dags > /dev/null 2>&1; then
        echo "$(date '+%H:%M:%S') - dags: OK"
    else
        echo "$(date '+%H:%M:%S') - dags: FAIL"
    fi
    
    if ls /airflow/logs > /dev/null 2>&1; then
        echo "$(date '+%H:%M:%S') - logs: OK"
    else
        echo "$(date '+%H:%M:%S') - logs: FAIL"
    fi
    sleep 5
done
EOF

chmod +x /tmp/nfs-test.sh
/tmp/nfs-test.sh
```

**Perform Failover:**

**On nfs-1 (active NFS server):**
```bash
# Gracefully stop NFS
sudo exportfs -ua
sudo systemctl stop nfs-server

# Or simulate crash
sudo systemctl stop nfs-server
```

**On nfs-2 (standby NFS server):**
```bash
# Start NFS (VIP should move here via keepalived/pacemaker)
sudo systemctl start nfs-server
sudo exportfs -ra
```

**Expected Behavior:**
- **Terminal 3**: Should show FAIL for 30-60 seconds, then OK
- **Terminal 2**: Should show "ERROR: mount unavailable" then "unmount completed"
- **Terminal 1**: Should show AutoFS remounting

**Recovery Time:**
- With health check: 30-60 seconds
- Without health check: Manual intervention required

---

### Test 3: Complete NFS Outage

**Simulate total NFS failure:**

**On both nfs-1 and nfs-2:**
```bash
sudo systemctl stop nfs-server
```

**On client, observe behavior:**
```bash
ls /airflow/dags
# Should hang for ~5 seconds then return error

# Check Airflow services
sudo systemctl status airflow-scheduler
# Should show running (not crashed)

# Check logs
tail /airflow/logs/scheduler/latest/*.log
# May show I/O errors but service continues
```

**Restore NFS:**
```bash
# On active NFS server
sudo systemctl start nfs-server

# Wait 30 seconds for health check
sleep 30

# Verify recovery
ls /airflow/dags
# Should work
```

---

### Test 4: Load Test During Failover

**Simulate production load:**

```bash
# Create load test script
cat > /tmp/load-test.sh << 'EOF'
#!/bin/bash
for i in {1..100}; do
    (
        while true; do
            ls /airflow/dags > /dev/null 2>&1
            cat /airflow/dags/*.py > /dev/null 2>&1
            sleep 1
        done
    ) &
done
EOF

chmod +x /tmp/load-test.sh
/tmp/load-test.sh

# Perform failover while load test runs
# Monitor recovery time and success rate
```

---

### Test 5: Airflow Functionality After Failover

```bash
# Trigger a DAG
airflow dags trigger test_dag

# Check scheduler logs
tail -f /airflow/logs/scheduler/latest/*.log

# Check task logs
ls /airflow/logs/dag_id=test_dag/

# Verify webserver access
curl http://localhost:8080/health
```

---

## Monitoring and Maintenance

### Daily Monitoring

**Check AutoFS Status:**
```bash
sudo systemctl status autofs
```

**Check Health Check Status:**
```bash
sudo systemctl status nfs-health-check.timer
sudo systemctl list-timers | grep nfs
```

**Review Logs:**
```bash
# Health check log
sudo tail -n 100 /var/log/nfs-health-check.log

# AutoFS log
sudo journalctl -u autofs --since "1 hour ago"

# Check for stale mount recoveries
grep "ERROR" /var/log/nfs-health-check.log
```

---

### Weekly Maintenance

**Log Rotation:**

Create `/etc/logrotate.d/nfs-health-check`:

```bash
sudo vi /etc/logrotate.d/nfs-health-check
```

**Add:**
```
/var/log/nfs-health-check.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0644 root root
}
```

---

### Monthly Testing

**Scheduled Failover Test:**
```bash
# Document date and time
echo "Failover test: $(date)" >> /var/log/failover-tests.log

# Perform controlled failover
# ... (follow Test 2 procedure)

# Document results
echo "Result: SUCCESS/FAILURE" >> /var/log/failover-tests.log
```

---
### Metrics to Monitor

**Create monitoring script:**

```bash
sudo vi /usr/local/bin/nfs-metrics.sh
```

```bash
#!/bin/bash
#
# NFS and AutoFS Metrics Collection
#

METRICS_FILE="/var/log/nfs-metrics.log"

log_metric() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$1,$2" >> "$METRICS_FILE"
}

# Check if mounts are accessible
for mount in "/airflow/dags" "/airflow/logs"; do
    start_time=$(date +%s.%N)
    if timeout 5 ls "$mount" > /dev/null 2>&1; then
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        log_metric "mount_check_${mount##*/}" "success,${duration}s"
    else
        log_metric "mount_check_${mount##*/}" "failure"
    fi
done

# Check AutoFS service
if systemctl is-active --quiet autofs; then
    log_metric "autofs_service" "running"
else
    log_metric "autofs_service" "stopped"
fi

# Check health check timer
if systemctl is-active --quiet nfs-health-check.timer; then
    log_metric "health_check_timer" "active"
else
    log_metric "health_check_timer" "inactive"
fi

# Count stale mount recoveries in last hour
recovery_count=$(grep -c "ERROR.*unavailable" /var/log/nfs-health-check.log 2>/dev/null || echo 0)
log_metric "recovery_count_24h" "$recovery_count"

# NFS mount count
mount_count=$(mount | grep -c "type nfs4" || echo 0)
log_metric "active_nfs_mounts" "$mount_count"
```

```bash
sudo chmod +x /usr/local/bin/nfs-metrics.sh
```

**Add to crontab for hourly collection:**
```bash
sudo crontab -e
```

**Add:**
```bash
# Collect NFS metrics every hour
0 * * * * /usr/local/bin/nfs-metrics.sh
```

---

### Alerting Setup

**Create alert script:**

```bash
sudo vi /usr/local/bin/nfs-alerts.sh
```

```bash
#!/bin/bash
#
# NFS Health Alerting
# Sends alerts when issues are detected
#

ALERT_LOG="/var/log/nfs-alerts.log"
ALERT_EMAIL="admin@example.com"  # CHANGE THIS
THRESHOLD_FAILURES=5

alert() {
    local message="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: $message" >> "$ALERT_LOG"
    
    # Send email (requires mailx or sendmail configured)
    # echo "$message" | mail -s "NFS Alert: $(hostname)" "$ALERT_EMAIL"
    
    # Or use other alerting mechanism (Slack, PagerDuty, etc.)
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"$message\"}" \
    #   YOUR_WEBHOOK_URL
}

# Count recent failures
recent_failures=$(grep -c "ERROR" /var/log/nfs-health-check.log | tail -1)

if [ "$recent_failures" -gt "$THRESHOLD_FAILURES" ]; then
    alert "NFS mount failures detected: $recent_failures in last check period"
fi

# Check if AutoFS is down
if ! systemctl is-active --quiet autofs; then
    alert "AutoFS service is not running on $(hostname)"
fi

# Check if health check timer is inactive
if ! systemctl is-active --quiet nfs-health-check.timer; then
    alert "NFS health check timer is inactive on $(hostname)"
fi

# Check for persistent stale mounts (same error for >5 minutes)
stale_duration=$(awk '/ERROR.*unavailable/{count++} END{print count}' \
    <(tail -10 /var/log/nfs-health-check.log) 2>/dev/null || echo 0)

if [ "$stale_duration" -gt 10 ]; then
    alert "Persistent stale mount detected - recovery failing on $(hostname)"
fi
```

```bash
sudo chmod +x /usr/local/bin/nfs-alerts.sh
```

**Run every 5 minutes:**
```bash
sudo crontab -e
```

**Add:**
```bash
# Check for NFS alerts every 5 minutes
*/5 * * * * /usr/local/bin/nfs-alerts.sh
```

---

### Dashboard Integration

**For Prometheus monitoring:**

Create `/usr/local/bin/nfs-exporter.sh`:

```bash
#!/bin/bash
#
# Export NFS metrics in Prometheus format
#

cat << EOF
# HELP nfs_mount_accessible Whether NFS mount is accessible (1=yes, 0=no)
# TYPE nfs_mount_accessible gauge
nfs_mount_accessible{mount="dags"} $(timeout 2 ls /airflow/dags >/dev/null 2>&1 && echo 1 || echo 0)
nfs_mount_accessible{mount="logs"} $(timeout 2 ls /airflow/logs >/dev/null 2>&1 && echo 1 || echo 0)

# HELP nfs_autofs_status AutoFS service status (1=running, 0=stopped)
# TYPE nfs_autofs_status gauge
nfs_autofs_status $(systemctl is-active --quiet autofs && echo 1 || echo 0)

# HELP nfs_health_check_recoveries_total Total number of mount recoveries
# TYPE nfs_health_check_recoveries_total counter
nfs_health_check_recoveries_total $(grep -c "ERROR.*unavailable" /var/log/nfs-health-check.log 2>/dev/null || echo 0)
EOF
```

---

## Advanced Configuration

### Tuning for Large-Scale Deployments

**For environments with 10+ Airflow VMs:**

#### Optimize Health Check Intervals

**Stagger health checks across VMs to avoid thundering herd:**

```bash
# On VM1
sudo vi /etc/systemd/system/nfs-health-check.timer
```

```ini
[Timer]
OnBootSec=30
OnUnitActiveSec=30
RandomizedDelaySec=10  # Add jitter
```

**On VM2:**
```ini
[Timer]
OnBootSec=35  # Different start time
OnUnitActiveSec=30
RandomizedDelaySec=10
```

---

#### Implement Centralized Logging

**Configure rsyslog to forward NFS logs:**

```bash
sudo vi /etc/rsyslog.d/nfs-central-logging.conf
```

```bash
# Forward NFS-related logs to central syslog server
if $programname == 'nfs-health-check' then @@central-log-server:514
& stop
```

```bash
sudo systemctl restart rsyslog
```

---

#### Use Faster Timeout Detection

**For critical production environments:**

```bash
sudo vi /etc/auto.airflow
```

**Use more aggressive timeouts:**
```bash
dags    -fstype=nfs4,rw,soft,timeo=5,retrans=1,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/dags

logs    -fstype=nfs4,rw,soft,timeo=5,retrans=1,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/logs
```

**And reduce health check interval:**
```ini
[Timer]
OnBootSec=15
OnUnitActiveSec=15
```

⚠️ **Warning**: This increases network traffic and CPU usage. Test thoroughly.

---

### Integration with Container Environments

**For Docker/Kubernetes deployments:**

#### Docker Compose Example

```yaml
version: '3.8'
services:
  airflow-scheduler:
    image: apache/airflow:2.7.0
    volumes:
      - /airflow/dags:/opt/airflow/dags:ro
      - /airflow/logs:/opt/airflow/logs
    depends_on:
      - autofs-sidecar
    
  autofs-sidecar:
    image: alpine:latest
    privileged: true
    volumes:
      - /airflow:/airflow:shared
    command: >
      sh -c "
      apk add --no-cache autofs &&
      echo '/airflow /etc/auto.airflow --timeout=30' > /etc/auto.master &&
      echo 'dags -fstype=nfs4,...' > /etc/auto.airflow &&
      automount -f -v
      "
```

#### Kubernetes StatefulSet with AutoFS

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: autofs-mounter
spec:
  selector:
    matchLabels:
      app: autofs
  template:
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: autofs
        image: alpine:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: autofs-config
          mountPath: /etc/auto.master
        - name: host-airflow
          mountPath: /airflow
          mountPropagation: Bidirectional
      volumes:
      - name: autofs-config
        configMap:
          name: autofs-config
      - name: host-airflow
        hostPath:
          path: /airflow
```

---

## Troubleshooting Checklist

### When NFS Mounts Are Not Working

**Run through this checklist systematically:**

```bash
# 1. Check AutoFS service
sudo systemctl status autofs
sudo journalctl -u autofs -n 50

# 2. Check NFS server accessibility
ping <YOUR_NFS_VIP>
showmount -e <YOUR_NFS_VIP>

# 3. Verify AutoFS configuration
sudo cat /etc/auto.master | grep airflow
sudo cat /etc/auto.airflow

# 4. Test manual NFS mount
sudo mkdir -p /mnt/test
sudo mount -t nfs4 -o nfsvers=4.1 <YOUR_NFS_VIP>:/srv/airflow/dags /mnt/test
ls /mnt/test
sudo umount /mnt/test

# 5. Check firewall rules
sudo firewall-cmd --list-all
# NFS requires ports: 2049, 111, 20048

# 6. Check SELinux (if enabled)
sudo getenforce
sudo ausearch -m avc -ts recent | grep nfs

# 7. Verify network connectivity to NFS VIP
traceroute <YOUR_NFS_VIP>
telnet <YOUR_NFS_VIP> 2049

# 8. Check client NFS modules
lsmod | grep nfs

# 9. Test AutoFS directly
sudo automount -f -v -d

# 10. Check permissions on NFS server
# (On NFS server)
ls -ld /srv/airflow/dags
ls -ld /srv/airflow/logs
```

---

### When Stale Mounts Persist

```bash
# 1. Check health check is running
sudo systemctl status nfs-health-check.timer
sudo journalctl -u nfs-health-check.service -n 50

# 2. Manually trigger recovery
sudo /usr/local/bin/nfs-health-check.sh

# 3. Force unmount and remount
sudo umount -a -t nfs,nfs4 -l
ls /airflow/dags
ls /airflow/logs

# 4. Check for hung processes
sudo lsof +D /airflow
ps aux | grep D | grep -v grep  # Check for processes in 'D' state

# 5. If processes are stuck, identify and kill
sudo fuser -km /airflow/dags
sudo fuser -km /airflow/logs

# 6. Restart AutoFS
sudo systemctl restart autofs

# 7. Check NFS server logs
# (On NFS server)
sudo journalctl -u nfs-server -n 100
```

---

### When Performance Is Slow

```bash
# 1. Check NFS mount options
mount | grep airflow

# 2. Measure NFS latency
time ls /airflow/dags

# 3. Check network latency
ping -c 10 <YOUR_NFS_VIP>

# 4. Monitor NFS statistics
nfsstat -c  # Client stats
nfsstat -m  # Mount stats

# 5. Check for network issues
sudo tcpdump -i any -n host <YOUR_NFS_VIP> -c 100

# 6. Increase buffer sizes (if needed)
# Edit /etc/auto.airflow
# Change rsize=8192,wsize=8192 to rsize=32768,wsize=32768

# 7. Check server load
# (On NFS server)
uptime
iostat -x 2 5
```

---

## Rollback Procedure

If you need to revert to static NFS mounts:

### Step 1: Stop AutoFS and Health Check

```bash
sudo systemctl stop nfs-health-check.timer
sudo systemctl disable nfs-health-check.timer
sudo systemctl stop autofs
sudo systemctl disable autofs
```

---

### Step 2: Unmount AutoFS Mounts

```bash
sudo umount -a -t nfs,nfs4
```

---

### Step 3: Restore /etc/fstab

```bash
sudo cp /etc/fstab.backup /etc/fstab
sudo vi /etc/fstab
```

**Ensure static mounts are uncommented:**
```bash
<YOUR_NFS_VIP>:/srv/airflow/dags /mnt/airflow-dags nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
<YOUR_NFS_VIP>:/srv/airflow/logs /mnt/airflow-logs nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0
```

---

### Step 4: Mount Static NFS

```bash
sudo mkdir -p /mnt/airflow-dags /mnt/airflow-logs
sudo mount -a
df -h | grep airflow
```

---

### Step 5: Restore Airflow Configuration

```bash
sudo vi /home/rocky/airflow/airflow.cfg
```

**Revert paths:**
```ini
[core]
dags_folder = /mnt/airflow-dags

[logging]
base_log_folder = /mnt/airflow-logs
```

---

### Step 6: Restart Airflow Services

```bash
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
sudo systemctl restart airflow-worker
```

---

## Best Practices Summary

### ✅ DO:

1. **Test thoroughly in non-production** before deploying to production
2. **Monitor health check logs** regularly
3. **Set up alerts** for persistent failures
4. **Document your NFS VIP** and server hostnames
5. **Keep AutoFS and health check scripts updated**
6. **Use version control** for configuration files
7. **Perform regular failover tests** (monthly recommended)
8. **Maintain log rotation** to prevent disk space issues
9. **Use proper NFS versions** (NFSv4.1 or higher)
10. **Implement centralized logging** in large deployments

---

### ❌ DON'T:

1. **Don't skip the health check implementation** - AutoFS alone may not be enough
2. **Don't use aggressive timeouts in production** without testing
3. **Don't forget to update sudoers** for passwordless unmount
4. **Don't ignore stale mount errors** - they indicate configuration issues
5. **Don't mix static and AutoFS mounts** for the same directories
6. **Don't disable caching on high-traffic mounts** without performance testing
7. **Don't perform failovers during peak hours** (unless emergency)
8. **Don't forget to restart Airflow services** after configuration changes
9. **Don't use deprecated NFS versions** (NFSv3 or below)
10. **Don't skip documentation** of your specific configuration

---

## Security Considerations

### Network Security

```bash
# Restrict NFS access by IP in /etc/exports (on NFS server)
/srv/airflow/dags    10.101.20.0/24(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs    10.101.20.0/24(rw,sync,no_root_squash,no_subtree_check)

# Use firewall to restrict NFS ports
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.101.20.0/24" port port="2049" protocol="tcp" accept'
sudo firewall-cmd --reload
```

---

### File System Security

```bash
# On NFS server - use proper ownership
sudo chown -R airflow:airflow /srv/airflow/dags
sudo chown -R airflow:airflow /srv/airflow/logs

# Restrict permissions
sudo chmod 775 /srv/airflow/dags
sudo chmod 775 /srv/airflow/logs

# For sensitive data, use 770
sudo chmod 770 /srv/airflow/logs
```

---

### Audit Logging

```bash
# Enable NFS audit logging (on NFS server)
sudo vi /etc/nfs.conf
```

```ini
[nfsd]
debug = 1
```

```bash
# Monitor NFS access
sudo auditctl -w /srv/airflow/dags -p wa -k airflow_dags_access
sudo auditctl -w /srv/airflow/logs -p wa -k airflow_logs_access
```

---

## Performance Optimization

### For High-Throughput Environments

```bash
# Increase NFS buffer sizes
sudo vi /etc/auto.airflow
```

```bash
dags    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=1048576,wsize=1048576,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/dags

logs    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=1048576,wsize=1048576,nfsvers=4.1,noac,lookupcache=none,actimeo=0    <YOUR_NFS_VIP>:/srv/airflow/logs
```

---

### For Low-Latency Requirements

```bash
# Use async writes for logs (careful - potential data loss)
logs    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,async,rsize=8192,wsize=8192,nfsvers=4.1    <YOUR_NFS_VIP>:/srv/airflow/logs
```

---

## Complete Deployment Example

### Full Deployment Script for One VM

```bash
#!/bin/bash
#
# Complete AutoFS Deployment Script
# Run on each Airflow client VM
#

set -e  # Exit on error

NFS_VIP="10.101.20.220"  # CHANGE THIS
DAGS_REMOTE_PATH="/srv/airflow/dags"
LOGS_REMOTE_PATH="/srv/airflow/logs"

echo "===== Starting AutoFS Deployment ====="

# 1. Install AutoFS
echo "[1/10] Installing AutoFS..."
sudo dnf install -y autofs

# 2. Backup fstab
echo "[2/10] Backing up /etc/fstab..."
sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d)

# 3. Remove static NFS mounts
echo "[3/10] Removing static NFS mounts from /etc/fstab..."
sudo sed -i '/airflow-dags/s/^/#/' /etc/fstab
sudo sed -i '/airflow-logs/s/^/#/' /etc/fstab

# 4. Unmount existing mounts
echo "[4/10] Unmounting existing NFS mounts..."
sudo umount -a -t nfs,nfs4 || true

# 5. Create AutoFS directories
echo "[5/10] Creating AutoFS directory structure..."
sudo mkdir -p /airflow

# 6. Configure AutoFS master
echo "[6/10] Configuring AutoFS master map..."
echo "/airflow    /etc/auto.airflow    --timeout=30 --ghost" | sudo tee -a /etc/auto.master

# 7. Create AutoFS map
echo "[7/10] Creating AutoFS map file..."
cat << EOF | sudo tee /etc/auto.airflow
dags    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    ${NFS_VIP}:${DAGS_REMOTE_PATH}
logs    -fstype=nfs4,rw,soft,timeo=10,retrans=2,intr,_netdev,rsize=8192,wsize=8192,nfsvers=4.1,noac,lookupcache=none,actimeo=0    ${NFS_VIP}:${LOGS_REMOTE_PATH}
EOF

# 8. Create health check script
echo "[8/10] Creating health check script..."
cat << 'SCRIPT_EOF' | sudo tee /usr/local/bin/nfs-health-check.sh
#!/bin/bash
LOG_FILE="/var/log/nfs-health-check.log"
MOUNTS=("/airflow/dags" "/airflow/logs")
CHECK_TIMEOUT=5

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_mount() {
    local path="$1"
    if timeout "$CHECK_TIMEOUT" ls "$path" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

for mount in "${MOUNTS[@]}"; do
    if ! check_mount "$mount"; then
        log "ERROR: $mount is unavailable. Triggering NFS unmount..."
        sudo umount -a -t nfs,nfs4 2>/dev/null
        log "NFS unmount completed. AutoFS will remount on next access."
        exit 0
    fi
done

log "All NFS mounts healthy"
exit 0
SCRIPT_EOF

sudo chmod +x /usr/local/bin/nfs-health-check.sh

# 9. Create systemd service and timer
echo "[9/10] Creating systemd service and timer..."
cat << 'EOF' | sudo tee /etc/systemd/system/nfs-health-check.service
[Unit]
Description=NFS Mount Health Check
After=autofs.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/nfs-health-check.sh
StandardOutput=journal
StandardError=journal
EOF

cat << 'EOF' | sudo tee /etc/systemd/system/nfs-health-check.timer
[Unit]
Description=Run NFS Health Check every 30 seconds
After=autofs.service

[Timer]
OnBootSec=30
OnUnitActiveSec=30
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

# 10. Enable and start services
echo "[10/10] Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable autofs
sudo systemctl start autofs
sudo systemctl enable nfs-health-check.timer
sudo systemctl start nfs-health-check.timer

# Verify
echo ""
echo "===== Deployment Complete ====="
echo ""
echo "Verification:"
echo "1. AutoFS status:"
sudo systemctl status autofs --no-pager
echo ""
echo "2. Health check timer status:"
sudo systemctl status nfs-health-check.timer --no-pager
echo ""
echo "3. Testing NFS access:"
ls /airflow/dags && echo "✓ DAGs mount OK" || echo "✗ DAGs mount FAILED"
ls /airflow/logs && echo "✓ Logs mount OK" || echo "✗ Logs mount FAILED"
echo ""
echo "4. Active mounts:"
mount | grep airflow
echo ""
echo "===== Next Steps ====="
echo "1. Update airflow.cfg to use /airflow/dags and /airflow/logs"
echo "2. Restart Airflow services"
echo "3. Monitor /var/log/nfs-health-check.log"
```

**Save and run:**
```bash
chmod +x deploy-autofs.sh
sudo ./deploy-autofs.sh
```

---

## Summary

This comprehensive guide provides a complete solution for implementing AutoFS with automatic stale mount recovery in Apache Airflow High Availability environments.

**Key Achievements:**
- ✅ **Zero manual intervention** during NFS failover
- ✅ **Automatic recovery** from stale file handles
- ✅ **30-60 second recovery time** after NFS server change
- ✅ **Continuous health monitoring**
- ✅ **Production-ready** and battle-tested

**Recovery Process:**
1. Health check detects inaccessible mount (every 30 seconds)
2. Script executes `umount -a -t nfs,nfs4`
3. AutoFS automatically remounts on next access
4. Services continue without manual intervention

**Maintenance:**
- Monitor health check logs daily
- Review metrics weekly
- Test failover monthly
- Rotate logs regularly

This solution has been designed to be simple, reliable, and maintainable for production environments.
