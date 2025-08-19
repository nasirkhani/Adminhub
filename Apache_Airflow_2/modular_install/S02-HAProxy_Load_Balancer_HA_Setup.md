## High Availability Load Balancer with Keepalived and VIP

### Step 2.1: Install HAProxy and Keepalived (VM1, VM14)

**Execute on both VM1 (airflow) and VM14 (haproxy2):**
```bash
# Install HAProxy and Keepalived
sudo dnf install -y haproxy keepalived curl

# Configure firewall for HAProxy and VIP
sudo firewall-cmd --permanent --add-port=5000/tcp   # HAProxy PostgreSQL Write
sudo firewall-cmd --permanent --add-port=6000/tcp   # HAProxy PostgreSQL Read
sudo firewall-cmd --permanent --add-port=7000/tcp   # HAProxy Stats
sudo firewall-cmd --permanent --add-port=8081/tcp   # Webserver frontend (future)
sudo firewall-cmd --permanent --add-protocol=vrrp   # Keepalived VRRP
sudo firewall-cmd --reload
```

### Step 2.2: Configure HAProxy for PostgreSQL and Webserver Load Balancing

**On both VM1 and VM14, create identical HAProxy configuration:**
```bash
sudo tee /etc/haproxy/haproxy.cfg << EOF
global
    log 127.0.0.1 local2
    chroot /var/lib/haproxy
    pidfile /var/run/haproxy.pid
    maxconn 6000
    user haproxy
    group haproxy
    daemon
    stats socket /var/lib/haproxy/stats

defaults
    mode tcp
    log global
    retries 3
    timeout queue 1m
    timeout connect 10s
    timeout client 31m
    timeout server 31m
    timeout check 10s
    maxconn 3000

# HAProxy Statistics Dashboard
listen stats
    mode http
    bind *:7000
    stats enable
    stats uri /
    stats refresh 30s
    stats show-node
    stats show-legends

# PostgreSQL Write Load Balancing (Primary)
listen postgres
    bind *:5000
    option httpchk
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008

# PostgreSQL Read-Only Load Balancing (Replicas)
listen postgres-readonly
    bind *:6000
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008

# Airflow Webserver Load Balancing Frontend
frontend airflow_frontend
    mode http
    bind *:8081
    default_backend airflow_webservers

# Airflow Webserver Load Balancing Backend
backend airflow_webservers
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    default-server inter 10s fall 3 rise 2
    server webserver1 192.168.83.129:8080 check
    server webserver2 192.168.83.154:8080 check
EOF

# Test HAProxy configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Enable HAProxy service
sudo systemctl enable haproxy
```

### Step 2.3: Create HAProxy Health Check Script

**On both VM1 and VM14:**
```bash
# Create comprehensive health check script
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

# Test the health check script
sudo /usr/local/bin/check_haproxy.sh && echo "Health check script: OK" || echo "Health check script: FAILED (Expected until HAProxy starts)"
```

### Step 2.4: Configure Keepalived for VIP Management

**On VM1 (Primary HAProxy):**
```bash
# Get network interface dynamically
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Network Interface: $INTERFACE"

# Create Keepalived configuration for PRIMARY
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

**On VM14 (Standby HAProxy):**
```bash
# Get network interface dynamically
INTERFACE=$(ip route get 8.8.8.8 | grep -oP 'dev \K\S+')
echo "Network Interface: $INTERFACE"

# Create Keepalived configuration for STANDBY
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

### Step 2.5: Start HAProxy and Keepalived Services

**On VM1 (Primary):**
```bash
# Start HAProxy first
sudo systemctl start haproxy
sudo systemctl status haproxy

# Start Keepalived (should acquire VIP)
sudo systemctl start keepalived
sudo systemctl status keepalived

# Verify VIP assignment
sleep 5
ip addr show | grep 192.168.83.210 && echo "VIP assigned to VM1: SUCCESS" || echo "VIP assignment: FAILED"
```

**On VM14 (Standby):**
```bash
# Start HAProxy
sudo systemctl start haproxy
sudo systemctl status haproxy

# Start Keepalived (should be in standby mode)
sudo systemctl start keepalived
sudo systemctl status keepalived

# Verify standby mode (VIP should NOT be here initially)
sleep 5
ip addr show | grep 192.168.83.210 && echo "VIP incorrectly on VM14" || echo "VM14 in standby mode: CORRECT"
```

### Step 2.6: Test VIP Functionality

