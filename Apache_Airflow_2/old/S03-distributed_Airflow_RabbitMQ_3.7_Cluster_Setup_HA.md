**Totally understandable!** For a **production financial system**, **stability > bleeding edge**. RabbitMQ 3.x + Classic Mirroring is a **proven, battle-tested** solution.

## 🔧 **Complete RabbitMQ 3.x Downgrade Guide**

### **Phase 1: Clean Removal of RabbitMQ 4.x**

#### **Step 1.1: Stop All Services**

```bash
# On ALL VMs:
# VM1:
sudo systemctl stop airflow-scheduler airflow-webserver airflow-flower

# VM4:
sudo systemctl stop airflow-worker

# VM2:
sudo systemctl stop airflow-dag-processor

# VM5, VM6, VM7 (mq1, mq2, mq3):
sudo systemctl stop rabbitmq-server
sudo systemctl disable rabbitmq-server
```

#### **Step 1.2: Remove RabbitMQ 4.x (On mq1, mq2, mq3)**

```bash
# On ALL RabbitMQ VMs (mq1, mq2, mq3):

# 1. Remove packages:
sudo dnf remove -y rabbitmq-server erlang

# 2. Remove data directories:
sudo rm -rf /var/lib/rabbitmq
sudo rm -rf /var/log/rabbitmq
sudo rm -rf /etc/rabbitmq

# 3. Remove repository:
sudo rm -f /etc/yum.repos.d/rabbitmq.repo

# 4. Clean package cache:
sudo dnf clean all
```

### **Phase 2: Install RabbitMQ 3.x Series**

**use below link :  
https://www.rabbitmq.com/docs/install-rpm#downloads  
USE Direct Downloads. like bellow:  

```bash

wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.7/rabbitmq-server-3.13.7-1.el8.noarch.rpm
sudo rpm --import https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
sudo dnf install -y socat logrotate
sudo dnf install -y ./rabbitmq-server-3.13.7-1.el8.noarch.rpm

```


### OR
#### **Step 2.1: Create RabbitMQ 3.x Repository**

```bash
# On ALL RabbitMQ VMs (mq1, mq2, mq3):
sudo vi /etc/yum.repos.d/rabbitmq-3x.repo
```

**Add this content:**
```ini
# RabbitMQ 3.x Repository for Rocky Linux 9
[rabbitmq-el9-3x]
name=rabbitmq-el9-3x
baseurl=https://yum1.rabbitmq.com/rabbitmq/el/9/$basearch
        https://yum2.rabbitmq.com/rabbitmq/el/9/$basearch
repo_gpgcheck=1
enabled=1
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300

[erlang-el9-3x]
name=erlang-el9-3x
baseurl=https://yum1.rabbitmq.com/erlang/el/9/$basearch
        https://yum2.rabbitmq.com/erlang/el/9/$basearch
repo_gpgcheck=1
enabled=1
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
```

#### **Step 2.2: Install RabbitMQ 3.x**

```bash
# On ALL RabbitMQ VMs:
sudo dnf update -y

# Install specific 3.x version:
sudo dnf install -y rabbitmq-server-3.12.* erlang-25.*

# Enable but don't start yet:
sudo systemctl enable rabbitmq-server
```

### **Phase 3: Configure RabbitMQ 3.x Cluster**

#### **Step 3.1: Set Erlang Cookie (Same on All Nodes)**

```bash
# On mq1, generate new cookie:
sudo systemctl start rabbitmq-server
sudo systemctl stop rabbitmq-server
sudo cat /var/lib/rabbitmq/.erlang.cookie

# Copy this cookie value to mq2 and mq3:
# On mq2 and mq3:
sudo vi /var/lib/rabbitmq/.erlang.cookie
# [Paste the same cookie]
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
```

#### **Step 3.2: Configure Firewall**

