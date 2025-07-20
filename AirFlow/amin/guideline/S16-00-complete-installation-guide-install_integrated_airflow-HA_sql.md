# Complete Apache Airflow 2.9.0 HA Installation Guide
## Rocky Linux 9 with PostgreSQL HA, RabbitMQ HA, and Celery

---

## **🎯 Architecture Overview**

This guide sets up a **10-VM distributed Apache Airflow system** with full High Availability for financial card processing:

### **Infrastructure Layout:**
- **Airflow Core**: 3 VMs (Scheduler, DAG Processor, Worker)
- **PostgreSQL HA**: 3-node Patroni cluster with ETCD
- **RabbitMQ HA**: 3-node cluster 
- **Processing Target**: 1 VM
- **Total**: 10 VMs with enterprise-grade reliability

### **VM Assignment:**
| VM | IP | Hostname | Role | Components |
|----|----|----|------|------------|
| **VM1** | `192.168.83.129` | `airflow` | Master | Scheduler, Webserver, HAProxy |
| **VM2** | `192.168.83.132` | - | Services | DAG Processor, NFS, FTP |
| **VM3** | `192.168.83.133` | - | Target | Card Processing |
| **VM4** | `192.168.83.131` | - | Worker | Celery Worker |
| **VM5** | `192.168.83.134` | `mq1` | MQ Node 1 | RabbitMQ Primary |
| **VM6** | `192.168.83.135` | `mq2` | MQ Node 2 | RabbitMQ Replica |
| **VM7** | `192.168.83.136` | `mq3` | MQ Node 3 | RabbitMQ Replica |
| **sql1** | `192.168.83.148` | `sql1` | DB Node 1 | Patroni, PostgreSQL, ETCD |
| **sql2** | `192.168.83.147` | `sql2` | DB Node 2 | Patroni, PostgreSQL, ETCD |
| **sql3** | `192.168.83.149` | `sql3` | DB Node 3 | Patroni, PostgreSQL, ETCD |

---

## **📋 Prerequisites**

### **System Requirements:**
- **All VMs**: Rocky Linux 9, 2GB+ RAM, 2+ CPU cores
- **Username**: `rocky` on all VMs
- **Password**: `111` on all VMs
- **Network**: All VMs can communicate with each other
- **Firewall**: Disabled or properly configured

### **Preparation on ALL VMs:**
```bash
# Update system packages
sudo dnf update -y
sudo dnf upgrade -y

# Install common dependencies
sudo dnf install -y curl wget vim git python3 python3-pip python3-devel

# Disable firewall (for lab environment)
sudo systemctl disable firewalld.service
sudo systemctl stop firewalld.service

# Disable SELinux (for simplified setup)
sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Reboot to apply changes
sudo reboot
```

---

## **🗄️ PHASE 1: PostgreSQL HA Cluster Setup**

### **Step 1.1: Set Hostnames**

**On sql1:**
```bash
sudo nmcli general hostname sql1
sudo reboot
```

**On sql2:**
```bash
sudo nmcli general hostname sql2
sudo reboot
```

**On sql3:**
```bash
sudo nmcli general hostname sql3
sudo reboot
```

### **Step 1.2: Configure /etc/hosts on sql1, sql2, sql3**

**On ALL PostgreSQL nodes (sql1, sql2, sql3):**
```bash
sudo tee -a /etc/hosts << EOF
192.168.83.129 airflow
192.168.83.148 sql1
192.168.83.147 sql2
192.168.83.149 sql3
192.168.83.134 mq1
192.168.83.135 mq2
192.168.83.136 mq3
EOF
```

### **Step 1.3: Install ETCD on sql1, sql2, sql3**

**On ALL PostgreSQL nodes (sql1, sql2, sql3):**
```bash
# Download ETCD
ETCD_VER=v3.4.34
GOOGLE_URL=https://storage.googleapis.com/etcd
DOWNLOAD_URL=${GOOGLE_URL}

rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1

# Install ETCD binaries
cd /tmp/etcd-download-test/
sudo mv etcd* /usr/local/bin

# Verify installation
etcd --version
etcdctl version

# Create ETCD directories and user
sudo mkdir -p /var/lib/etcd/
sudo mkdir /etc/etcd
sudo groupadd --system etcd
sudo useradd -s /sbin/nologin --system -g etcd etcd
sudo chown -R etcd:etcd /var/lib/etcd/
sudo chmod 0775 /var/lib/etcd/
```

### **Step 1.4: Configure ETCD Services**

**On sql1:**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd key-value store
Documentation=https://github.com/etcd-io/etcd
After=network.target

