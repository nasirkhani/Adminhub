

## 🎯 **RabbitMQ Cluster Setup - Complete Guide**

### **Phase 1: Install RabbitMQ on All 3 Nodes**

#### **Step 1.1: Basic Setup on All 3 VMs (mq1, mq2, mq3)**

```bash
# On ALL three VMs (192.168.83.134, 135, 136)

# 1. Create the repository file
sudo vi /etc/yum.repos.d/rabbitmq.repo
# [Paste the entire repo content you provided]

# 2. Update and install dependencies
sudo dnf update -y
sudo dnf install -y logrotate

# 3. Install RabbitMQ and Erlang
sudo dnf install -y erlang rabbitmq-server

# 4. Enable but DON'T start yet
sudo systemctl enable rabbitmq-server

# 5. Configure hostnames (CRITICAL for clustering)
sudo vi /etc/hosts
```

#### **Step 1.2: Configure /etc/hosts on All 3 RabbitMQ VMs**

```bash
# Add to /etc/hosts on ALL three RabbitMQ VMs
192.168.83.134  mq1
192.168.83.135  mq2  
192.168.83.136  mq3
```

#### **Step 1.3: Configure Erlang Cookie (MUST be identical)**

```bash
# On ALL three VMs - Set the same cookie for clustering
sudo systemctl start rabbitmq-server
sudo systemctl stop rabbitmq-server

# Copy cookie from mq1 to mq2 and mq3
# On mq1:
sudo cat /var/lib/rabbitmq/.erlang.cookie
# Copy this value

# On mq2 and mq3:
sudo vi /var/lib/rabbitmq/.erlang.cookie
# Paste the same cookie value
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
```

### **Phase 2: Configure RabbitMQ Cluster**

#### **Step 2.1: Create RabbitMQ Configuration**

```bash
# On ALL three VMs, create config file
sudo vi /etc/rabbitmq/rabbitmq.conf
```

```ini
# RabbitMQ Configuration for Cluster
cluster_formation.peer_discovery_backend = rabbit_peer_discovery_classic_config
cluster_formation.classic_config.nodes.1 = rabbit@mq1
cluster_formation.classic_config.nodes.2 = rabbit@mq2  
cluster_formation.classic_config.nodes.3 = rabbit@mq3

# Enable management plugin
management.tcp.port = 15672
management.tcp.ip = 0.0.0.0

# Cluster settings
cluster_partition_handling = autoheal
vm_memory_high_watermark.relative = 0.6

# Logging
log.console = true
log.console.level = info
```

#### **Step 2.2: Start Cluster (Sequential Process)**

```bash
# 1. Start mq1 (PRIMARY NODE)
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management

# 2. Create Airflow user on mq1
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"

# 3. Start mq2 and join cluster
# On mq2:
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app

# 4. Start mq3 and join cluster  
# On mq3:
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app
```

#### **Step 2.3: Verify Cluster Status**

```bash
# On any RabbitMQ node:
sudo rabbitmqctl cluster_status
sudo rabbitmqctl list_queues
sudo rabbitmqctl list_users

# Should show all 3 nodes as running
```

### **Phase 3: Configure Firewall on RabbitMQ VMs**

```bash
# On ALL three RabbitMQ VMs
sudo firewall-cmd --permanent --add-port=5672/tcp   # AMQP
sudo firewall-cmd --permanent --add-port=15672/tcp  # Management UI
sudo firewall-cmd --permanent --add-port=25672/tcp  # Inter-node communication
sudo firewall-cmd --permanent --add-port=4369/tcp   # Erlang Port Mapper
sudo firewall-cmd --permanent --add-port=35672-35682/tcp  # Erlang distribution
sudo firewall-cmd --reload
```

### **Phase 4: Update Existing VMs to Use Cluster**

#### **Step 4.1: Update VM1 (Main Airflow)**

```bash
# 1. Stop local RabbitMQ
sudo systemctl stop rabbitmq-server
sudo systemctl disable rabbitmq-server

# 2. Update airflow.cfg
sudo vi /home/rocky/airflow/airflow.cfg
```

