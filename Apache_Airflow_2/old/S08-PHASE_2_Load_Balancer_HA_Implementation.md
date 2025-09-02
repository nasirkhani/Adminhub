**Goal**: Setup VM14 as HAProxy standby with Keepalived for VIP failover

## **Step 2.1: Prepare VM14 (HAProxy Standby + Webserver)**

### **Basic Setup:**
```bash
# SSH into VM14
ssh rocky@192.168.83.154

# Disable SELinux for simplified setup
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Set hostname
sudo nmcli general hostname haproxy2
sudo reboot

# After reboot, SSH back
ssh rocky@192.168.83.154

# Update system
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel nfs-utils haproxy keepalived curl
```

### **Configure Firewall:**
```bash
# Open required ports
sudo firewall-cmd --permanent --add-port=8080/tcp   # Webserver
sudo firewall-cmd --permanent --add-port=5000/tcp   # HAProxy PostgreSQL Write
sudo firewall-cmd --permanent --add-port=6000/tcp   # HAProxy PostgreSQL Read
sudo firewall-cmd --permanent --add-port=7000/tcp   # HAProxy Stats
sudo firewall-cmd --permanent --add-protocol=vrrp   # Keepalived VRRP
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

## **Step 2.2: Install Airflow on VM14**

```bash
# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow (CORRECTED CONSTRAINT URL)
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres,crypto]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install paramiko

# Fix permissions
sudo chmod +x /home/rocky/.local/bin/airflow
sudo chmod 755 /home/rocky /home/rocky/.local /home/rocky/.local/bin

# Create symlinks and directories
ln -s /mnt/airflow-dags ~/airflow/dags
mkdir -p ~/airflow/logs ~/airflow/plugins

# Copy configuration from VM1
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@192.168.83.129:/home/rocky/airflow/config ~/airflow/ 2>/dev/null || mkdir ~/airflow/config
scp -r rocky@192.168.83.129:/home/rocky/airflow/utils ~/airflow/ 2>/dev/null || mkdir ~/airflow/utils

# Copy SSH keys
mkdir -p ~/.ssh
scp rocky@192.168.83.129:/home/rocky/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519

# Create utility modules
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

## **Step 2.3: Configure HAProxy on VM14 (Standby)**

### **Copy HAProxy Configuration from VM1:**
```bash
# On VM14 - Copy HAProxy config from VM1
scp rocky@192.168.83.129:/etc/haproxy/haproxy.cfg /tmp/haproxy.cfg
sudo cp /tmp/haproxy.cfg /etc/haproxy/haproxy.cfg
```

### **Verify HAProxy Configuration:**
```bash
# On VM14 - Check HAProxy config
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Enable but don't start yet (standby mode)
sudo systemctl enable haproxy
```

## **Step 2.4: Configure Keepalived on Both Nodes (CORRECTED)**

### **On VM1 (Primary HAProxy) - Install and Configure Keepalived:**
```bash
# On VM1 - Install Keepalived
sudo dnf install -y keepalived curl

# Configure firewall for VRRP
sudo firewall-cmd --permanent --add-protocol=vrrp
sudo firewall-cmd --reload

# Get correct interface name (CORRECTED)
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Interface: $INTERFACE"

# Create proper health check script (CORRECTED)
sudo tee /usr/local/bin/check_haproxy.sh << 'EOF'
#!/bin/bash
# Check if HAProxy is running and responding
if systemctl is-active --quiet haproxy; then
    # Also check if HAProxy stats port is responding
    if curl -f -s --max-time 2 http://localhost:7000 >/dev/null 2>&1; then
        exit 0  # HAProxy is healthy
    else
        exit 1  # HAProxy not responding
    fi
else
    exit 1  # HAProxy service not running
fi
EOF

sudo chmod +x /usr/local/bin/check_haproxy.sh

# Test the script
sudo /usr/local/bin/check_haproxy.sh && echo "Health check script: OK" || echo "Health check script: FAILED"

# Create Keepalived configuration (CORRECTED)
sudo tee /etc/keepalived/keepalived.conf << EOF
global_defs {
    router_id AIRFLOW_HA_PRIMARY
    script_user root
    enable_script_security
}

vrrp_script chk_haproxy {
    script "/usr/local/bin/check_haproxy.sh"
    interval 2
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_AIRFLOW {
    state MASTER
    interface $INTERFACE
    virtual_router_id 51
    priority 110
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass airflow_ha_2024
    }
    virtual_ipaddress {
        192.168.83.210/24 dev $INTERFACE
    }
    track_script {
        chk_haproxy
    }
}
EOF

sudo systemctl enable keepalived
```