**Test VIP connectivity:**
```bash
# From VM1 - Test VIP is reachable
ping -c 3 192.168.83.210

# Test HAProxy stats via VIP
curl -s http://192.168.83.210:7000 | grep -i "HAProxy Statistics" && echo "HAProxy Stats via VIP: SUCCESS"

# Test PostgreSQL connectivity via VIP (should work after Patroni cluster is fully up)
export PGPASSWORD=postgres
psql -h 192.168.83.210 -U postgres -p 5000 -c "SELECT 'PostgreSQL via VIP: SUCCESS';" || echo "PostgreSQL not ready yet (expected)"
```

### Step 2.7: Create Airflow Database and User

**Create database via VIP once PostgreSQL cluster is stable:**
```bash
# Wait for PostgreSQL cluster to be fully operational
sleep 30

# Test PostgreSQL cluster connectivity via VIP
export PGPASSWORD=postgres
psql -h 192.168.83.210 -U postgres -p 5000 -c "SELECT pg_is_in_recovery(), inet_server_addr();"

# Create Airflow database
psql -h 192.168.83.210 -U postgres -p 5000 -c "
CREATE DATABASE airflow_db 
    WITH OWNER postgres 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8';"

# Create Airflow user with proper permissions
psql -h 192.168.83.210 -U postgres -p 5000 -c "
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER USER airflow_user CREATEDB;"

# Grant schema permissions
psql -h 192.168.83.210 -U postgres -p 5000 -d airflow_db -c "
GRANT ALL ON SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow_user;"

# Verify Airflow user connectivity
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT current_user, current_database();"
```

### Step 2.8: Test HAProxy Failover

**Test failover scenario:**
```bash
# Test initial state
echo "=== Initial HAProxy Failover Test ==="
curl -s http://192.168.83.210:7000 | head -1 && echo "HAProxy accessible via VIP"

# On VM1 - Stop HAProxy to trigger failover
sudo systemctl stop haproxy

# Wait for failover detection
echo "Waiting for failover..."
sleep 10

# Check VIP moved to VM14
ssh rocky@192.168.83.154 "ip addr show | grep 192.168.83.210 && echo 'VIP moved to VM14: SUCCESS' || echo 'Failover: FAILED'"

# Test services still accessible via VIP
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database after failover: SUCCESS';" && echo "Database failover: SUCCESS"

# Restart VM1 HAProxy
sudo systemctl start haproxy

# Wait for failback
echo "Waiting for failback..."
sleep 10

# Check VIP returned to VM1 (higher priority)
ip addr show | grep 192.168.83.210 && echo "VIP returned to VM1: SUCCESS" || echo "Failback: CHECK MANUALLY"
```

### Step 2.9: Verification Checklist

**Run verification commands:**
```bash
echo "=== HAProxy Load Balancer HA Verification ==="

# 1. VIP responds
ping -c 2 192.168.83.210 && echo "✅ VIP accessible" || echo "❌ VIP not accessible"

# 2. HAProxy running on both nodes
sudo systemctl is-active haproxy && echo "✅ VM1 HAProxy active" || echo "❌ VM1 HAProxy failed"
ssh rocky@192.168.83.154 "sudo systemctl is-active haproxy" && echo "✅ VM14 HAProxy active" || echo "❌ VM14 HAProxy failed"

# 3. Keepalived running on both nodes
sudo systemctl is-active keepalived && echo "✅ VM1 Keepalived active" || echo "❌ VM1 Keepalived failed"
ssh rocky@192.168.83.154 "sudo systemctl is-active keepalived" && echo "✅ VM14 Keepalived active" || echo "❌ VM14 Keepalived failed"

# 4. Database accessible via VIP
export PGPASSWORD=airflow_pass
psql -h 192.168.83.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database via VIP: SUCCESS';" && echo "✅ Database via VIP working" || echo "❌ Database via VIP failed"

# 5. HAProxy stats accessible
curl -s http://192.168.83.210:7000 | grep -q "HAProxy Statistics" && echo "✅ HAProxy stats accessible" || echo "❌ HAProxy stats failed"

echo ""
echo "Load Balancer HA Setup Complete!"
echo "Main VIP: 192.168.83.210"
echo "Database Write: 192.168.83.210:5000"
echo "Database Read: 192.168.83.210:6000"
echo "HAProxy Stats: http://192.168.83.210:7000"
echo "Future Webserver: http://192.168.83.210:8081"
```

This completes the HAProxy Load Balancer HA setup with automatic failover capabilities. The infrastructure now has:

✅ **Database HA**: 3-node PostgreSQL cluster with automatic failover  
✅ **Load Balancer HA**: Active/Passive HAProxy with VIP (192.168.83.210)  
✅ **Health Monitoring**: Automated health checks and failover detection  
✅ **Service Discovery**: Single VIP for all database and future webserver access  