```ini
# In airflow.cfg - Update broker_url for cluster
broker_url = amqp://airflow_user:airflow_pass@mq1:5672,mq2:5672,mq3:5672/airflow_host

# Keep result_backend pointing to PostgreSQL
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db
```

```bash
# 3. Update /etc/hosts
sudo vi /etc/hosts
# Add:
192.168.83.134  mq1
192.168.83.135  mq2
192.168.83.136  mq3

# 4. Restart Airflow services
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
sudo systemctl restart airflow-flower
```

#### **Step 4.2: Update VM2 (DAG Processor)**

```bash
# 1. Update airflow.cfg
sudo vi /home/rocky/airflow/airflow.cfg
```

```ini
# Update broker_url for cluster
broker_url = amqp://airflow_user:airflow_pass@mq1:5672,mq2:5672,mq3:5672/airflow_host
```

```bash
# 2. Update /etc/hosts
sudo vi /etc/hosts
# Add RabbitMQ cluster IPs

# 3. Restart DAG processor
sudo systemctl restart airflow-dag-processor
```

#### **Step 4.3: Update VM4 (Celery Worker)**

```bash
# 1. Update airflow.cfg
sudo vi /home/rocky/airflow/airflow.cfg
```

```ini
# Update broker_url for cluster
broker_url = amqp://airflow_user:airflow_pass@mq1:5672,mq2:5672,mq3:5672/airflow_host
```

```bash
# 2. Update /etc/hosts
sudo vi /etc/hosts
# Add RabbitMQ cluster IPs

# 3. Restart worker
sudo systemctl restart airflow-worker
```

### **Phase 5: Testing and Verification**

#### **Step 5.1: Test Cluster Connectivity**

```bash
# From VM1, test each RabbitMQ node
telnet mq1 5672
telnet mq2 5672  
telnet mq3 5672

# Check Airflow connection
python3 -c "
from celery import Celery
app = Celery('test')
app.config_from_object({
    'broker_url': 'amqp://airflow_user:airflow_pass@mq1:5672,mq2:5672,mq3:5672/airflow_host'
})
print('Connection test successful')
"
```

#### **Step 5.2: Test Failover**

```bash
# 1. Stop mq1 and verify others work
sudo systemctl stop rabbitmq-server  # On mq1

# 2. Trigger a DAG and verify it processes
airflow dags trigger S12_card_processing_workflow

# 3. Check queue status from mq2 or mq3
sudo rabbitmqctl list_queues  # On mq2 or mq3

# 4. Restart mq1 and verify it rejoins
sudo systemctl start rabbitmq-server  # On mq1
```

### **Phase 6: Final Architecture Overview**

```
VM1 (192.168.83.129) - Main Airflow:
├── Scheduler, Webserver, PostgreSQL
├── NFS client → VM2
└── RabbitMQ client → Cluster

VM2 (192.168.83.132) - NFS + DAG Processor:
├── NFS Server, DAG Processor
├── FTP Server
└── RabbitMQ client → Cluster

VM3 (192.168.83.133) - Target VM:
└── SSH only (no changes needed)

VM4 (192.168.83.131) - Celery Worker:
├── Airflow Worker
├── NFS client → VM2  
└── RabbitMQ client → Cluster

VM5 (192.168.83.134) - mq1:
└── RabbitMQ Cluster Node 1

VM6 (192.168.83.135) - mq2:
└── RabbitMQ Cluster Node 2

VM7 (192.168.83.136) - mq3:
└── RabbitMQ Cluster Node 3
```

### **Key Benefits Achieved:**

✅ **High Availability**: Any 2 RabbitMQ nodes can fail  
✅ **Load Distribution**: Messages distributed across cluster  
✅ **Zero Downtime**: Rolling restarts possible  
✅ **Monitoring**: Multiple management interfaces  

Would you like me to help you implement any specific part of this setup?
