# S02-HAProxy_Load_Balancer_HA_Setup.md

## High Availability Load Balancer with Keepalived and VIP

### Step 2.1:  Install HAProxy and Keepalived (VM1, VM2)

**Execute on both VM1 (haproxy-1) and VM2 (haproxy-2):**
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



#### **Create Systemd Configuration File for HAProxy**

**On airflow:**

```bash
sudo vi /etc/systemd/system/multi-user.target.wants/haproxy.service
```

Add the following content:

```
[Unit]
Description=HAProxy Load Balancer
After=network-online.target
Wants=network-online.target

[Service]
EnvironmentFile=-/etc/sysconfig/haproxy
Environment="CONFIG=/etc/haproxy/haproxy.cfg" "PIDFILE=/run/haproxy.pid" "CFGDIR=/etc/haproxy/conf.d"
ExecStartPre=/usr/sbin/haproxy -f $CONFIG -f $CFGDIR -c -q $OPTIONS
ExecStart=/usr/sbin/haproxy -Ws -f $CONFIG -f $CFGDIR -p $PIDFILE $OPTIONS
ExecReload=/usr/sbin/haproxy -f $CONFIG -f $CFGDIR -c -q $OPTIONS
ExecReload=/bin/kill -USR2 $MAINPID
KillMode=mixed
SuccessExitStatus=143
Type=notify

[Install]
WantedBy=multi-user.target
```


### Step 2.2: Configure HAProxy for PostgreSQL and Webserver Load Balancing

**⚠️ IMPORTANT: Replace `<POSTGRESQL_*_IP>` and `<HAPROXY_*_IP>` placeholders with your actual VM IP addresses.**

**On both VM1 and VM2, create identical HAProxy configuration:**
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
    # REPLACE_WITH_YOUR_POSTGRESQL_IPs - Update these IP addresses
    server postgresql-1 <POSTGRESQL_1_IP>:5432 maxconn 1000 check port 8008
    server postgresql-2 <POSTGRESQL_2_IP>:5432 maxconn 1000 check port 8008
    server postgresql-3 <POSTGRESQL_3_IP>:5432 maxconn 1000 check port 8008

# PostgreSQL Read-Only Load Balancing (Replicas)
listen postgres-readonly
    bind *:6000
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    # REPLACE_WITH_YOUR_POSTGRESQL_IPs - Update these IP addresses
    server postgresql-1 <POSTGRESQL_1_IP>:5432 maxconn 1000 check port 8008
    server postgresql-2 <POSTGRESQL_2_IP>:5432 maxconn 1000 check port 8008
    server postgresql-3 <POSTGRESQL_3_IP>:5432 maxconn 1000 check port 8008

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
    # REPLACE_WITH_YOUR_HAPROXY_IPs - Update these IP addresses
    server webserver1 <HAPROXY_1_IP>:8080 check
    server webserver2 <HAPROXY_2_IP>:8080 check
EOF

# Test HAProxy configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Enable HAProxy service
sudo systemctl enable haproxy
```

**🔧 Automated IP Replacement Helper for HAProxy Configuration:**
```bash
# Create script to replace IP placeholders in HAProxy configuration
# CUSTOMIZE these values with your actual VM IPs:
HAPROXY_1_IP="192.168.1.10"     # Replace with VM1 IP
HAPROXY_2_IP="192.168.1.11"     # Replace with VM2 IP
POSTGRESQL_1_IP="192.168.1.18"  # Replace with VM9 IP
POSTGRESQL_2_IP="192.168.1.19"  # Replace with VM10 IP
POSTGRESQL_3_IP="192.168.1.20"  # Replace with VM11 IP

# Replace placeholders in HAProxy configuration
sudo sed -i "s/<HAPROXY_1_IP>/$HAPROXY_1_IP/g" /etc/haproxy/haproxy.cfg
sudo sed -i "s/<HAPROXY_2_IP>/$HAPROXY_2_IP/g" /etc/haproxy/haproxy.cfg
sudo sed -i "s/<POSTGRESQL_1_IP>/$POSTGRESQL_1_IP/g" /etc/haproxy/haproxy.cfg
sudo sed -i "s/<POSTGRESQL_2_IP>/$POSTGRESQL_2_IP/g" /etc/haproxy/haproxy.cfg
sudo sed -i "s/<POSTGRESQL_3_IP>/$POSTGRESQL_3_IP/g" /etc/haproxy/haproxy.cfg

