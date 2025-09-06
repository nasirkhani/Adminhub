# S03-RabbitMQ_Cluster_HA_Setup.md

## High Availability Message Queue Cluster for Celery

### Step 3.1:  Install RabbitMQ (VM6, VM7, VM8)

**Execute on all three RabbitMQ nodes (rabbit-1, rabbit-2, rabbit-3):**
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

**On VM6 (rabbit-1) - Generate and start first node:**
```bash
# Start RabbitMQ to generate the Erlang cookie
sudo systemctl start rabbitmq-server
sudo systemctl stop rabbitmq-server

# Get the generated Erlang cookie
COOKIE=$(sudo cat /var/lib/rabbitmq/.erlang.cookie)
echo "Erlang Cookie for cluster: $COOKIE"

# Save this cookie value - you'll need it for VM7 and VM8
echo "IMPORTANT: Copy this cookie to rabbit-2 and rabbit-3"
```

**On VM7 (rabbit-2) and VM8 (rabbit-3) - Set the same cookie:**
```bash
# Replace COOKIE_VALUE with the actual cookie from VM6 (rabbit-1)
# Example: COOKIE="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
COOKIE="YOUR_COOKIE_FROM_RABBIT_1_HERE"

# Set the same cookie on VM7 and VM8
echo "$COOKIE" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie

# Verify cookie is set correctly
sudo cat /var/lib/rabbitmq/.erlang.cookie
```

**🔧 Cookie Distribution Helper:**
```bash
# Run this on VM6 (rabbit-1) to distribute the cookie automatically
# First get the cookie
COOKIE=$(sudo cat /var/lib/rabbitmq/.erlang.cookie)
echo "Distributing Erlang cookie: $COOKIE"

# Copy to other RabbitMQ nodes using hostnames
for host in rabbit-2 rabbit-3; do
    echo "Setting cookie on $host..."
    ssh rocky@$host "echo '$COOKIE' | sudo tee /var/lib/rabbitmq/.erlang.cookie"
    ssh rocky@$host "sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie"
    ssh rocky@$host "sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie"
    echo "✅ Cookie set on $host"
done

echo "Cookie distribution completed"
```

### Step 3.3: Start RabbitMQ Cluster

**On VM6 (rabbit-1) - Start primary node:**
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

**On VM7 (rabbit-2) - Join cluster:**
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Stop the app (not the service) to join cluster
sudo rabbitmqctl stop_app

# Join the cluster using hostname
sudo rabbitmqctl join_cluster rabbit@rabbit-1

# Start the app
sudo rabbitmqctl start_app

# Verify cluster membership
sudo rabbitmqctl cluster_status
```

**On VM8 (rabbit-3) - Join cluster:**
```bash
# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Stop the app to join cluster
sudo rabbitmqctl stop_app

# Join the cluster using hostname
sudo rabbitmqctl join_cluster rabbit@rabbit-1

# Start the app
sudo rabbitmqctl start_app

# Verify cluster membership
sudo rabbitmqctl cluster_status
```

### Step 3.4: Configure High Availability Policies

**On any RabbitMQ node (e.g., VM6 - rabbit-1):**
```bash
# Set classic queue mirroring policy for high availability
sudo rabbitmqctl set_policy ha-all ".*" '{"ha-mode":"all","ha-sync-mode":"automatic"}' --vhost airflow_host

# Set quorum queue policy for better performance (RabbitMQ 3.8+)
# sudo rabbitmqctl set_policy quorum-all ".*" '{"queue-mode":"quorum","queue-leader-locator":"balanced"}' --vhost airflow_host --priority 1

# Verify policies are applied
sudo rabbitmqctl list_policies --vhost airflow_host

# List users and permissions
sudo rabbitmqctl list_users
sudo rabbitmqctl list_permissions -p airflow_host
```

### Step 3.5: Configure RabbitMQ for Production (this is arbitrary section and did NOT approved and tested before)

**⚠️ IMPORTANT: Replace `<RABBIT_*_IP>` placeholders with your actual RabbitMQ VM IP addresses.**

**On all RabbitMQ nodes (VM6, VM7, VM8):**
```bash
# Create RabbitMQ configuration file for production settings
sudo tee /etc/rabbitmq/rabbitmq.conf << EOF
# Network and clustering configuration
cluster_formation.peer_discovery_backend = classic_config
cluster_formation.classic_config.nodes.1 = rabbit@rabbit-1
cluster_formation.classic_config.nodes.2 = rabbit@rabbit-2
cluster_formation.classic_config.nodes.3 = rabbit@rabbit-3