[Service]
User=etcd
Type=notify
Environment=ETCD_DATA_DIR=/var/lib/etcd
Environment=ETCD_NAME=sql1
Environment=ETCD_LISTEN_PEER_URLS="http://192.168.83.148:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.148:2379, http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://192.168.83.148:2380"
Environment=ETCD_INITIAL_CLUSTER="sql1=http://192.168.83.148:2380,sql2=http://192.168.83.147:2380,sql3=http://192.168.83.149:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://192.168.83.148:2379"
Environment=ETCD_INITIAL_CLUSTER_TOKEN="etcdcluster"
Environment=ETCD_INITIAL_CLUSTER_STATE="new"
ExecStart=/usr/local/bin/etcd --enable-v2=true
Restart=always
RestartSec=10s
LimitNOFILE=40000

[Install]
WantedBy=multi-user.target
EOF
```

**On sql2:**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd key-value store
Documentation=https://github.com/etcd-io/etcd
After=network.target

[Service]
User=etcd
Type=notify
Environment=ETCD_DATA_DIR=/var/lib/etcd
Environment=ETCD_NAME=sql2
Environment=ETCD_LISTEN_PEER_URLS="http://192.168.83.147:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.147:2379, http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://192.168.83.147:2380"
Environment=ETCD_INITIAL_CLUSTER="sql1=http://192.168.83.148:2380,sql2=http://192.168.83.147:2380,sql3=http://192.168.83.149:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://192.168.83.147:2379"
Environment=ETCD_INITIAL_CLUSTER_TOKEN="etcdcluster"
Environment=ETCD_INITIAL_CLUSTER_STATE="new"
ExecStart=/usr/local/bin/etcd --enable-v2=true
Restart=always
RestartSec=10s
LimitNOFILE=40000

[Install]
WantedBy=multi-user.target
EOF
```

**On sql3:**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd key-value store
Documentation=https://github.com/etcd-io/etcd
After=network.target

[Service]
User=etcd
Type=notify
Environment=ETCD_DATA_DIR=/var/lib/etcd
Environment=ETCD_NAME=sql3
Environment=ETCD_LISTEN_PEER_URLS="http://192.168.83.149:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.149:2379, http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://192.168.83.149:2380"
Environment=ETCD_INITIAL_CLUSTER="sql1=http://192.168.83.148:2380,sql2=http://192.168.83.147:2380,sql3=http://192.168.83.149:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://192.168.83.149:2379"
Environment=ETCD_INITIAL_CLUSTER_TOKEN="etcdcluster"
Environment=ETCD_INITIAL_CLUSTER_STATE="new"
ExecStart=/usr/local/bin/etcd --enable-v2=true
Restart=always
RestartSec=10s
LimitNOFILE=40000

[Install]
WantedBy=multi-user.target
EOF
```

### **Step 1.5: Install PostgreSQL 16 on sql1, sql2, sql3**

**On ALL PostgreSQL nodes (sql1, sql2, sql3):**
```bash
# Install PostgreSQL 16
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql16-server postgresql16-contrib

# Create symbolic link for Patroni
sudo ln -s /usr/pgsql-16/bin /usr/sbin
```

### **Step 1.6: Install Patroni on sql1, sql2, sql3**

**On ALL PostgreSQL nodes (sql1, sql2, sql3):**
```bash
# Install Patroni
curl https://bootstrap.pypa.io/pip/3.6/get-pip.py -o /tmp/get-pip.py -k
python3 /tmp/get-pip.py
pip install psycopg2-binary
pip install patroni[etcd,consul]
```

### **Step 1.7: Configure Patroni**

**On sql1:**
```bash
# Create Patroni directories
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf

# Generate SSL certificates
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Organization/OU=IT/CN=sql1"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*

# Create Patroni configuration
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: sql1
restapi:
  listen: 192.168.83.148:8008
  connect_address: 192.168.83.148:8008
etcd:
  hosts: 192.168.83.148:2379,192.168.83.147:2379,192.168.83.149:2379
bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    maximum_lag_on_syncnode: 15000000
    synchronous_mode: false
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        shared_buffers: 512MB
        work_mem: 8MB
        maintenance_work_mem: 256MB
        max_worker_processes: 8
        wal_buffers: 16MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 1GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 200
        ssl: true
        ssl_cert_file: /usr/patroni/conf/server.crt
        ssl_key_file: /usr/patroni/conf/server.key
  initdb:
    - encoding: UTF8
    - data-checksums
  pg_hba:
    - host replication replicator 127.0.0.1/32 md5
    - host replication replicator 192.168.83.148/32 md5
    - host replication replicator 192.168.83.147/32 md5
    - host replication replicator 192.168.83.149/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: 192.168.83.148:5432
  connect_address: 192.168.83.148:5432
  data_dir: /var/lib/pgsql/16/data
  bin_dir: /usr/pgsql-16/bin
  pgpass: /tmp/pgpass
  authentication:
    replication:
      username: replicator
      password: replicator
    superuser:
      username: postgres
      password: postgres
    rewind:
      username: pgrewind
      password: pgrewind
tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: true
EOF
```

**On sql2 (Replace sql1 with sql2 and update IP to 192.168.83.147):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Organization/OU=IT/CN=sql2"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*

# Create Patroni configuration (similar to sql1 but with sql2 name and 192.168.83.147 IP)
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: sql2
restapi:
  listen: 192.168.83.147:8008
  connect_address: 192.168.83.147:8008
etcd:
  hosts: 192.168.83.148:2379,192.168.83.147:2379,192.168.83.149:2379
bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    maximum_lag_on_syncnode: 15000000
    synchronous_mode: false
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        shared_buffers: 512MB
        work_mem: 8MB
        maintenance_work_mem: 256MB
        max_worker_processes: 8
        wal_buffers: 16MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 1GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 200
        ssl: true
        ssl_cert_file: /usr/patroni/conf/server.crt
        ssl_key_file: /usr/patroni/conf/server.key
  initdb:
    - encoding: UTF8
    - data-checksums
  pg_hba:
    - host replication replicator 127.0.0.1/32 md5
    - host replication replicator 192.168.83.148/32 md5
    - host replication replicator 192.168.83.147/32 md5
    - host replication replicator 192.168.83.149/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: 192.168.83.147:5432
  connect_address: 192.168.83.147:5432
  data_dir: /var/lib/pgsql/16/data
  bin_dir: /usr/pgsql-16/bin
  pgpass: /tmp/pgpass
  authentication:
    replication:
      username: replicator
      password: replicator
    superuser:
      username: postgres
      password: postgres
    rewind:
      username: pgrewind
      password: pgrewind
tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: true
EOF
```

**On sql3 (Replace sql1 with sql3 and update IP to 192.168.83.149):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Organization/OU=IT/CN=sql3"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*

# Create Patroni configuration (similar to sql1 but with sql3 name and 192.168.83.149 IP)
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: sql3
restapi:
  listen: 192.168.83.149:8008
  connect_address: 192.168.83.149:8008
etcd:
  hosts: 192.168.83.148:2379,192.168.83.147:2379,192.168.83.149:2379
bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    maximum_lag_on_syncnode: 15000000
    synchronous_mode: false
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        shared_buffers: 512MB
        work_mem: 8MB
        maintenance_work_mem: 256MB
        max_worker_processes: 8
        wal_buffers: 16MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 1GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 200
        ssl: true
        ssl_cert_file: /usr/patroni/conf/server.crt
        ssl_key_file: /usr/patroni/conf/server.key
  initdb:
    - encoding: UTF8
    - data-checksums
  pg_hba:
    - host replication replicator 127.0.0.1/32 md5
    - host replication replicator 192.168.83.148/32 md5
    - host replication replicator 192.168.83.147/32 md5
    - host replication replicator 192.168.83.149/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: 192.168.83.149:5432
  connect_address: 192.168.83.149:5432
  data_dir: /var/lib/pgsql/16/data
  bin_dir: /usr/pgsql-16/bin
  pgpass: /tmp/pgpass
  authentication:
    replication:
      username: replicator
      password: replicator
    superuser:
      username: postgres
      password: postgres
    rewind:
      username: pgrewind
      password: pgrewind
tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: true
EOF
```

### **Step 1.8: Create Patroni Service**

**On ALL PostgreSQL nodes (sql1, sql2, sql3):**
```bash
sudo tee /usr/lib/systemd/system/patroni.service << EOF
[Unit]
Description=patroni
Documentation=https://patroni.readthedocs.io/en/latest/index.html
After=syslog.target network.target etcd.target
Wants=network-online.target

[Service]
Type=simple
User=postgres
Group=postgres
PermissionsStartOnly=true
ExecStart=/usr/local/bin/patroni /usr/patroni/conf/patroni.yml
ExecReload=/bin/kill -HUP \$MAINPID
LimitNOFILE=65536
KillMode=process
KillSignal=SIGINT
Restart=on-abnormal
RestartSec=30s
TimeoutSec=0

