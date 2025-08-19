## High Availability Message Queue Cluster for Celery

### Step 3.1: Install RabbitMQ (VM5, VM6, VM7)

**Execute on all three RabbitMQ nodes:**
```bash
# Download and install RabbitMQ 3.13.7 (stable version)
wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.7/rabbitmq-server-3.13.7-1.el8.noarch.rpm
sudo rpm --import https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
sudo dnf install -y socat logrotate
sudo dnf install -y ./rabbitmq-server-3.13.7-1.el8.noarch.rpm

# Configure firewall for RabbitMQ cluster
sudo firewall-cmd --permanent --add-port=5672/tcp   # AMQP
sudo firewall-cmd --permanent --add-port=15672/tcp  # Management UI
sudo firewall-cmd --permanent --add-port=25672/tcp  # Inter-node communication
sudo firewall-cmd --permanent --add-port=4369/tcp   # Erlang Port Mapper
sudo firewall-cmd --reload

# Enable but don't start yet (need to configure clustering first)
sudo systemctl enable rabbitmq-server
```

### Step 3.2: Configure Erlang Cookie for Clustering

**On VM5 (mq1) - Generate and start first node:**
```bash
# Start RabbitMQ to generate the Erlang cookie
sudo systemctl start rabbitmq-server
sudo systemctl stop rabbitmq-server

# Get the generated Erlang cookie
COOKIE=$(sudo cat /var/lib/rabbitmq/.erlang.cookie)
echo "Erlang Cookie for cluster: $COOKIE"

# Save this cookie value - you'll need it for VM6 and VM7
echo "IMPORTANT: Copy this cookie to VM6 and VM7"
```

**On VM6 (mq2) and VM7 (mq3) - Set the same cookie:**
```bash
# Replace COOKIE_VALUE with the actual cookie from VM5
# Example: COOKIE="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
COOKIE="YOUR_COOKIE_FROM_VM5_HERE"

# Set the same cookie on VM6 and VM7
echo "$COOKIE" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie

# Verify cookie is set correctly
sudo cat /var/lib/rabbitmq/.erlang.cookie
```

### Step 3.3: Start RabbitMQ Cluster

**On VM5 (mq1) - Start primary node:**
```bash
# Start the primary node
sudo systemctl start rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Create Airflow user and vhost
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"

# Verify node is running
sudo rabbitmqctl cluster_status
```

**On VM6 (mq2) - Join cluster:**
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Stop the app (not the service) to join cluster
sudo rabbitmqctl stop_app

# Join the cluster
sudo rabbitmqctl join_cluster rabbit@mq1

# Start the app
sudo rabbitmqctl start_app

# Verify cluster membership
sudo rabbitmqctl cluster_status
```

**On VM7 (mq3) - Join cluster:**
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Stop the app to join cluster
sudo rabbitmqctl stop_app

# Join the cluster
sudo rabbitmqctl join_cluster rabbit@mq1

# Start the app
sudo rabbitmqctl start_app

# Verify cluster membership
sudo rabbitmqctl cluster_status
```

### Step 3.4: Configure High Availability Policies

**On any RabbitMQ node (e.g., VM5):**
```bash
# Set classic queue mirroring policy for high availability
sudo rabbitmqctl set_policy ha-all ".*" '{"ha-mode":"all","ha-sync-mode":"automatic"}' --vhost airflow_host

# Set quorum queue policy for better performance (RabbitMQ 3.8+)
sudo rabbitmqctl set_policy quorum-all ".*" '{"queue-mode":"quorum","queue-leader-locator":"balanced"}' --vhost airflow_host --priority 1

# Verify policies are applied
sudo rabbitmqctl list_policies --vhost airflow_host

# List users and permissions
sudo rabbitmqctl list_users
sudo rabbitmqctl list_permissions -p airflow_host
```

### Step 3.5: Configure RabbitMQ for Production

