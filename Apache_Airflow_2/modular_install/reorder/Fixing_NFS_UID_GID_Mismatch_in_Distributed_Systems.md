# **Complete Guide: Fixing NFS UID/GID Mismatch in Distributed Systems**

This guide solves the problem where NFS-mounted files show numeric UIDs (like "1001") instead of usernames on client machines.

---

## **Table of Contents**
1. [Problem Overview](#problem-overview)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Diagnosis Steps](#diagnosis-steps)
4. [Solution Implementation](#solution-implementation)
5. [Common Errors & Solutions](#common-errors--solutions)
6. [Verification & Testing](#verification--testing)
7. [Prevention Best Practices](#prevention-best-practices)

---

## **Problem Overview**

### **Symptoms:**
- Files on NFS-mounted directories show numeric UIDs (e.g., `1001`) instead of usernames
- Ownership changes back to numbers automatically after being set to username
- Permission denied errors even though user should have access
- Airflow (or other applications) fail to write logs or create files

### **Example:**
```bash
# On client machine
ls -la /mnt/airflow-logs/
drwxr-xr-x  5 1001 1001 4096 Sep 28 11:40 'dag_id=S00_NASIR_DAG'
                ↑    ↑
          Should be "rocky rocky"
```

---

## **Root Cause Analysis**

**NFS uses numeric UIDs/GIDs, NOT usernames.**

When a file is created:
- **NFS Server**: User `rocky` (UID 1001) creates a file → Stored as UID 1001
- **NFS Client**: Mounts the file → Looks up UID 1001 in local `/etc/passwd`
- **Problem**: If client's `rocky` user has UID 1000, file appears as "1001" (unknown user)

**Why this happens:**
- VMs created at different times
- Different installation orders
- System users added in different sequences
- No centralized user management (LDAP/FreeIPA)

---

## **Diagnosis Steps**

### **Step 1: Check UID/GID on ALL machines**

```bash
# Run on EVERY machine in your infrastructure
id rocky
```

**Expected output:**
```bash
uid=1000(rocky) gid=1000(rocky) groups=1000(rocky)
```

**Document results in a table:**

| Machine | Hostname | UID | GID | Match? |
|---------|----------|-----|-----|--------|
| NFS Server 1 | nfs-1 | 1001 | 1001 | ❌ |
| NFS Server 2 | nfs-2 | 1000 | 1000 | ✅ |
| Client 1 | haproxy-1 | 1000 | 1000 | ✅ |
| Client 2 | haproxy-2 | 1000 | 1000 | ✅ |
| Client 3 | scheduler-2 | 1000 | 1000 | ✅ |
| Worker 1 | celery-1 | 1000 | 1000 | ✅ |

**Conclusion**: The active NFS server has a different UID/GID!

---

### **Step 2: Verify file ownership on NFS server**

```bash
# On NFS server
ls -lan /srv/airflow/logs/ | head -10
ls -lan /srv/airflow/dags/ | head -10
```

Look for numeric UIDs in the output.

---

### **Step 3: Check for conflicting users**

```bash
# On the problematic NFS server
cat /etc/passwd | grep 1000
cat /etc/group | grep 1000
```

Check if another user/group is already using the target UID/GID.

---

## **Solution Implementation**

### **Architecture Overview**

For this guide, assume:
- **Target UID/GID**: 1000 (used by most machines)
- **Current NFS Server UID/GID**: 1001 (the outlier)
- **Conflicting user**: `rhel` (already using UID 1000 on NFS server)

---

### **Phase 1: Preparation**

#### **1.1 Stop all services**

```bash
# On NFS Servers (nfs-1, nfs-2)
sudo systemctl stop airflow-dag-processor
sudo systemctl stop nfs-server  # Optional, but recommended

# On Schedulers (haproxy-1, scheduler-2)
sudo systemctl stop airflow-scheduler

# On Webservers (haproxy-1, haproxy-2)
sudo systemctl stop airflow-webserver

# On Workers (celery-1, celery-2)
sudo systemctl stop airflow-worker
```

#### **1.2 Document current state**

```bash
# On NFS server
id rocky
id rhel  # Or whatever conflicting user exists
ls -lan /srv/airflow/ | head -20
```

---

### **Phase 2: Resolve UID/GID Conflicts**

#### **2.1 SSH as a different user to NFS server**

**Critical**: You cannot change a user's UID while logged in as that user!

```bash
# From your workstation/jump host
ssh rhel@<NFS_SERVER_IP>
# OR
ssh root@<NFS_SERVER_IP>
```

#### **2.2 Become root**

```bash
sudo su -
```

#### **2.3 Move conflicting user to new UID/GID**

```bash
# Change the conflicting user (rhel) to a different UID
usermod -u 1003 rhel

# Update file ownership for old UID
find / -user 1000 -exec chown -h 1003 {} \; 2>/dev/null

# Verify
id rhel
# Should show: uid=1003(rhel) gid=1000(rhel)...
```

---

### **Phase 3: Change Target User UID/GID**

#### **3.1 Kill all processes owned by target user**

```bash
# Kill all rocky processes
pkill -9 -u rocky

# Verify no processes remain
ps aux | grep rocky
```

**If you see error: "user rocky is currently used by process XXXX"**

```bash
# Check what the process is
ps -p XXXX -o pid,user,cmd

# Kill it specifically
kill -9 XXXX

# Or kill all rocky processes forcefully
pkill -9 -u rocky
```

#### **3.2 Change user UID**

```bash
usermod -u 1000 rocky

# Verify
id rocky
# Should show: uid=1000(rocky) gid=1001(rocky)...
```

**If you see error: "UID '1000' already exists"**
- You didn't complete Phase 2 properly
- Another user still has UID 1000
- Go back and check: `cat /etc/passwd | grep 1000`

#### **3.3 Change conflicting group GID**

```bash
# Check which group has GID 1000
cat /etc/group | grep -E "^.*:.*:1000:"

# Change it (example: rhel group)
groupmod -g 1003 rhel

# Verify
cat /etc/group | grep rhel
```

#### **3.4 Change target user GID**

```bash
groupmod -g 1000 rocky

# Verify
id rocky
# Should show: uid=1000(rocky) gid=1000(rocky) groups=1000(rocky)
```

**If you see error: "GID '1000' already exists"**
- Complete step 3.3 first
- Check: `cat /etc/group | grep 1000`

---

### **Phase 4: Update File Ownership**

#### **4.1 Fix files with old UID**

```bash
# Find and fix all files owned by old UID (1001)
find /srv/airflow -user 1001 -exec chown -h 1000 {} \;

# Also fix user's home directory
find /home/rocky -user 1001 -exec chown -h 1000 {} \;
```

#### **4.2 Fix files with old GID**

```bash
# Find and fix all files with old GID (1001)
find /srv/airflow -group 1001 -exec chgrp -h 1000 {} \;

# Also fix user's home directory
find /home/rocky -group 1001 -exec chgrp -h 1000 {} \;
```

#### **4.3 Verify ownership**

```bash
# Check numeric ownership
ls -lan /srv/airflow/logs/ | head -10
ls -lan /srv/airflow/dags/ | head -10

# Should show UID 1000 and GID 1000 everywhere

# Check symbolic ownership
ls -la /srv/airflow/logs/ | head -10
ls -la /srv/airflow/dags/ | head -10

# Should show "rocky rocky" everywhere
```

---

### **Phase 5: Synchronize Secondary NFS Server**

#### **5.1 On secondary NFS server (nfs-2)**

```bash
# Ensure rocky has correct UID/GID
id rocky
# Should already be uid=1000, gid=1000

# Fix file ownership just to be safe
sudo chown -R rocky:rocky /srv/airflow/

# Verify
ls -la /srv/airflow/logs/ | head -5
ls -la /srv/airflow/dags/ | head -5
```

---

### **Phase 6: Update NFS Clients**

#### **6.1 Remount NFS shares on ALL client machines**

```bash
# On haproxy-1, haproxy-2, scheduler-2, celery-1, celery-2
sudo umount -a -t nfs,nfs4
sudo mount -a

# Verify mounts
df -h | grep nfs
mount | grep nfs
```

#### **6.2 Verify ownership on clients**

```bash
# Check if files now show "rocky" instead of "1001"
ls -la /mnt/airflow-logs/ | head -10
ls -la /mnt/airflow-dags/ | head -10

# Should show "rocky rocky" everywhere
```

---

### **Phase 7: Restart Services**

#### **7.1 Start NFS services**

```bash
# On nfs-1, nfs-2
sudo systemctl start nfs-server
sudo exportfs -ra  # Re-export NFS shares
sudo systemctl start airflow-dag-processor
```

#### **7.2 Start Airflow services**

```bash
# On schedulers (haproxy-1, scheduler-2)
sudo systemctl start airflow-scheduler

# On webservers (haproxy-1, haproxy-2)
sudo systemctl start airflow-webserver

# On workers (celery-1, celery-2)
sudo systemctl start airflow-worker
```

#### **7.3 Check service status**

```bash
# On each machine
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver
sudo systemctl status airflow-worker
sudo systemctl status airflow-dag-processor
```

---

## **Common Errors & Solutions**

### **Error 1: "UID 'XXXX' already exists"**

**Cause**: Another user is already using the target UID.

**Solution**:
```bash
# Find who's using the UID
cat /etc/passwd | grep "x:1000:"

# Change that user to a different UID first
usermod -u 1003 <conflicting_user>
find / -user 1000 -exec chown -h 1003 {} \; 2>/dev/null

# Then proceed with your target user
usermod -u 1000 <target_user>
```

---

### **Error 2: "user is currently used by process XXXX"**

**Cause**: The user has active processes (SSH sessions, systemd user sessions, etc.).

**Solutions**:

**Option A: SSH as different user**
```bash
# Exit current session
exit

# SSH as root or another user
ssh root@<server>
# OR
ssh <other_user>@<server>
sudo su -

# Kill all target user processes
pkill -9 -u rocky
usermod -u 1000 rocky
```

**Option B: Kill specific process**
```bash
# Identify the process
ps -p XXXX -o pid,user,cmd

# Kill it
sudo kill -9 XXXX

# Try again
sudo usermod -u 1000 rocky
```

---

### **Error 3: "GID 'XXXX' already exists"**

**Cause**: Another group is already using the target GID.

**Solution**:
```bash
# Find which group is using the GID
cat /etc/group | grep ":1000:"

# Change that group to a different GID first
groupmod -g 1003 <conflicting_group>

# Then proceed with your target group
groupmod -g 1000 <target_group>
```

---

### **Error 4: Files still show numeric UIDs after changing**

**Cause**: Old file ownership not updated, or NFS client cache.

**Solution**:
```bash
# On NFS server - update file ownership
find /srv/airflow -user <old_uid> -exec chown -h <new_uid> {} \;
find /srv/airflow -group <old_gid> -exec chgrp -h <new_gid> {} \;

# On NFS clients - remount to clear cache
sudo umount -a -t nfs,nfs4
sudo mount -a
```

---

### **Error 5: Permission denied after ownership change**

**Cause**: SELinux or incorrect permissions.

**Solution**:
```bash
# Check SELinux status
getenforce

# If Enforcing, check for denials
ausearch -m avc -ts recent

# Temporary: set to permissive (for testing only)
sudo setenforce 0

# Permanent fix: Set correct SELinux contexts
restorecon -Rv /srv/airflow/

# Or disable SELinux (not recommended for production)
# Edit /etc/selinux/config and set SELINUX=disabled
```

---

## **Verification & Testing**

### **Test 1: Create new files**

```bash
# On a client machine
touch /mnt/airflow-dags/test_file.txt
ls -la /mnt/airflow-dags/test_file.txt

# Should show: -rw-r--r-- 1 rocky rocky ... test_file.txt
```

### **Test 2: Trigger Airflow DAG**

```bash
# Access Airflow UI and trigger a DAG
# Check new log files
ls -la /mnt/airflow-logs/scheduler/latest/

# Should show "rocky rocky" ownership
```

### **Test 3: Cross-machine verification**

```bash
# Create file on NFS server
echo "test" | sudo -u rocky tee /srv/airflow/dags/nfs_test.txt

# Check on client
ls -la /mnt/airflow-dags/nfs_test.txt

# Should show rocky ownership on both
```

### **Test 4: Service logs**

```bash
# Check for permission errors
sudo journalctl -u airflow-scheduler -n 50
sudo journalctl -u airflow-worker -n 50

# Should not see permission denied errors
```

---

## **Prevention Best Practices**

### **1. Standardize UIDs/GIDs during initial setup**

Create a **user creation standard** for your infrastructure:

```bash
# On ALL machines, create users with SAME UID/GID
# Example: Always create rocky as UID 1000

# Method 1: Create user with specific UID
sudo useradd -u 1000 -g 1000 -m -s /bin/bash rocky

# Method 2: Modify during installation
# Use kickstart or cloud-init to enforce UIDs
```

### **2. Use centralized authentication**

Implement one of these:

**Option A: FreeIPA / Red Hat Identity Management**
- Centralized user/group management
- Automatic UID/GID synchronization
- Single source of truth

**Option B: LDAP**
- Lightweight Directory Access Protocol
- All machines authenticate against central directory

**Option C: SSSD (System Security Services Daemon)**
- Works with LDAP, AD, or FreeIPA
- Caches credentials locally

### **3. Document UID/GID assignments**

Maintain a spreadsheet:

| User | UID | GID | Purpose | Used On |
|------|-----|-----|---------|---------|
| rocky | 1000 | 1000 | Airflow admin | All machines |
| airflow | 1001 | 1001 | Service account | Schedulers, Workers |
| postgres | 26 | 26 | PostgreSQL | DB servers |

### **4. Use configuration management**

**Ansible example:**
```yaml
- name: Ensure rocky user exists with correct UID
  user:
    name: rocky
    uid: 1000
    group: rocky
    create_home: yes
    state: present

- name: Ensure rocky group exists with correct GID
  group:
    name: rocky
    gid: 1000
    state: present
```

### **5. NFS export options**

Add to `/etc/exports` for better consistency:
```bash
/srv/airflow/dags 10.101.20.0/24(rw,sync,no_root_squash,no_subtree_check,no_all_squash)
/srv/airflow/logs 10.101.20.0/24(rw,sync,no_root_squash,no_subtree_check,no_all_squash)
```

**Key options:**
- `no_root_squash`: Allow root on client to be root on server
- `no_all_squash`: Don't map all UIDs to nobody
- `all_squash,anonuid=1000,anongid=1000`: Force all access as specific UID (alternative approach)

### **6. Regular audits**

Create a monitoring script:

```bash
#!/bin/bash
# check_uid_consistency.sh

EXPECTED_UID=1000
SERVERS="nfs-1 nfs-2 haproxy-1 haproxy-2 scheduler-2 celery-1 celery-2"

for server in $SERVERS; do
    echo "Checking $server..."
    ssh $server "id rocky" | grep -q "uid=$EXPECTED_UID"
    if [ $? -eq 0 ]; then
        echo "✅ $server: UID correct"
    else
        echo "❌ $server: UID MISMATCH!"
    fi
done
```

---

## **Summary Checklist**

- [ ] Diagnosed UID/GID mismatch across all machines
- [ ] Identified conflicting users/groups
- [ ] Stopped all relevant services
- [ ] Changed conflicting user UID/GID
- [ ] Changed target user UID/GID
- [ ] Updated file ownership on NFS servers
- [ ] Synchronized secondary NFS server
- [ ] Remounted NFS shares on all clients
- [ ] Verified ownership shows correctly on clients
- [ ] Restarted all services
- [ ] Tested file creation and permissions
- [ ] Documented final UID/GID mapping
- [ ] Implemented prevention measures

---

## **Quick Reference Commands**

```bash
# Check UID/GID
id <username>

# Find files by numeric UID/GID
find /path -user 1001
find /path -group 1001

# Change user UID
usermod -u 1000 <username>

# Change group GID
groupmod -g 1000 <groupname>

# Update file ownership
find /path -user <old_uid> -exec chown -h <new_uid> {} \;
find /path -group <old_gid> -exec chgrp -h <new_gid> {} \;

# Remount NFS
umount -a -t nfs,nfs4
mount -a

# Re-export NFS shares
exportfs -ra

# Kill user processes
pkill -9 -u <username>
```

---

**This guide solves NFS UID/GID mismatch issues permanently. For production environments, implement centralized authentication (FreeIPA/LDAP) to prevent future occurrences.**