[Install]
WantedBy=multi-user.target
EOF
```

### **Step 1.9: Start PostgreSQL HA Services**

**On ALL PostgreSQL nodes (sql1, sql2, sql3) - Start in order:**

**First, start ETCD on all nodes:**
```bash
sudo systemctl daemon-reload
sudo systemctl start etcd
sudo systemctl enable etcd
sudo systemctl status etcd
```

**Then, start Patroni (start sql1 first, then sql2, then sql3):**
```bash
sudo systemctl start patroni
sudo systemctl enable patroni
sudo systemctl status patroni
```

**Verify cluster status (from any PostgreSQL node):**
```bash
patronictl -c /usr/patroni/conf/patroni.yml list
```

---

## **🐰 PHASE 2: RabbitMQ HA Cluster Setup**

### **Step 2.1: Set Hostnames**

**On VM5:**
```bash
sudo nmcli general hostname mq1
sudo reboot
```

**On VM6:**
```bash
sudo nmcli general hostname mq2
sudo reboot
```

**On VM7:**
```bash
sudo nmcli general hostname mq3
sudo reboot
```

### **Step 2.2: Install RabbitMQ on VM5, VM6, VM7**

**On ALL RabbitMQ nodes (VM5, VM6, VM7):**
```bash
# Install Erlang
sudo dnf install -y erlang

# Install RabbitMQ
sudo dnf install -y rabbitmq-server

# Start and enable RabbitMQ
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl status rabbitmq-server
```

### **Step 2.3: Configure RabbitMQ Cluster**

**On mq1 (VM5) - Primary node:**
```bash
# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Create Airflow user
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator

# Create virtual host
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"

# Get Erlang cookie for cluster
sudo cat /var/lib/rabbitmq/.erlang.cookie
```

**On mq2 (VM6) and mq3 (VM7) - Join cluster:**
```bash
# Stop RabbitMQ
sudo systemctl stop rabbitmq-server

# Copy Erlang cookie from mq1
sudo echo "ERLANG_COOKIE_FROM_MQ1" > /var/lib/rabbitmq/.erlang.cookie
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 600 /var/lib/rabbitmq/.erlang.cookie

# Start RabbitMQ
sudo systemctl start rabbitmq-server

# Join cluster
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management
```

**Verify cluster status (on any RabbitMQ node):**
```bash
sudo rabbitmqctl cluster_status
```

---

## **🔧 PHASE 3: HAProxy Setup on VM1**

### **Step 3.1: Install HAProxy on VM1**

**On VM1:**
```bash
# Set hostname
sudo nmcli general hostname airflow
sudo reboot

# Install HAProxy
sudo dnf install -y haproxy

# Configure HAProxy for PostgreSQL load balancing
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

listen stats
    mode http
    bind *:7000
    stats enable
    stats uri /

listen postgres
    bind *:5000
    option httpchk
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 2000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 2000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 2000 check port 8008

listen postgres-readonly
    bind *:6000
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 2000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 2000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 2000 check port 8008
EOF

# Start HAProxy
sudo systemctl start haproxy
sudo systemctl enable haproxy
sudo systemctl status haproxy
```

---

## **🚀 PHASE 4: Airflow Installation and Configuration**

### **Step 4.1: Install Python and Dependencies on VM1, VM2, VM4**

**On VM1, VM2, VM4:**
```bash
# Install Python 3.8+
sudo dnf install -y python3 python3-pip python3-devel
python3 --version
pip3 --version

# Install system dependencies
sudo dnf install -y gcc gcc-c++ make postgresql-devel
```

### **Step 4.2: Install Airflow on VM1, VM2, VM4**

**On VM1, VM2, VM4:**
```bash
# Install Airflow with required extras
pip3 install "apache-airflow[celery,postgres,crypto]==2.9.0"
pip3 install "celery==5.5.0" "flower==1.2.0"

# Initialize Airflow directory
export AIRFLOW_HOME=/home/rocky/airflow
mkdir -p $AIRFLOW_HOME
```

### **Step 4.3: Create Airflow Database and User**

**On VM1 (Connect to HA cluster):**
```bash
# Create database and user on HA cluster
export PGPASSWORD=postgres
psql -h 192.168.83.129 -U postgres -p 5000 -c "
CREATE DATABASE airflow_db 
    WITH OWNER postgres 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8';"

psql -h 192.168.83.129 -U postgres -p 5000 -c "
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER USER airflow_user CREATEDB;"