# Performance settings
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 2GB

# Management interface - REPLACE_WITH_YOUR_IP
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

**Verify cluster health and connectivity using hostnames:**
```bash
# Test cluster status from each node using hostnames
echo "=== RabbitMQ Cluster Status ==="
echo "VM6 (rabbit-1):"
sudo rabbitmqctl cluster_status


# access RabbitMQ web UI at http://<your_vm_ip>:15672 to manage queues.

echo "VM7 (rabbit-2):"
ssh rocky@rabbit-2 "sudo rabbitmqctl cluster_status"

echo "VM8 (rabbit-3):"
ssh rocky@rabbit-3 "sudo rabbitmqctl cluster_status"

# Test management interface connectivity from all nodes using hostnames
echo "=== Management Interface Test ==="
curl -u airflow_user:airflow_pass http://rabbit-1:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "rabbit-1 management: SUCCESS"
curl -u airflow_user:airflow_pass http://rabbit-2:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "rabbit-2 management: SUCCESS"
curl -u airflow_user:airflow_pass http://rabbit-3:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "rabbit-3 management: SUCCESS"

# Test queue creation and replication
sudo rabbitmqctl declare queue test_ha_queue durable=true --vhost airflow_host
sudo rabbitmqctl list_queues name policy --vhost airflow_host
sudo rabbitmqctl delete_queue test_ha_queue --vhost airflow_host
```

**🔧 Alternative Testing with IP Addresses:**
```bash
# If hostname resolution issues, test with IP addresses
# CUSTOMIZE these values with your actual RabbitMQ VM IPs:
RABBIT_1_IP="192.168.1.15"  # Replace with VM6 IP
RABBIT_2_IP="192.168.1.16"  # Replace with VM7 IP
RABBIT_3_IP="192.168.1.17"  # Replace with VM8 IP

echo "=== Management Interface Test (Using IPs) ==="
curl -u airflow_user:airflow_pass http://$RABBIT_1_IP:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "$RABBIT_1_IP management: SUCCESS"
curl -u airflow_user:airflow_pass http://$RABBIT_2_IP:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "$RABBIT_2_IP management: SUCCESS"
curl -u airflow_user:airflow_pass http://$RABBIT_3_IP:15672/api/overview | grep -o '"cluster_name":"[^"]*"' && echo "$RABBIT_3_IP management: SUCCESS"
```

### Step 3.7: Create Connection Monitoring Script

**Create a monitoring script for RabbitMQ health (run on VM1 - haproxy-1):**

**⚠️ IMPORTANT: Replace `<RABBIT_*_IP>` placeholders with your actual RabbitMQ VM IP addresses**

```bash
# On VM1 (haproxy-1) - for monitoring from Airflow node
sudo tee /usr/local/bin/check_rabbitmq_cluster.sh << 'EOF'
#!/bin/bash

# RabbitMQ cluster nodes - REPLACE_WITH_YOUR_IPs
NODES=("<RABBIT_1_IP>" "<RABBIT_2_IP>" "<RABBIT_3_IP>")
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
```

**🔧 Monitoring Script IP Replacement Helper:**
```bash
# Customize and replace IP addresses in monitoring script
# CUSTOMIZE these values with your actual RabbitMQ VM IPs:
RABBIT_1_IP="192.168.1.15"  # Replace with VM6 IP
RABBIT_2_IP="192.168.1.16"  # Replace with VM7 IP
RABBIT_3_IP="192.168.1.17"  # Replace with VM8 IP

# Replace placeholders in monitoring script
sudo sed -i "s/<RABBIT_1_IP>/$RABBIT_1_IP/g" /usr/local/bin/check_rabbitmq_cluster.sh
sudo sed -i "s/<RABBIT_2_IP>/$RABBIT_2_IP/g" /usr/local/bin/check_rabbitmq_cluster.sh
sudo sed -i "s/<RABBIT_3_IP>/$RABBIT_3_IP/g" /usr/local/bin/check_rabbitmq_cluster.sh

echo "Monitoring script updated. Testing:"
sudo /usr/local/bin/check_rabbitmq_cluster.sh
```

### Step 3.8: Test RabbitMQ Failover