**On all RabbitMQ nodes (VM5, VM6, VM7):**
```bash
# Create RabbitMQ configuration file for production settings
sudo tee /etc/rabbitmq/rabbitmq.conf << EOF
# Network and clustering configuration
cluster_formation.peer_discovery_backend = classic_config
cluster_formation.classic_config.nodes.1 = rabbit@mq1
cluster_formation.classic_config.nodes.2 = rabbit@mq2
cluster_formation.classic_config.nodes.3 = rabbit@mq3

# Performance settings
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 2GB

# Management interface
management.tcp.port = 15672
management.tcp.ip = 0.0.0.0

# Logging
log.file.level = info
log.connection.level = info

# Security
auth_backends.1 = internal
auth_mechanisms.1 = PLAIN
auth_mechanisms.2 = AMQPLAIN

# Networking
listeners.tcp.default = 5672
num_acceptors.tcp = 10
handshake_timeout = 10000
heartbeat = 580

# Queue settings
default_vhost = /
default_user = guest
default_pass = guest
default_user_tags.administrator = true
default_permissions.configure = .*
default_permissions.read = .*
default_permissions.write = .*
EOF

# Restart RabbitMQ to apply configuration
sudo systemctl restart rabbitmq-server

# Verify service is running
sudo systemctl status rabbitmq-server
```

### Step 3.6: Test RabbitMQ Cluster

**Verify cluster health and connectivity:**
```bash
# Test cluster status from each node
echo "=== RabbitMQ Cluster Status ==="
echo "VM5 (mq1):"
sudo rabbitmqctl cluster_status

echo "VM6 (mq2):"
ssh rocky@192.168.83.136 "sudo rabbitmqctl cluster_status"

echo "VM7 (mq3):"
ssh rocky@192.168.83.137 "sudo rabbitmqctl cluster_status"

# Test management interface connectivity from all nodes
echo "=== Management Interface Test ==="
curl -u airflow_user:airflow_pass http://192.168.83.135:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "mq1 management: SUCCESS"
curl -u airflow_user:airflow_pass http://192.168.83.136:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "mq2 management: SUCCESS"
curl -u airflow_user:airflow_pass http://192.168.83.137:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "mq3 management: SUCCESS"

# Test queue creation and replication
sudo rabbitmqctl declare queue test_ha_queue durable=true --vhost airflow_host
sudo rabbitmqctl list_queues name policy --vhost airflow_host
sudo rabbitmqctl delete_queue test_ha_queue --vhost airflow_host
```

### Step 3.7: Create Connection Monitoring Script

**Create a monitoring script for RabbitMQ health:**
```bash
# On VM1 (for monitoring from Airflow node)
sudo tee /usr/local/bin/check_rabbitmq_cluster.sh << 'EOF'
#!/bin/bash

# RabbitMQ cluster nodes
NODES=("192.168.83.135" "192.168.83.136" "192.168.83.137")
USER="airflow_user"
PASS="airflow_pass"
HEALTHY_NODES=0

echo "=== RabbitMQ Cluster Health Check ==="
echo "$(date): Starting cluster health check"

for node in "${NODES[@]}"; do
    if curl -s -u $USER:$PASS http://$node:15672/api/overview >/dev/null 2>&1; then
        echo "$(date): Node $node is healthy"
        HEALTHY_NODES=$((HEALTHY_NODES + 1))
    else
        echo "$(date): Node $node is DOWN"
    fi
done

echo "$(date): Healthy nodes: $HEALTHY_NODES/3"

if [ $HEALTHY_NODES -ge 2 ]; then
    echo "$(date): Cluster is healthy (quorum maintained)"
    exit 0
else
    echo "$(date): Cluster is unhealthy (quorum lost)"
    exit 1
fi
EOF

sudo chmod +x /usr/local/bin/check_rabbitmq_cluster.sh

# Test the monitoring script
sudo /usr/local/bin/check_rabbitmq_cluster.sh
```

### Step 3.8: Test RabbitMQ Failover

**Test cluster resilience:**
```bash
# Test 1: Stop one node and verify cluster continues
echo "=== Testing Single Node Failure ==="

# Stop VM6 (mq2)
ssh rocky@192.168.83.136 "sudo systemctl stop rabbitmq-server"

# Wait a moment for cluster to detect failure
sleep 10

# Check cluster status from remaining nodes
sudo rabbitmqctl -n rabbit@mq1 cluster_status
ssh rocky@192.168.83.137 "sudo rabbitmqctl -n rabbit@mq3 cluster_status"

# Test connectivity to remaining nodes
curl -u airflow_user:airflow_pass http://192.168.83.135:15672/api/overview | grep -q "cluster_name" && echo "mq1 still accessible"
curl -u airflow_user:airflow_pass http://192.168.83.137:15672/api/overview | grep -q "cluster_name" && echo "mq3 still accessible"

# Restart the stopped node
ssh rocky@192.168.83.136 "sudo systemctl start rabbitmq-server"

# Wait for node to rejoin
sleep 15

# Verify node rejoined the cluster
ssh rocky@192.168.83.136 "sudo rabbitmqctl cluster_status"

echo "Single node failover test completed"
```