# Grant schema permissions
psql -h 192.168.83.129 -U postgres -p 5000 -d airflow_db -c "
GRANT ALL ON SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow_user;"
```

### **Step 4.4: Configure Airflow on ALL Airflow nodes**

**On VM1, VM2, VM4 - Create airflow.cfg:**
```bash
# Generate default configuration
airflow config list --defaults > /home/rocky/airflow/airflow.cfg

# Edit configuration (replace with manual editing)
tee /home/rocky/airflow/airflow.cfg << EOF
[core]
dags_folder = /home/rocky/airflow/dags
hostname_callable = airflow.utils.net.get_host_ip_address
default_timezone = Asia/Tehran
executor = CeleryExecutor
parallelism = 32
max_active_tasks_per_dag = 16
dags_are_paused_at_creation = True
max_active_runs_per_dag = 16
load_examples = False
plugins_folder = /home/rocky/airflow/plugins
execute_tasks_new_python_interpreter = False
fernet_key = 
donot_pickle = False
dagbag_import_timeout = 30.0
dagbag_import_error_tracebacks = True
dagbag_import_error_traceback_depth = 2
dag_file_processor_timeout = 50
task_runner = StandardTaskRunner
default_impersonation = 
security = 
unit_test_mode = False
enable_xcom_pickling = False
killed_task_cleanup_time = 60
dag_run_conf_overrides_params = True
dag_discovery_safe_mode = True
default_task_retries = 0
min_serialized_dag_update_interval = 30
min_serialized_dag_fetch_interval = 10
max_db_retries = 3
store_serialized_dags = True
store_dag_code = True
check_slas = True
xcom_backend = airflow.models.xcom.BaseXCom

[database]
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db
sql_alchemy_pool_size = 10
sql_alchemy_max_overflow = 20
sql_alchemy_pool_pre_ping = True
sql_alchemy_pool_recycle = 3600
sql_alchemy_pool_enabled = True
sql_alchemy_reconnect_timeout = 300
sql_alchemy_schema = 
load_default_connections = True

[logging]
base_log_folder = /home/rocky/airflow/logs
remote_logging = False
remote_log_conn_id = 
remote_base_log_folder = 
encrypt_s3_logs = False
logging_level = INFO
fab_logging_level = WARN
logging_config_class = 
colored_console_log = True
colored_log_format = [%%(blue)s%%(asctime)s%%(reset)s] {{%%(blue)s%%(filename)s:%%(reset)s%%(lineno)d}} %%(log_color)s%%(levelname)s%%(reset)s - %%(log_color)s%%(message)s%%(reset)s
colored_formatter_class = airflow.utils.log.colored_log.CustomTTYColoredFormatter
log_format = [%%(asctime)s] {{%%(filename)s:%%(lineno)d}} %%(levelname)s - %%(message)s
simple_log_format = %%(asctime)s %%(levelname)s - %%(message)s
task_log_prefix_template = 
log_filename_template = {{ ti.dag_id }}/{{ ti.task_id }}/{{ ts }}/{{ try_number }}.log
log_processor_filename_template = {{ filename }}.log
dag_processor_manager_log_location = /home/rocky/airflow/logs/dag_processor_manager/dag_processor_manager.log
task_log_reader = task

[metrics]
statsd_on = False
statsd_host = localhost
statsd_port = 8125
statsd_prefix = airflow
statsd_allow_list = 
statsd_block_list = 
statsd_disabled_tags = 

[secrets]
backend = 
backend_kwargs = 

[cli]
api_client = airflow.api.client.json_client
endpoint_url = http://localhost:8080

[api]
enable_experimental_api = False
auth_backends = airflow.api.auth.backend.deny_all
google_key_path = 
google_scopes = https://www.googleapis.com/auth/cloud-platform
google_audience = 
maximum_page_limit = 100
fallback_page_limit = 100
default_page_offset = 0
default_page_limit = 100

[lineage]
backend = 

[atlas]
sasl_enabled = False
host = 
port = 21000
username = 
password = 

[operators]
default_owner = airflow
default_cpus = 1
default_ram = 512
default_disk = 512
default_gpus = 0
allow_illegal_arguments = False

[hive]
default_hive_mapred_queue = 