echo "HAProxy configuration updated. Verifying server entries:"
grep -A 3 -B 1 "server.*:" /etc/haproxy/haproxy.cfg
```

### Step 2.3: Create HAProxy Health Check Script

**On both VM1 and VM2:**
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

**⚠️ IMPORTANT: Replace `<MAIN_VIP>` with your chosen Main VIP address**

**On VM1 (Primary HAProxy - haproxy-1):**
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
        # REPLACE_WITH_YOUR_MAIN_VIP
        <MAIN_VIP>/24 dev $INTERFACE
    }
    track_script {
        chk_haproxy
    }
}
EOF

sudo systemctl enable keepalived
```

**On VM2 (Standby HAProxy - haproxy-2):**
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
        # REPLACE_WITH_YOUR_MAIN_VIP
        <MAIN_VIP>/24 dev $INTERFACE
    }
    track_script {
        chk_haproxy
    }
}
EOF

sudo systemctl enable keepalived
```

**🔧 Automated VIP Replacement Helper for Keepalived:**
```bash
# Replace VIP placeholder in keepalived configuration
# CUSTOMIZE this value with your chosen Main VIP:
MAIN_VIP="192.168.1.210"  # Replace with your chosen Main VIP

# Replace placeholder in keepalived configuration
sudo sed -i "s/<MAIN_VIP>/$MAIN_VIP/g" /etc/keepalived/keepalived.conf

echo "Keepalived configuration updated. Verifying VIP:"
grep -A 1 -B 1 "virtual_ipaddress" /etc/keepalived/keepalived.conf
```

### Step 2.5: Start HAProxy and Keepalived Services

**On VM1 (Primary - haproxy-1):**
```bash
# Start HAProxy first
sudo systemctl start haproxy
sudo systemctl status haproxy

# Start Keepalived (should acquire VIP)
sudo systemctl start keepalived
sudo systemctl status keepalived

# Verify VIP assignment
sleep 5
# REPLACE <MAIN_VIP> with your actual Main VIP address
ip addr show | grep <MAIN_VIP> && echo "VIP assigned to VM1: SUCCESS" || echo "VIP assignment: FAILED"
```

**On VM2 (Standby - haproxy-2):**
```bash
# Start HAProxy
sudo systemctl start haproxy
sudo systemctl status haproxy

# Start Keepalived (should be in standby mode)
sudo systemctl start keepalived
sudo systemctl status keepalived

# Verify standby mode (VIP should NOT be here initially)
sleep 5
# REPLACE <MAIN_VIP> with your actual Main VIP address
ip addr show | grep <MAIN_VIP> && echo "VIP incorrectly on VM2" || echo "VM2 in standby mode: CORRECT"
```

### Step 2.6: Test VIP Functionality

**Test VIP connectivity (run from VM1 after replacing placeholders):**
```bash
# IMPORTANT: Replace <MAIN_VIP> with your actual Main VIP address before running

# Test VIP is reachable
ping -c 3 <MAIN_VIP>

# Test HAProxy stats via VIP
curl -s http://<MAIN_VIP>:7000 | grep -i "HAProxy Statistics" && echo "HAProxy Stats via VIP: SUCCESS"

# Test PostgreSQL connectivity via VIP (should work after Patroni cluster is fully up)
export PGPASSWORD=postgres
psql -h <MAIN_VIP> -U postgres -p 5000 -c "SELECT 'PostgreSQL via VIP: SUCCESS';" || echo "PostgreSQL not ready yet (expected)"
```

**🔧 VIP Testing Helper Script:**
```bash
# Create VIP testing script with your actual VIP
# CUSTOMIZE this value:
MAIN_VIP="192.168.1.210"  # Replace with your actual Main VIP

# Test VIP functionality
echo "=== Testing VIP Functionality ==="
echo "Main VIP: $MAIN_VIP"

# Test VIP reachability
if ping -c 2 $MAIN_VIP >/dev/null 2>&1; then
    echo "✅ VIP reachable"
    
    # Test HAProxy stats
    if curl -s http://$MAIN_VIP:7000 | grep -q "HAProxy Statistics"; then
        echo "✅ HAProxy stats accessible via VIP"
    else
        echo "❌ HAProxy stats not accessible"
    fi
    
    # Test database connectivity
    export PGPASSWORD=postgres
    if psql -h $MAIN_VIP -U postgres -p 5000 -c "SELECT 1;" >/dev/null 2>&1; then
        echo "✅ Database accessible via VIP"
    else
        echo "⚠️ Database not ready yet (normal if Patroni cluster still starting)"
    fi