### Step 3.9: Configure Airflow Broker URLs

**Create optimized broker connection strings for Airflow:**
```bash
# Create connection configuration for high availability
cat << EOF
=== RabbitMQ Broker URLs for Airflow Configuration ===

Primary Broker URL (for airflow.cfg):
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host;amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host

Alternative with IP addresses:
broker_url = amqp://airflow_user:airflow_pass@192.168.83.135:5672/airflow_host;amqp://airflow_user:airflow_pass@192.168.83.136:5672/airflow_host;amqp://airflow_user:airflow_pass@192.168.83.137:5672/airflow_host

Features:
- Automatic failover between nodes
- Load distribution across cluster
- High availability with queue mirroring
- Management interfaces available on all nodes

Management URLs:
- http://192.168.83.135:15672 (mq1)
- http://192.168.83.136:15672 (mq2)  
- http://192.168.83.137:15672 (mq3)

Credentials: airflow_user / airflow_pass
EOF
```

### Step 3.10: Verification Checklist

**Run comprehensive verification:**
```bash
echo "=== RabbitMQ Cluster HA Verification ==="

# 1. All nodes running
sudo systemctl is-active rabbitmq-server && echo "✅ mq1 running" || echo "❌ mq1 failed"
ssh rocky@192.168.83.136 "sudo systemctl is-active rabbitmq-server" && echo "✅ mq2 running" || echo "❌ mq2 failed"
ssh rocky@192.168.83.137 "sudo systemctl is-active rabbitmq-server" && echo "✅ mq3 running" || echo "❌ mq3 failed"

# 2. Cluster membership
CLUSTER_SIZE=$(sudo rabbitmqctl cluster_status | grep -c "rabbit@mq")
[ "$CLUSTER_SIZE" -eq 3 ] && echo "✅ All 3 nodes in cluster" || echo "❌ Cluster incomplete ($CLUSTER_SIZE/3 nodes)"

# 3. Airflow user and vhost configured
sudo rabbitmqctl list_users | grep -q airflow_user && echo "✅ Airflow user exists" || echo "❌ Airflow user missing"
sudo rabbitmqctl list_vhosts | grep -q airflow_host && echo "✅ Airflow vhost exists" || echo "❌ Airflow vhost missing"

# 4. HA policies configured
POLICIES=$(sudo rabbitmqctl list_policies --vhost airflow_host | wc -l)
[ "$POLICIES" -gt 1 ] && echo "✅ HA policies configured" || echo "❌ HA policies missing"

# 5. Management interface accessible
curl -s -u airflow_user:airflow_pass http://192.168.83.135:15672/api/overview >/dev/null && echo "✅ Management interface accessible" || echo "❌ Management interface failed"

# 6. Run cluster health check
sudo /usr/local/bin/check_rabbitmq_cluster.sh && echo "✅ Cluster health check passed" || echo "❌ Cluster health check failed"

echo ""
echo "RabbitMQ Cluster HA Setup Complete!"
echo "Cluster Nodes: mq1, mq2, mq3"
echo "Virtual Host: airflow_host"
echo "User: airflow_user"
echo "Management: http://192.168.83.135:15672"
echo "Features: Queue mirroring, Automatic failover, Load balancing"
```

This completes the RabbitMQ cluster setup with:

✅ **3-Node Cluster**: mq1, mq2, mq3 with automatic failover  
✅ **High Availability**: Queue mirroring across all nodes  
✅ **Load Balancing**: Automatic distribution of connections  
✅ **Management Interface**: Web UI available on all nodes  
✅ **Production Configuration**: Optimized settings for performance  
✅ **Health Monitoring**: Automated cluster health checks  

The message queue infrastructure now provides zero single points of failure and automatic failover capabilities.