[webserver]
base_url = http://localhost:8080
default_ui_timezone = Asia/Tehran
web_server_host = 0.0.0.0
web_server_port = 8080
web_server_ssl_cert = 
web_server_ssl_key = 
web_server_master_timeout = 120
web_server_worker_timeout = 120
worker_refresh_batch_size = 1
worker_refresh_interval = 6000
reload_on_plugin_change = False
secret_key = temporary_key
workers = 4
worker_class = sync
access_logfile = -
error_logfile = -
access_logformat = 
expose_config = False
expose_hostname = True
expose_stacktrace = True
dag_default_view = tree
dag_orientation = LR
log_fetch_timeout_sec = 5
log_fetch_delay_sec = 2
log_auto_tailing_offset = 30
log_animation_speed = 1000
hide_paused_dags_by_default = False
page_size = 100
navbar_color = #fff
default_dag_run_display_number = 25
enable_proxy_fix = False
proxy_fix_x_for = 1
proxy_fix_x_proto = 1
proxy_fix_x_host = 1
proxy_fix_x_port = 1
proxy_fix_x_prefix = 1
cookie_secure = False
cookie_samesite = Lax
default_wrap = False
x_frame_enabled = True
show_recent_stats_for_completed_runs = True
update_fab_perms = True
session_lifetime_minutes = 43200
instance_name = Airflow
instance_name_has_markup = False
auto_refresh_interval = 3
warn_deployment_exposure = True

[email]
email_backend = airflow.utils.email.send_email_smtp
email_conn_id = smtp_default
default_email_on_retry = True
default_email_on_failure = True
subject_template = /home/rocky/airflow/config_templates/email_subject_template.txt
html_content_template = /home/rocky/airflow/config_templates/email_template.html

[smtp]
smtp_host = localhost
smtp_starttls = True
smtp_ssl = False
smtp_user = 
smtp_password = 
smtp_port = 587
smtp_mail_from = 
smtp_timeout = 30
smtp_retry_limit = 5

[sentry]
sentry_dsn = 

[celery]
celery_app_name = airflow.executors.celery_executor
worker_concurrency = 16
worker_log_server_port = 8793
broker_url = amqp://airflow_user:airflow_pass@192.168.83.134:5672,192.168.83.135:5672,192.168.83.136:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db
flower_host = 0.0.0.0
flower_url_prefix = 
flower_port = 5555
flower_basic_auth = 
default_queue = default
celery_config_options = airflow.config_templates.default_celery.DEFAULT_CELERY_CONFIG
ssl_active = False
ssl_key = 
ssl_cert = 
ssl_cacert = 
pool = prefork
operation_timeout = 1.0
task_track_started = True
worker_precheck = False

[celery_kubernetes_executor]
kubernetes_queue = kubernetes

[kubernetes_executor]
namespace = default
airflow_configmap = 
airflow_local_settings_configmap = 
worker_container_repository = 
worker_container_tag = 
worker_container_image_pull_policy = IfNotPresent
worker_service_account_name = 
image_pull_secrets = 
gcp_service_account_keys = 
in_cluster = True
cluster_context = 
config_file = 
worker_pods_creation_batch_size = 1
multi_namespace_mode = False
delete_worker_pods = True
delete_worker_pods_on_failure = False
worker_pods_pending_timeout = 300
worker_pods_pending_timeout_batch_size = 100
worker_pods_pending_timeout_check_interval = 120

[kubernetes]
pod_template_file = 
namespace = default
delete_option_kwargs = 
worker_container_repository = 
worker_container_tag = 
worker_container_image_pull_policy = IfNotPresent
worker_service_account_name = 
image_pull_secrets = 
gcp_service_account_keys = 
in_cluster = True
cluster_context = 
config_file = 
dags_in_image = False
logs_volume_subpath = 
logs_volume_claim = 
logs_volume_host = 
dags_volume_subpath = 
dags_volume_claim = 
dags_volume_host = 
volume_mounts = 
worker_pods_creation_batch_size = 1
multi_namespace_mode = False
run_as_user = 50000
fs_group = 0

[scheduler]
job_heartbeat_sec = 5
scheduler_heartbeat_sec = 5
run_duration = -1
min_file_process_interval = 0
dag_dir_list_interval = 300
print_stats_interval = 30
pool_metrics_interval = 5.0
scheduler_health_check_threshold = 30
orphaned_tasks_check_interval = 300.0
child_process_log_directory = /home/rocky/airflow/logs/scheduler
scheduler_zombie_task_threshold = 300
catchup_by_default = True
max_tis_per_query = 512
use_row_level_locking = True
max_dagruns_to_create_per_loop = 10
max_dagruns_per_loop_to_schedule = 20
schedule_after_task_execution = True
parsing_processes = 2
file_parsing_sort_mode = modified_time
use_job_schedule = True
allow_trigger_in_future = False
dependency_detector = airflow.serialization.serialized_objects.DependencyDetector
standalone_dag_processor = False
max_callbacks_per_loop = 20
dag_stale_not_seen_duration = 600
parsing_cleanup_interval = 60
task_queued_timeout = 600.0
task_queued_timeout_check_interval = 120.0