**Test cluster resilience:**
```bash
# Test 1: Stop one node and verify cluster continues
echo "=== Testing Single Node Failure ==="

# Stop VM7 (rabbit-2) using hostname
ssh rocky@rabbit-2 "sudo systemctl stop rabbitmq-server"

# Wait a moment for cluster to detect failure
sleep 10

# Check cluster status from remaining nodes
sudo rabbitmqctl -n rabbit@rabbit-1 cluster_status
ssh rocky@rabbit-3 "sudo rabbitmqctl -n rabbit@rabbit-3 cluster_status"

# Test connectivity to remaining nodes using hostnames
curl -u airflow_user:airflow_pass http://rabbit-1:15672/api/overview | grep -q "cluster_name" && echo "rabbit-1 still accessible"
curl -u airflow_user:airflow_pass http://rabbit-3:15672/api/overview | grep -q "cluster_name" && echo "rabbit-3 still accessible"

# Restart the stopped node
ssh rocky@rabbit-2 "sudo systemctl start rabbitmq-server"

# Wait for node to rejoin
sleep 15

# Verify node rejoined the cluster
ssh rocky@rabbit-2 "sudo rabbitmqctl cluster_status"

echo "Single node failover test completed"
```

### Step 3.9: Configure Airflow Broker URLs

**Create optimized broker connection strings for Airflow configuration:**
```bash
# Create connection configuration for high availability
cat << EOF
=== RabbitMQ Broker URLs for Airflow Configuration ===

Primary Broker URL (for airflow.cfg) - Using Hostnames:
broker_url = amqp://airflow_user:airflow_pass@rabbit-1:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-2:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-3:5672/airflow_host

Alternative with IP addresses (REPLACE with your actual IPs):
broker_url = amqp://airflow_user:airflow_pass@<RABBIT_1_IP>:5672/airflow_host;amqp://airflow_user:airflow_pass@<RABBIT_2_IP>:5672/airflow_host;amqp://airflow_user:airflow_pass@<RABBIT_3_IP>:5672/airflow_host

Features:
- Automatic failover between nodes
- Load distribution across cluster
- High availability with queue mirroring
- Management interfaces available on all nodes

Management URLs - Using Hostnames:
- http://rabbit-1:15672 (VM6)
- http://rabbit-2:15672 (VM7)  
- http://rabbit-3:15672 (VM8)

Alternative Management URLs - Using IPs (REPLACE with your actual IPs):
- http://<RABBIT_1_IP>:15672 (VM6)
- http://<RABBIT_2_IP>:15672 (VM7)
- http://<RABBIT_3_IP>:15672 (VM8)

Credentials: airflow_user / airflow_pass
EOF
```

**🔧 Broker URL Generator Script:**
```bash
# Create script to generate proper broker URLs with your IPs
# CUSTOMIZE these values with your actual RabbitMQ VM IPs:
RABBIT_1_IP="192.168.1.15"  # Replace with VM6 IP
RABBIT_2_IP="192.168.1.16"  # Replace with VM7 IP
RABBIT_3_IP="192.168.1.17"  # Replace with VM8 IP

sudo tee /tmp/generate_broker_urls.sh << EOF
#!/bin/bash
RABBIT_1_IP="$RABBIT_1_IP"
RABBIT_2_IP="$RABBIT_2_IP"
RABBIT_3_IP="$RABBIT_3_IP"

echo "=== Generated RabbitMQ Broker URLs ==="
echo ""
echo "Using Hostnames (Preferred):"
echo "broker_url = amqp://airflow_user:airflow_pass@rabbit-1:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-2:5672/airflow_host;amqp://airflow_user:airflow_pass@rabbit-3:5672/airflow_host"
echo ""
echo "Using IP Addresses:"
echo "broker_url = amqp://airflow_user:airflow_pass@\$RABBIT_1_IP:5672/airflow_host;amqp://airflow_user:airflow_pass@\$RABBIT_2_IP:5672/airflow_host;amqp://airflow_user:airflow_pass@\$RABBIT_3_IP:5672/airflow_host"
echo ""
echo "Management Interfaces:"
echo "- http://rabbit-1:15672 or http://\$RABBIT_1_IP:15672"
echo "- http://rabbit-2:15672 or http://\$RABBIT_2_IP:15672"
echo "- http://rabbit-3:15672 or http://\$RABBIT_3_IP:15672"
EOF

chmod +x /tmp/generate_broker_urls.sh
# Run to generate URLs: /tmp/generate_broker_urls.sh
```

### Step 3.10: Verification Checklist