else
    echo "❌ VIP not reachable"
fi
```

### Step 2.7: Create Airflow Database and User

**Create database via VIP once PostgreSQL cluster is stable (run from VM1):**

⚠️ **IMPORTANT**: Replace `<MAIN_VIP>` with your actual Main VIP address in all commands below:

```bash
# Wait for PostgreSQL cluster to be fully operational
sleep 30

# Test PostgreSQL cluster connectivity via VIP
export PGPASSWORD=postgres
psql -h <MAIN_VIP> -U postgres -p 5000 -c "SELECT pg_is_in_recovery(), inet_server_addr();"

# Create Airflow database
psql -h <MAIN_VIP> -U postgres -p 5000 -c "
CREATE DATABASE airflow_db 
    WITH OWNER postgres 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8';"

# Create Airflow user with proper permissions
psql -h <MAIN_VIP> -U postgres -p 5000 -c "
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER USER airflow_user CREATEDB;"

# Grant schema permissions
psql -h <MAIN_VIP> -U postgres -p 5000 -d airflow_db -c "
GRANT ALL ON SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow_user;"

# Verify Airflow user connectivity
export PGPASSWORD=airflow_pass
psql -h <MAIN_VIP> -U airflow_user -p 5000 -d airflow_db -c "SELECT current_user, current_database();"
```

**🔧 Database Setup Helper Script:**
```bash
# Create database setup script with your actual VIP
# CUSTOMIZE this value:
MAIN_VIP="192.168.1.210"  # Replace with your actual Main VIP

# Database setup script
sudo tee /tmp/setup_airflow_db.sh << EOF
#!/bin/bash
MAIN_VIP="$MAIN_VIP"

echo "Setting up Airflow database via VIP: \$MAIN_VIP"

# Test connection first
export PGPASSWORD=postgres
if ! psql -h \$MAIN_VIP -U postgres -p 5000 -c "SELECT 1;" >/dev/null 2>&1; then
    echo "❌ Cannot connect to PostgreSQL via VIP"
    exit 1
fi

# Create database and user
echo "Creating Airflow database..."
psql -h \$MAIN_VIP -U postgres -p 5000 -c "CREATE DATABASE airflow_db WITH OWNER postgres ENCODING 'UTF8';"

echo "Creating Airflow user..."
psql -h \$MAIN_VIP -U postgres -p 5000 -c "CREATE USER airflow_user WITH PASSWORD 'airflow_pass'; GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user; ALTER USER airflow_user CREATEDB;"

echo "Setting up permissions..."
psql -h \$MAIN_VIP -U postgres -p 5000 -d airflow_db -c "GRANT ALL ON SCHEMA public TO airflow_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow_user;"

echo "Verifying setup..."
export PGPASSWORD=airflow_pass
psql -h \$MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database setup: SUCCESS';"

echo "✅ Airflow database setup completed"
EOF

chmod +x /tmp/setup_airflow_db.sh
# Run the script after customizing MAIN_VIP:
# /tmp/setup_airflow_db.sh
```

### Step 2.8: Test HAProxy Failover

**Test failover scenario (run from VM1):**
```bash
# CUSTOMIZE with your actual Main VIP:
MAIN_VIP="192.168.1.210"  # Replace with your actual Main VIP

echo "=== Initial HAProxy Failover Test ==="
curl -s http://$MAIN_VIP:7000 | head -1 && echo "HAProxy accessible via VIP"

# On VM1 - Stop HAProxy to trigger failover
sudo systemctl stop haproxy

# Wait for failover detection
echo "Waiting for failover..."
sleep 10

# Check VIP moved to VM2 (haproxy-2)
ssh rocky@haproxy-2 "ip addr show | grep $MAIN_VIP && echo 'VIP moved to VM2: SUCCESS' || echo 'Failover: FAILED'"

# Test services still accessible via VIP
export PGPASSWORD=airflow_pass
psql -h $MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database after failover: SUCCESS';" && echo "Database failover: SUCCESS"

# Restart VM1 HAProxy
sudo systemctl start haproxy

# Wait for failback
echo "Waiting for failback..."
sleep 10