[triggerer]
default_capacity = 1000
job_heartbeat_sec = 30
trigger_log_retention_days = 30

[kerberos]
ccache = /tmp/airflow_krb5_ccache
principal = airflow
reinit_frequency = 3600
kinit_path = kinit
keytab = airflow.keytab

[github_enterprise]
api_rev = v3

[admin]
hide_sensitive_variable_fields = True

[elasticsearch]
host = 
log_id_template = {dag_id}-{task_id}-{execution_date}-{try_number}
end_of_log_mark = end_of_log
frontend = 
write_stdout = False
json_format = False
json_fields = asctime, filename, lineno, levelname, message

[elasticsearch_configs]
use_ssl = False
verify_certs = True

[smartsensor]
use_smart_sensor = False
shard_code_upper_limit = 10000
shards = 5
sensors_enabled = NamedHivePartitionSensor

[local_kubernetes_executor]
kubernetes_queue = kubernetes

[docker]
docker_url = unix://var/run/docker.sock
tls_ca = 
tls_cert = 
tls_key = 
tls_assert_hostname = 
tls_verify = False
api_version = auto
stop_timeout = 10

[ssh]
ssh_conn_id = ssh_default

[sftp]
private_key_pass_phrase = 

[segment]
write_key = 
on = False

[ldap]
uri = 
user_filter = objectClass=*
user_name_attr = uid
group_member_attr = memberOf
superuser_filter = 
data_profiler_filter = 
bind_user = 
bind_password = 
basedn = 
cacert = /etc/ca/ldap_ca.crt
search_scope = LEVEL
ignore_malformed_schema = False

[mesos]
master = localhost:5050
framework_name = Airflow
task_cpu = 1
task_memory = 256
checkpoint = False
failover_timeout = 604800
authenticate = False
default_principal = admin
default_secret = admin

[sensors]
default_timeout = 604800
default_poke_interval = 60
default_mode = poke
instance_name_template = 

[smart_sensor]
use_smart_sensor = False
shard_code_upper_limit = 10000
shards = 5
sensors_enabled = NamedHivePartitionSensor
EOF
```

### **Step 4.5: Initialize Airflow Database**

**On VM1:**
```bash
# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username airflow_user \
    --firstname Airflow \
    --lastname User \
    --role Admin \
    --email airflow@airflow.com \
    --password airflow_pass
```

### **Step 4.6: Create Systemd Services**

**On VM1 - Scheduler and Webserver:**
```bash
# Scheduler service
sudo tee /etc/systemd/system/airflow-scheduler.service << EOF
[Unit]
Description=Apache Airflow Scheduler
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
EOF

# Webserver service
sudo tee /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Apache Airflow Webserver
After=airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
EOF

# Flower service
sudo tee /etc/systemd/system/airflow-flower.service << EOF
[Unit]
Description=Apache Airflow Flower
After=airflow-scheduler.service
Requires=airflow-scheduler.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-flower
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
EOF
```

**On VM2 - DAG Processor:**
```bash
# DAG Processor service
sudo tee /etc/systemd/system/airflow-dag-processor.service << EOF
[Unit]
Description=Apache Airflow DAG Processor
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow dag-processor
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-dag-processor
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
EOF
```

**On VM4 - Celery Worker:**
```bash
# Celery Worker service
sudo tee /etc/systemd/system/airflow-celery-worker.service << EOF
[Unit]
Description=Apache Airflow Celery Worker
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery worker
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-celery-worker
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
EOF
```

### **Step 4.7: Setup NFS on VM2**

**On VM2:**
```bash
# Install NFS server
sudo dnf install -y nfs-utils

# Create shared directory
sudo mkdir -p /home/rocky/airflow/dags
sudo chown rocky:rocky /home/rocky/airflow/dags

# Configure NFS exports
sudo tee /etc/exports << EOF
/home/rocky/airflow/dags 192.168.83.129(rw,sync,no_root_squash)
/home/rocky/airflow/dags 192.168.83.131(rw,sync,no_root_squash)
EOF

# Start NFS services
sudo systemctl enable nfs-server
sudo systemctl start nfs-server
sudo exportfs -a
```

**On VM1 and VM4 - Mount NFS:**
```bash
# Install NFS client
sudo dnf install -y nfs-utils

# Create mount point
sudo mkdir -p /home/rocky/airflow/dags

# Mount NFS share
sudo mount -t nfs 192.168.83.132:/home/rocky/airflow/dags /home/rocky/airflow/dags