**Run comprehensive verification:**
```bash
echo "=== RabbitMQ Cluster HA Verification ==="

# 1. All nodes running
sudo systemctl is-active rabbitmq-server && echo "✅ rabbit-1 running" || echo "❌ rabbit-1 failed"
ssh rocky@rabbit-2 "sudo systemctl is-active rabbitmq-server" && echo "✅ rabbit-2 running" || echo "❌ rabbit-2 failed"
ssh rocky@rabbit-3 "sudo systemctl is-active rabbitmq-server" && echo "✅ rabbit-3 running" || echo "❌ rabbit-3 failed"

# 2. Cluster membership using hostnames
CLUSTER_SIZE=$(sudo rabbitmqctl cluster_status | grep -c "rabbit@rabbit-")
[ "$CLUSTER_SIZE" -eq 3 ] && echo "✅ All 3 nodes in cluster" || echo "❌ Cluster incomplete ($CLUSTER_SIZE/3 nodes)"

# 3. Airflow user and vhost configured
sudo rabbitmqctl list_users | grep -q airflow_user && echo "✅ Airflow user exists" || echo "❌ Airflow user missing"
sudo rabbitmqctl list_vhosts | grep -q airflow_host && echo "✅ Airflow vhost exists" || echo "❌ Airflow vhost missing"

# 4. HA policies configured
POLICIES=$(sudo rabbitmqctl list_policies --vhost airflow_host | wc -l)
[ "$POLICIES" -gt 1 ] && echo "✅ HA policies configured" || echo "❌ HA policies missing"

# 5. Management interface accessible using hostname
curl -s -u airflow_user:airflow_pass http://rabbit-1:15672/api/overview >/dev/null && echo "✅ Management interface accessible" || echo "❌ Management interface failed"

# 6. Run cluster health check (if monitoring script IPs are configured)
if grep -q "<RABBIT_.*_IP>" /usr/local/bin/check_rabbitmq_cluster.sh; then
    echo "⚠️ Update monitoring script IPs before testing"
else
    sudo /usr/local/bin/check_rabbitmq_cluster.sh && echo "✅ Cluster health check passed" || echo "❌ Cluster health check failed"
fi

echo ""
echo "RabbitMQ Cluster HA Setup Complete!"
echo "Cluster Nodes: rabbit-1, rabbit-2, rabbit-3"
echo "Virtual Host: airflow_host"
echo "User: airflow_user"
echo "Management: http://rabbit-1:15672 (or use IP addresses)"
echo "Features: Queue mirroring, Automatic failover, Load balancing"
```

**🔧 Complete Verification Script:**
```bash
# Create comprehensive verification script
# CUSTOMIZE these values:
RABBIT_1_IP="192.168.1.15"  # Replace with VM6 IP
RABBIT_2_IP="192.168.1.16"  # Replace with VM7 IP
RABBIT_3_IP="192.168.1.17"  # Replace with VM8 IP

sudo tee /usr/local/bin/verify_rabbitmq_cluster.sh << EOF
#!/bin/bash
RABBIT_1_IP="$RABBIT_1_IP"
RABBIT_2_IP="$RABBIT_2_IP"
RABBIT_3_IP="$RABBIT_3_IP"

echo "=== RabbitMQ Cluster Verification ==="
echo "Node IPs: \$RABBIT_1_IP, \$RABBIT_2_IP, \$RABBIT_3_IP"
echo ""

# Test management interfaces
echo "Testing management interfaces:"
for ip in \$RABBIT_1_IP \$RABBIT_2_IP \$RABBIT_3_IP; do
    if curl -s -u airflow_user:airflow_pass http://\$ip:15672/api/overview >/dev/null; then
        echo "✅ Management interface \$ip accessible"
    else
        echo "❌ Management interface \$ip failed"
    fi
done

# Test cluster status
echo ""
echo "Cluster Status:"
sudo rabbitmqctl cluster_status | grep -E "rabbit@rabbit-|Cluster status"

echo ""
echo "Verification completed"
EOF

sudo chmod +x /usr/local/bin/verify_rabbitmq_cluster.sh
# Run after customizing: sudo /usr/local/bin/verify_rabbitmq_cluster.sh
```

This completes the RabbitMQ cluster setup with:

✅ **3-Node Cluster**: rabbit-1, rabbit-2, rabbit-3 with automatic failover  
✅ **High Availability**: Queue mirroring across all nodes  
✅ **Load Balancing**: Automatic distribution of connections  
✅ **Management Interface**: Web UI available on all nodes  
✅ **Production Configuration**: Optimized settings for performance  
✅ **Health Monitoring**: Automated cluster health checks  

The message queue infrastructure now provides zero single points of failure and automatic failover capabilities.

**Next Steps**: Once this RabbitMQ cluster setup is complete and verified, proceed to **S04-NFS_Storage_HA_Setup.md** for shared storage configuration.





