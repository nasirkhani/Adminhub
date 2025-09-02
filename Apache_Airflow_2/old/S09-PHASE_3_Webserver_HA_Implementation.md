**Goal**: Setup webserver on VM14 and configure HAProxy to load balance webservers between VM1 and VM14

## Step 3.1: Create Webserver Service on VM14

### Create Webserver SystemD Service:
```bash
# On VM14 - Create webserver service
sudo tee /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Airflow Webserver (HA Node 2)
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
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver-ha2
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver
```

### Test Webserver Configuration:
```bash
# On VM14 - Test database connectivity first
airflow db check

# Start webserver
sudo systemctl start airflow-webserver

# Check status
sudo systemctl status airflow-webserver

# Test webserver is responding locally (follow redirects)
sleep 15
curl -s -L http://localhost:8080 | grep -i "airflow" && echo "VM14 Webserver: SUCCESS" || echo "VM14 Webserver: FAILED"
```

## Step 3.2: Update HAProxy Configuration for Webserver Load Balancing

### Update HAProxy Configuration on VM1:
```bash
# On VM1 - Backup current HAProxy config
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup

# Create new HAProxy configuration with webserver load balancing
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

# HAProxy Statistics
listen stats
    mode http
    bind *:7000
    stats enable
    stats uri /
    stats refresh 30s
    stats show-node
    stats show-legends

# PostgreSQL Load Balancing (existing)
listen postgres
    bind *:5000
    option httpchk
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008

# PostgreSQL Read-Only Load Balancing (existing)
listen postgres-readonly
    bind *:6000
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008

# Airflow Webserver Load Balancing (using port 8081 to avoid conflicts)
frontend airflow_frontend
    mode http
    bind *:8081
    default_backend airflow_webservers

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

# Reload HAProxy with new configuration
sudo systemctl reload haproxy
sudo systemctl status haproxy
```

### Update HAProxy Configuration on VM14:
```bash
# On VM14 - Copy the same configuration from VM1
scp rocky@192.168.83.129:/etc/haproxy/haproxy.cfg /tmp/haproxy.cfg
sudo cp /tmp/haproxy.cfg /etc/haproxy/haproxy.cfg

# Test configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Reload HAProxy
sudo systemctl reload haproxy
sudo systemctl status haproxy
```

## Step 3.3: Update Firewall for Webserver Load Balancing

### Update Firewall on VM1 and VM14:
```bash
# On VM1
sudo firewall-cmd --permanent --add-port=8081/tcp   # Webserver frontend (HAProxy)
sudo firewall-cmd --reload

# On VM14  
sudo firewall-cmd --permanent --add-port=8081/tcp   # Webserver frontend (HAProxy)
sudo firewall-cmd --reload
```

## Step 3.4: Test Webserver Load Balancing

### Test Load Balancing via VIP:
```bash
# Test direct access to individual webservers
echo "=== Testing Individual Webservers ==="
curl -s -L -I http://192.168.83.129:8080 | head -1
curl -s -L -I http://192.168.83.154:8080 | head -1

# Test load balanced access via VIP (using port 8081)
echo "=== Testing Load Balanced Access via VIP ==="
curl -s -L -I http://192.168.83.210:8081 | head -1

# Test multiple requests to see load balancing
echo "=== Testing Load Balancing Distribution ==="
for i in {1..6}; do
    echo "Request $i:"
    curl -s -L -I http://192.168.83.210:8081 | head -1
    sleep 1
done
```

### Test Webserver Health Checks:
```bash
# Check HAProxy stats to see webserver health
curl -s http://192.168.83.210:7000 | grep -A5 -B5 "webserver"

# Or open in browser: http://192.168.83.210:7000
echo "Open HAProxy stats at: http://192.168.83.210:7000"
echo "Check 'airflow_webservers' backend status"
```

## Step 3.5: Test Webserver Failover

### Test 1: Stop VM1 Webserver
```bash
# On VM1 - Stop webserver
sudo systemctl stop airflow-webserver

# Wait for health check to detect failure
sleep 15

# Test VIP still serves webserver (should route to VM14)
echo "=== After VM1 Webserver Stop ==="
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver via VIP after VM1 stop: SUCCESS" || echo "Webserver failover: FAILED"

# Check HAProxy stats
curl -s http://192.168.83.210:7000 | grep -A2 -B2 "webserver1.*DOWN"

# Restart VM1 webserver
sudo systemctl start airflow-webserver
sleep 15

echo "=== After VM1 Webserver Restart ==="
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver after VM1 restart: SUCCESS"
```

### Test 2: Stop VM14 Webserver
```bash
# On VM14 - Stop webserver
sudo systemctl stop airflow-webserver

# Wait for health check to detect failure
sleep 15

# Test VIP still serves webserver (should route to VM1)
echo "=== After VM14 Webserver Stop ==="
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver via VIP after VM14 stop: SUCCESS" || echo "Webserver failover: FAILED"

# Restart VM14 webserver
sudo systemctl start airflow-webserver
sleep 15

echo "=== After VM14 Webserver Restart ==="
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver after VM14 restart: SUCCESS"
```

### Test 3: Complete HAProxy Failover with Webserver
```bash
# Test complete failover: Stop VM1 HAProxy (which should move VIP to VM14)
echo "=== Testing Complete HAProxy Failover ==="

# Stop VM1 HAProxy
sudo systemctl stop haproxy

# Wait for VIP failover
sleep 10

# Test webserver still accessible via VIP (now through VM14's HAProxy)
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver via VIP after HAProxy failover: SUCCESS" || echo "Complete failover: FAILED"

# Test HAProxy stats via VIP (now from VM14)
curl -s http://192.168.83.210:7000 | grep -i "statistics" && echo "HAProxy stats after failover: SUCCESS"

# Restart VM1 HAProxy
sudo systemctl start haproxy
sleep 10

# Test everything still works after failback
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" && echo "Webserver after HAProxy failback: SUCCESS"
```