# Add to fstab for permanent mount
echo "192.168.83.132:/home/rocky/airflow/dags /home/rocky/airflow/dags nfs defaults 0 0" | sudo tee -a /etc/fstab
```

---

## **🎯 PHASE 5: Start All Services**

### **Step 5.1: Start Services in Order**

**1. Verify PostgreSQL HA cluster:**
```bash
# From any PostgreSQL node
patronictl -c /usr/patroni/conf/patroni.yml list
```

**2. Verify RabbitMQ cluster:**
```bash
# From any RabbitMQ node
sudo rabbitmqctl cluster_status
```

**3. Start Airflow services:**

**On VM1:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler airflow-webserver airflow-flower
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver
sudo systemctl start airflow-flower
```

**On VM2:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
sudo systemctl start airflow-dag-processor
```

**On VM4:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-celery-worker
sudo systemctl start airflow-celery-worker
```

---

## **✅ PHASE 6: Verification and Testing**

### **Step 6.1: Health Checks**

```bash
# Check PostgreSQL HA cluster
patronictl -c /usr/patroni/conf/patroni.yml list

# Check RabbitMQ cluster
sudo rabbitmqctl cluster_status

# Check HAProxy stats
curl http://192.168.83.129:7000/stats

# Check Airflow database connection
airflow db check

# Check Airflow services
sudo systemctl status airflow-scheduler airflow-webserver airflow-flower
sudo systemctl status airflow-dag-processor  # On VM2
sudo systemctl status airflow-celery-worker  # On VM4
```

### **Step 6.2: Web UI Access**

- **Airflow Web UI**: `http://192.168.83.129:8080`
- **Flower (Celery Monitor)**: `http://192.168.83.129:5555`
- **HAProxy Stats**: `http://192.168.83.129:7000`
- **RabbitMQ Management**: `http://192.168.83.134:15672` (or VM6/VM7)

### **Step 6.3: Test DAG Execution**

```bash
# Create a test DAG on VM2
tee /home/rocky/airflow/dags/test_dag.py << EOF
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'test_ha_setup',
    default_args=default_args,
    description='Test HA setup',
    schedule_interval=None,
    catchup=False,
)

test_task = BashOperator(
    task_id='test_task',
    bash_command='echo "HA Airflow cluster is working!"',
    dag=dag,
)
EOF

# Trigger test DAG
airflow dags unpause test_ha_setup
airflow dags trigger test_ha_setup
```

---

## **🔧 Post-Installation Configuration**

### **Optional: Setup FTP Server on VM2**
```bash
# Install and configure FTP server
sudo dnf install -y vsftpd
sudo systemctl enable vsftpd
sudo systemctl start vsftpd
```

### **Optional: Setup SSH Keys for VM connections**
```bash
# Generate SSH key on VM1, VM2, VM4
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy public key to target VMs for automation
ssh-copy-id rocky@192.168.83.133  # VM3
```

---

## **🎯 Final Architecture Status**

### **✅ Fully HA Components:**
- **PostgreSQL**: 3-node Patroni cluster with automatic failover
- **RabbitMQ**: 3-node cluster with message distribution
- **Load Balancing**: HAProxy for database connections

### **✅ Distributed Airflow:**
- **VM1**: Scheduler + Webserver + HAProxy
- **VM2**: DAG Processor + NFS + FTP (optional)
- **VM4**: Celery Worker
- **VM3**: Processing target

### **🔍 Monitoring Commands:**
```bash
# PostgreSQL cluster status
patronictl -c /usr/patroni/conf/patroni.yml list

# RabbitMQ cluster status  
sudo rabbitmqctl cluster_status

# Airflow health
airflow db check
systemctl status airflow-*

# Database connections
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT client_addr, application_name, state, COUNT(*) 
FROM pg_stat_activity 
WHERE datname = 'airflow_db' 
GROUP BY client_addr, application_name, state;"
```

---

## **🚨 Troubleshooting**

### **Common Issues:**

1. **Services not starting**: Check logs with `journalctl -u service-name -f`
2. **Database connection issues**: Verify HAProxy and Patroni status
3. **DAGs not showing**: Check NFS mount and DAG processor logs
4. **Celery tasks failing**: Verify RabbitMQ cluster and worker status

### **Log Locations:**
- **Airflow logs**: `/home/rocky/airflow/logs/`
- **System logs**: `journalctl -u service-name`
- **PostgreSQL logs**: Check Patroni logs
- **RabbitMQ logs**: `/var/log/rabbitmq/`

---

**🎉 Congratulations! You now have a fully distributed, High Availability Apache Airflow system ready for financial card processing workloads.**