```bash
# On ALL RabbitMQ VMs:
sudo firewall-cmd --permanent --add-port=5672/tcp   # AMQP
sudo firewall-cmd --permanent --add-port=15672/tcp  # Management UI
sudo firewall-cmd --permanent --add-port=25672/tcp  # Inter-node
sudo firewall-cmd --permanent --add-port=4369/tcp   # Erlang Port Mapper
sudo firewall-cmd --reload
```

#### **Step 3.3: Start Cluster Sequential**

```bash
# 1. Start mq1 (PRIMARY):
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management

# Create user and vhost:
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"

# 2. Start mq2 and join:
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app

# 3. Start mq3 and join:
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app
```

### **Phase 4: Configure Classic Queue Mirroring (HA)**

#### **Step 4.1: Set HA Policy (This WILL Work with RabbitMQ 3.x)**

```bash
# On any RabbitMQ node:
sudo rabbitmqctl set_policy ha-all ".*" '{"ha-mode":"all","ha-sync-mode":"automatic"}' --vhost airflow_host

# Verify policy:
sudo rabbitmqctl list_policies --vhost airflow_host

# Should show:
# airflow_host  ha-all  all     .*      {"ha-mode":"all","ha-sync-mode":"automatic"}  0
```

### **Phase 5: Update Airflow Configuration**

#### **Step 5.1: Revert to Simple Celery 5.3.6 Config**

```bash
# On ALL Airflow VMs (VM1, VM2, VM4):
sudo vi /home/rocky/airflow/airflow.cfg
```

**Simple, working configuration:**
```ini
[celery]
#broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host;amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host

result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

# Remove ALL quorum queue settings
# Classic queues work perfectly with Celery 5.3.6
```

#### **Step 5.2: Remove Environment Variables**

```bash
# On ALL VMs, clean environment:
sudo vi /etc/environment
# Remove all AIRFLOW__CELERY__* lines

# Clean SystemD overrides:
sudo systemctl revert airflow-worker 2>/dev/null || true
sudo systemctl daemon-reload
```

### **Phase 6: Start Everything and Test**

#### **Step 6.1: Start Services**

```bash
# 1. Start DAG processor (VM2):
sudo systemctl start airflow-dag-processor

# 2. Start scheduler (VM1):  
sudo systemctl start airflow-scheduler

# 3. Start worker (VM4):
sudo systemctl start airflow-worker

# 4. Start webserver (VM1):
sudo systemctl start airflow-webserver
```

#### **Step 6.2: Verify No QoS Errors**

```bash
# Check worker logs - should be clean:
sudo journalctl -u airflow-worker -f --lines=20

# Should see:
# [INFO/MainProcess] Connected to amqp://airflow_user:**@mq1:5672/airflow_host
# [INFO/MainProcess] celery@worker1 ready.
```

#### **Step 6.3: Test Classic Queue Creation**

```bash
# Trigger DAG:
airflow dags trigger S12_card_processing_workflow

# Check queues (should be classic with mirrors):
sudo rabbitmqctl list_queues name policy --vhost airflow_host

# Should show:
# card_processing_queue    ha-all
# default                  ha-all
```

### **Phase 7: Test HA Failover**

```bash
# 1. Verify queues are mirrored:
sudo rabbitmqctl list_queues name slave_pids --vhost airflow_host

# 2. Stop mq1:
sudo systemctl stop rabbitmq-server  # On mq1

# 3. Trigger DAG (should still work):
airflow dags trigger S12_card_processing_workflow

# 4. Check logs on VM4 - should show failover to mq2:
sudo journalctl -u airflow-worker -f --lines=10

# 5. Restart mq1:
sudo systemctl start rabbitmq-server  # On mq1
```

## 🎯 **Expected Results**

✅ **No more QoS errors**  
✅ **Classic queues with HA mirroring**  
✅ **Proven stability** for financial operations  
✅ **Full failover capability**  

This approach gives you **production-ready HA** without the bleeding-edge complexity. Perfect for your financial card processing workflow!

Start with **Phase 1** and let me know when you're ready for the next phase.