### **On VM14 (Standby HAProxy) - Configure Keepalived:**
```bash
# On VM14 - Get correct interface name (CORRECTED)
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Interface: $INTERFACE"

# Create proper health check script (CORRECTED)
sudo tee /usr/local/bin/check_haproxy.sh << 'EOF'
#!/bin/bash
# Check if HAProxy is running and responding
if systemctl is-active --quiet haproxy; then
    # Also check if HAProxy stats port is responding
    if curl -f -s --max-time 2 http://localhost:7000 >/dev/null 2>&1; then
        exit 0  # HAProxy is healthy
    else
        exit 1  # HAProxy not responding
    fi
else
    exit 1  # HAProxy service not running
fi
EOF

sudo chmod +x /usr/local/bin/check_haproxy.sh

# Test the script
sudo /usr/local/bin/check_haproxy.sh && echo "Health check script: OK" || echo "Health check script: FAILED"

# Create Keepalived configuration (CORRECTED)
sudo tee /etc/keepalived/keepalived.conf << EOF
global_defs {
    router_id AIRFLOW_HA_STANDBY
    script_user root
    enable_script_security
}

vrrp_script chk_haproxy {
    script "/usr/local/bin/check_haproxy.sh"
    interval 2
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_AIRFLOW {
    state BACKUP
    interface $INTERFACE
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass airflow_ha_2024
    }
    virtual_ipaddress {
        192.168.83.210/24 dev $INTERFACE
    }
    track_script {
        chk_haproxy
    }
}
EOF

sudo systemctl enable keepalived
```

## **Step 2.5: Start HAProxy and Keepalived Services**

### **Start Services on VM1 (Primary):**
```bash
# On VM1 - HAProxy already running, just start Keepalived
sudo systemctl start keepalived
sudo systemctl status keepalived
sudo systemctl status haproxy

# Check VIP assignment
ip addr show | grep 192.168.83.210
```

### **Start Services on VM14 (Standby):**
```bash
# On VM14 - Start HAProxy and Keepalived
sudo systemctl start haproxy
sudo systemctl start keepalived

# Check status
sudo systemctl status haproxy
sudo systemctl status keepalived

# Verify standby mode (VIP should NOT be here initially)
ip addr show | grep 192.168.83.210 || echo "VIP not on standby - CORRECT"
```

## **Step 2.6: Update Airflow Configuration to Use VIP**

### **Update VM1 Airflow Configuration:**
```bash
# On VM1 - Update airflow.cfg to use VIP for database connections
sed -i 's|postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
sed -i 's|db+postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|db+postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
```

### **Update VM13 Airflow Configuration:**
```bash
# On VM13 - Update airflow.cfg to use VIP
sed -i 's|postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
sed -i 's|db+postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|db+postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
```

### **Update VM4 Airflow Configuration:**
```bash
# On VM4 - Update airflow.cfg to use VIP
sed -i 's|postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
sed -i 's|db+postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db|db+postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db|g' ~/airflow/airflow.cfg
```

## **Step 2.7: Restart Airflow Services to Use VIP**

### **Restart Services on VM1:**
```bash
# On VM1 - Restart Airflow services
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
sudo systemctl restart airflow-flower
```

### **Restart Services on VM13:**
```bash
# On VM13 - Restart scheduler
sudo systemctl restart airflow-scheduler
```

### **Restart Services on VM4:**
```bash
# On VM4 - Restart worker
sudo systemctl restart airflow-worker
```

## **Step 2.8: Test Proper HAProxy Failover (CORRECTED)**

### **Test 1: Verify Initial State**
```bash
# Check VIP location
echo "=== Initial VIP Status ==="
ip addr show | grep 192.168.83.210 && echo "VIP on VM1" || echo "VIP NOT on VM1"
ssh rocky@192.168.83.154 "ip addr show | grep 192.168.83.210 && echo 'VIP on VM14' || echo 'VIP NOT on VM14'"

# Test health check scripts
echo "=== Health Check Tests ==="
sudo /usr/local/bin/check_haproxy.sh && echo "VM1 HAProxy health: OK" || echo "VM1 HAProxy health: FAILED"
ssh rocky@192.168.83.154 "sudo /usr/local/bin/check_haproxy.sh && echo 'VM14 HAProxy health: OK' || echo 'VM14 HAProxy health: FAILED'"
```

### **Test 2: Test Database Connectivity via VIP**
```bash
# On VM1 - Test database connection via VIP
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database via VIP: SUCCESS';"

# Test HAProxy stats via VIP
curl -s http://192.168.83.210:7000 | grep -i "HAProxy Statistics" && echo "HAProxy Stats via VIP: SUCCESS"
```