## Step 3.6: Test Full Airflow UI Access

### Access Airflow UI via Load Balanced VIP:
```bash
echo "=== Airflow UI Access Test ==="
echo "Open your browser and navigate to:"
echo "Load Balanced (Recommended): http://192.168.83.210:8081"
echo "Direct VM1 Access: http://192.168.83.129:8080"
echo "Direct VM14 Access: http://192.168.83.154:8080"
echo ""
echo "Login credentials:"
echo "Username: admin"
echo "Password: admin123"
echo ""
echo "You should be able to:"
echo "- Login successfully"
echo "- See DAGs list"
echo "- Navigate through UI"
echo "- Trigger DAGs"
echo ""
echo "Refresh the page multiple times - you'll be load balanced between VM1 and VM14"
```

### Test DAG Execution via Load Balanced UI:
```bash
# Trigger test DAG via CLI to verify complete integration
airflow dags unpause test_distributed_setup
airflow dags trigger test_distributed_setup

# Wait and check results
sleep 30
airflow dags state test_distributed_setup $(date +%Y-%m-%d)

# Check task execution
airflow tasks states-for-dag-run test_distributed_setup $(date +%Y-%m-%d)
```

## Phase 3 Complete Verification

Run these commands to verify Phase 3 completion:

```bash
# 1. Both webservers running
echo "=== Webserver Status ==="
sudo systemctl is-active airflow-webserver  # On VM1
ssh rocky@192.168.83.154 "sudo systemctl is-active airflow-webserver 2>/dev/null"  # On VM14

# 2. Webserver accessible via VIP (using port 8081)
curl -s -L -I http://192.168.83.210:8081 | head -1

# 3. Load balancing working
echo "=== Load Balancing Test ==="
for i in {1..4}; do
    curl -s -L -I http://192.168.83.210:8081 | head -1
done

# 4. HAProxy stats show both webservers
curl -s http://192.168.83.210:7000 | grep -A5 "airflow_webservers"

# 5. Complete system health
echo "=== Complete System Health ==="
airflow db check && echo "Database: OK"
airflow dags list | head -3 && echo "Scheduler: OK"
curl -s -L http://192.168.83.210:8081 | grep -i "airflow" >/dev/null && echo "Webserver: OK"

# 6. Access instructions
echo ""
echo "COMPLETE HA AIRFLOW SETUP READY!"
echo "=================================="
echo "Airflow UI (Load Balanced): http://192.168.83.210:8081"
echo "Airflow UI (Direct VM1): http://192.168.83.129:8080"
echo "Airflow UI (Direct VM14): http://192.168.83.154:8080"
echo "Flower: http://192.168.83.210:5555"  
echo "HAProxy Stats: http://192.168.83.210:7000"
echo "Login: admin / admin123"
```

## Final Architecture Status

```
ENTERPRISE AIRFLOW COMPLETE HA CLUSTER

VM1 (airflow) - Primary Node:
├── Scheduler (HA with VM13)
├── Webserver (Load Balanced with VM14)
├── HAProxy Primary (PostgreSQL + Webserver LB)
├── Keepalived Primary (VIP: 192.168.83.210)
└── Flower Monitor

VM13 (scheduler2) - Scheduler HA:
├── Scheduler (HA with VM1)
└── Multi-scheduler coordination

VM14 (haproxy2) - Standby Node:
├── Webserver (Load Balanced with VM1)
├── HAProxy Standby (PostgreSQL + Webserver LB)
└── Keepalived Standby (VIP failover)

High Availability Features:
├── Scheduler HA: Multi-scheduler (VM1 + VM13)
├── Webserver HA: Load Balanced (VM1 + VM14)
├── Load Balancer HA: Active/Passive (VM1 + VM14)
├── Database HA: Patroni Cluster (VM8,9,10)
├── Message Queue HA: RabbitMQ Cluster (VM5,6,7)
├── Shared Storage HA: NFS Active/Passive (VM2 + VM12)
└── Single Entry Point: VIP (192.168.83.210)
```

## Achieved HA Goals

### Priority 1: Scheduler HA
- **VM1 + VM13**: Dual schedulers with coordination
- **Automatic failover**: If one scheduler fails, the other continues
- **Load distribution**: DAG processing shared between schedulers

### Priority 2: Load Balancer HA
- **VIP (192.168.83.210)**: Single entry point for all services
- **VM1 + VM14**: Active/Passive HAProxy with Keepalived
- **Automatic failover**: VIP moves when HAProxy fails
- **Zero downtime**: Database and webserver remain accessible

### Priority 3: Webserver HA
- **VM1 + VM14**: Dual webservers load balanced by HAProxy
- **Round-robin**: User requests distributed across webservers
- **Health checks**: Failed webservers automatically removed from pool
- **Session handling**: Stateless webserver design


**You now have a complete enterprise-grade, highly available Apache Airflow infrastructure!**

**Key Benefits:**
- Zero Single Points of Failure
- Automatic Failover for all critical components
- Load Distribution across multiple nodes
- Unified Access through single VIP
- Production Ready monitoring and health checks

**Access your HA Airflow cluster at: http://192.168.83.210:8081**