# Check VIP returned to VM1 (higher priority)
ip addr show | grep $MAIN_VIP && echo "VIP returned to VM1: SUCCESS" || echo "Failback: CHECK MANUALLY"
```

### Step 2.9: Verification Checklist

**Run verification commands (customize VIP addresses first):**
```bash
# CUSTOMIZE these values:
MAIN_VIP="192.168.1.210"  # Replace with your actual Main VIP

echo "=== HAProxy Load Balancer HA Verification ==="

# 1. VIP responds
ping -c 2 $MAIN_VIP && echo "✅ VIP accessible" || echo "❌ VIP not accessible"

# 2. HAProxy running on both nodes
sudo systemctl is-active haproxy && echo "✅ VM1 HAProxy active" || echo "❌ VM1 HAProxy failed"
ssh rocky@haproxy-2 "sudo systemctl is-active haproxy" && echo "✅ VM2 HAProxy active" || echo "❌ VM2 HAProxy failed"

# 3. Keepalived running on both nodes
sudo systemctl is-active keepalived && echo "✅ VM1 Keepalived active" || echo "❌ VM1 Keepalived failed"
ssh rocky@haproxy-2 "sudo systemctl is-active keepalived" && echo "✅ VM2 Keepalived active" || echo "❌ VM2 Keepalived failed"

# 4. Database accessible via VIP
export PGPASSWORD=airflow_pass
psql -h $MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "SELECT 'Database via VIP: SUCCESS';" && echo "✅ Database via VIP working" || echo "❌ Database via VIP failed"

# 5. HAProxy stats accessible
curl -s http://$MAIN_VIP:7000 | grep -q "HAProxy Statistics" && echo "✅ HAProxy stats accessible" || echo "❌ HAProxy stats failed"

echo ""
echo "Load Balancer HA Setup Complete!"
echo "Main VIP: $MAIN_VIP"
echo "Database Write: $MAIN_VIP:5000"
echo "Database Read: $MAIN_VIP:6000"
echo "HAProxy Stats: http://$MAIN_VIP:7000"
echo "Future Webserver: http://$MAIN_VIP:8081"
```

**🔧 Complete Verification Script:**
```bash
# Create comprehensive verification script
# CUSTOMIZE this value:
MAIN_VIP="192.168.1.210"  # Replace with your actual Main VIP

sudo tee /usr/local/bin/verify_haproxy_ha.sh << EOF
#!/bin/bash
MAIN_VIP="$MAIN_VIP"

echo "=== HAProxy HA Verification Script ==="
echo "Main VIP: \$MAIN_VIP"
echo ""

# Test VIP accessibility
if ping -c 2 \$MAIN_VIP >/dev/null 2>&1; then
    echo "✅ VIP accessible"
    
    # Test HAProxy stats
    if curl -s http://\$MAIN_VIP:7000 | grep -q "HAProxy Statistics"; then
        echo "✅ HAProxy stats working"
    else
        echo "❌ HAProxy stats failed"
    fi
    
    # Test database connectivity
    export PGPASSWORD=airflow_pass
    if psql -h \$MAIN_VIP -U airflow_user -p 5000 -d airflow_db -c "SELECT 1;" >/dev/null 2>&1; then
        echo "✅ Database accessible via VIP"
    else
        echo "❌ Database connection failed"
    fi
else
    echo "❌ VIP not accessible"
fi

# Check which node has the VIP
if ip addr show | grep -q \$MAIN_VIP; then
    echo "✅ VM1 (haproxy-1) has VIP"
elif ssh -o ConnectTimeout=5 rocky@haproxy-2 "ip addr show | grep -q \$MAIN_VIP" 2>/dev/null; then
    echo "✅ VM2 (haproxy-2) has VIP"
else
    echo "❌ VIP not found on either node"
fi

echo ""
echo "Verification complete"
EOF

sudo chmod +x /usr/local/bin/verify_haproxy_ha.sh
# Run after customizing: sudo /usr/local/bin/verify_haproxy_ha.sh
```

This completes the HAProxy Load Balancer HA setup with automatic failover capabilities. The infrastructure now has:

✅ **Database HA**: 3-node PostgreSQL cluster with automatic failover  
✅ **Load Balancer HA**: Active/Passive HAProxy with VIP (`<MAIN_VIP>`)  
✅ **Health Monitoring**: Automated health checks and failover detection  
✅ **Service Discovery**: Single VIP for all database and future webserver access  

**Next Steps**: Once this load balancer HA setup is complete and verified, proceed to **S03-RabbitMQ_Cluster_HA_Setup.md** for message queue cluster configuration.