### **Test 3: Simulate VM1 HAProxy Failure (CORRECTED FAILOVER TEST)**
```bash
# Test database connectivity before failover
echo "=== Before Failover ==="
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'DB before failover: SUCCESS';"

# Stop HAProxy on VM1
echo "=== Stopping VM1 HAProxy ==="
sudo systemctl stop haproxy

# Wait for failover (should be faster with proper health check)
echo "Waiting for failover..."
sleep 8

# Check VIP moved to VM14
echo "=== After HAProxy Stop ==="
ip addr show | grep 192.168.83.210 && echo "VIP still on VM1: PROBLEM" || echo "VIP moved from VM1: OK"
ssh rocky@192.168.83.154 "ip addr show | grep 192.168.83.210 && echo 'VIP moved to VM14: SUCCESS' || echo 'VIP NOT on VM14: PROBLEM'"

# Test database connectivity after failover
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'DB after failover: SUCCESS';" && echo "Failover: SUCCESS" || echo "Failover: FAILED"

# Test Airflow still works
airflow db check && echo "Airflow after failover: SUCCESS" || echo "Airflow after failover: FAILED"

# Restart VM1 HAProxy
echo "=== Restarting VM1 HAProxy ==="
sudo systemctl start haproxy

# Wait for failback
echo "Waiting for failback..."
sleep 8

# Check VIP moved back to VM1 (higher priority)
echo "=== After HAProxy Restart ==="
ip addr show | grep 192.168.83.210 && echo "VIP back on VM1: SUCCESS" || echo "VIP NOT back on VM1"
ssh rocky@192.168.83.154 "ip addr show | grep 192.168.83.210 && echo 'VIP still on VM14' || echo 'VIP moved from VM14: OK'"

# Test database connectivity after failback
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'DB after failback: SUCCESS';" && echo "Failback: SUCCESS" || echo "Failback: FAILED"
```

### **Test 4: Monitor Keepalived Logs**
```bash
# Check Keepalived logs on both nodes
echo "=== VM1 Keepalived Logs ==="
sudo journalctl -u keepalived --since "5 minutes ago" | grep -E "(MASTER|BACKUP|VIP|transition)"

echo "=== VM14 Keepalived Logs ==="
ssh rocky@192.168.83.154 "sudo journalctl -u keepalived --since '5 minutes ago' | grep -E '(MASTER|BACKUP|VIP|transition)'"
```

### **Test 5: Verify Airflow Still Works**
```bash
# Test Airflow CLI via VIP
airflow db check

# Check DAG list
airflow dags list | head -5

# Check scheduler jobs
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "
SELECT hostname, state, latest_heartbeat 
FROM job 
WHERE job_type = 'SchedulerJob' 
AND state = 'running' 
ORDER BY latest_heartbeat DESC;
"
```

## ✅ **Phase 2 Corrected Verification**

Run these commands to verify Phase 2 completion:

```bash
# 1. VIP is pingable
ping -c 3 192.168.83.210

# 2. HAProxy is running on both nodes
sudo systemctl is-active haproxy  # On VM1
ssh rocky@192.168.83.154 "sudo systemctl is-active haproxy 2>/dev/null"  # On VM14

# 3. Keepalived is running on both nodes
sudo systemctl is-active keepalived  # On VM1
ssh rocky@192.168.83.154 "sudo systemctl is-active keepalived 2>/dev/null"  # On VM14

# 4. Test failover works
sudo systemctl stop haproxy
sleep 10
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Failover test: SUCCESS';" && echo "FAILOVER WORKS" || echo "FAILOVER FAILED"

# 5. Test failback works
sudo systemctl start haproxy  
sleep 10
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Failback test: SUCCESS';" && echo "FAILBACK WORKS" || echo "FAILBACK FAILED"

# 6. Airflow services using VIP
airflow db check && echo "Airflow using VIP: SUCCESS"
```

## **Expected Corrected Results**

✅ **VIP (192.168.83.210)**: Accessible and responds to ping  
✅ **VM1**: HAProxy + Keepalived active, VIP assigned (primary)  
✅ **VM14**: HAProxy + Keepalived active, VIP standby  
✅ **Database**: Accessible via VIP from all Airflow components  
✅ **Failover**: VIP moves to VM14 when VM1 HAProxy fails (CORRECTED)  
✅ **Failback**: VIP returns to VM1 when VM1 HAProxy restarts (CORRECTED)  
✅ **Health Check**: Proper script detects HAProxy failure (CORRECTED)  

---

## **Key Corrections Made**

1. **Fixed Constraint URL**: Changed from `constraints-${AIRFLOW_VERSION}.txt` to `constraints-${PYTHON_VERSION}.txt`
2. **Fixed Interface Detection**: Used `$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')` instead of hardcoded `ens33`
3. **Fixed Health Check**: Created proper `/usr/local/bin/check_haproxy.sh` script that actually detects HAProxy failures and triggers VIP failover

## **next step: Phase 3**

overview of next step: **Phase 3: Webserver HA**

1. Create webserver service on VM14
2. Update HAProxy to load balance webservers 
3. Test webserver failover
4. Verify complete HA setup
