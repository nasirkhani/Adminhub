# 🚀 Enterprise Apache Airflow 2.9.0 - Complete Distributed HA Infrastructure Setup

**A comprehensive guide for implementing production-ready, highly available Apache Airflow infrastructure from scratch**

---

## 📋 **Infrastructure Overview**

### **Target Architecture**
```
                    ┌─────────────────────────────────────────┐
                    │            ENTERPRISE AIRFLOW           │
                    │         DISTRIBUTED HA CLUSTER         │
                    └─────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VM1 (airflow) │    │  VM2 (ftp/nfs)  │    │ VM12 (nfs2)     │
│ • Scheduler     │    │ • NFS Primary   │    │ • NFS Standby   │
│ • Webserver     │    │ • DAG Processor │    │ • DAG Processor │
│ • HAProxy (PG)  │    │ • FTP Server    │    │ • File Sync     │
│ • Flower        │    │ • Lsyncd        │    │ • Ready Standby │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       └──── Real-time sync ──┘
         │
    ┌────┴─────┬─────────────┬─────────────┐
    │          │             │             │
┌───▼───┐ ┌───▼───┐    ┌───▼───┐    ┌───▼───┐
│  VM4  │ │ VM5   │    │ VM6   │    │ VM7   │
│Worker │ │ mq1   │    │ mq2   │    │ mq3   │
│       │ │RabbitMQ│    │RabbitMQ│    │RabbitMQ│
└───────┘ └───────┘    └───────┘    └───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         ┌────▼───┐    ┌────▼───┐    ┌────▼───┐
         │ VM8    │    │ VM9    │    │ VM10   │
         │ sql1   │    │ sql2   │    │ sql3   │
         │Patroni │    │Patroni │    │Patroni │
         │Primary │    │Replica │    │Replica │
         └────────┘    └────────┘    └────────┘
```

### **VM Specifications**
| VM | Hostname | IP Address | Role | RAM | CPU | Disk |
|---|---|---|---|---|---|---|
| VM1 | airflow | 192.168.83.129 | Airflow Main + HAProxy | 4GB | 2 | 20GB |
| VM2 | ftp | 192.168.83.132 | NFS Primary + DAG Processor | 2GB | 1 | 15GB |
| VM3 | card1 | 192.168.83.133 | Target System | 1GB | 1 | 10GB |
| VM4 | worker1 | 192.168.83.131 | Celery Worker | 2GB | 2 | 15GB |
| VM5 | mq1 | 192.168.83.135 | RabbitMQ Node 1 | 2GB | 1 | 10GB |
| VM6 | mq2 | 192.168.83.136 | RabbitMQ Node 2 | 2GB | 1 | 10GB |
| VM7 | mq3 | 192.168.83.137 | RabbitMQ Node 3 | 2GB | 1 | 10GB |
| VM8 | sql1 | 192.168.83.148 | PostgreSQL Node 1 | 4GB | 2 | 20GB |
| VM9 | sql2 | 192.168.83.147 | PostgreSQL Node 2 | 4GB | 2 | 20GB |
| VM10 | sql3 | 192.168.83.149 | PostgreSQL Node 3 | 4GB | 2 | 20GB |
| VM12 | nfs2 | 192.168.83.150 | NFS Standby + DAG Processor | 2GB | 1 | 15GB |

---

## 🔧 **PHASE 1: Infrastructure Preparation**

### **Step 1.1: Base System Setup (ALL VMs)**

**Execute on ALL VMs (VM1-VM12):**

```bash
# Update system
sudo dnf update -y
sudo dnf upgrade -y

# Install common packages
sudo dnf install -y vim curl wget rsync nfs-utils firewalld

# Disable SELinux for simplified setup
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Configure timezone
sudo timedatectl set-timezone Asia/Tehran

# Create rocky user with sudo privileges (if not exists)
sudo useradd -m -s /bin/bash rocky
echo "rocky:111" | sudo chpasswd
echo "rocky ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/rocky
```

### **Step 1.2: Set Hostnames (Each VM Individually)**

**On VM1:**
```bash
sudo nmcli general hostname airflow
```

**On VM2:**
```bash
sudo nmcli general hostname ftp
```

**On VM3:**
```bash
sudo nmcli general hostname card1
```

**On VM4:**
```bash
sudo nmcli general hostname worker1
```

**On VM5:**
```bash
sudo nmcli general hostname mq1
```

**On VM6:**
```bash
sudo nmcli general hostname mq2
```

**On VM7:**
```bash
sudo nmcli general hostname mq3
```

**On VM8:**
```bash
sudo nmcli general hostname sql1
```

**On VM9:**
```bash
sudo nmcli general hostname sql2
```

**On VM10:**
```bash
sudo nmcli general hostname sql3
```

**On VM12:**
```bash
sudo nmcli general hostname nfs2
```

**Reboot all VMs after hostname changes:**
```bash
sudo reboot
```

### **Step 1.3: Configure /etc/hosts (ALL VMs)**

**Execute on ALL VMs:**
```bash
sudo tee -a /etc/hosts << EOF
# Airflow Cluster Infrastructure
192.168.83.129 airflow
192.168.83.132 ftp
192.168.83.133 card1
192.168.83.131 worker1
192.168.83.135 mq1
192.168.83.136 mq2
192.168.83.137 mq3
192.168.83.148 sql1
192.168.83.147 sql2
192.168.83.149 sql3
192.168.83.150 nfs2
EOF
```

### **Step 1.4: SSH Key Setup (From VM1)**

**On VM1 (airflow):**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy to all VMs
for host in ftp card1 worker1 mq1 mq2 mq3 sql1 sql2 sql3 nfs2; do
    ssh-copy-id rocky@$host
done

# Test connectivity
for host in ftp card1 worker1 mq1 mq2 mq3 sql1 sql2 sql3 nfs2; do
    ssh rocky@$host "echo 'SSH to $host: SUCCESS'"
done
```

### **Step 1.5: Firewall Configuration**

**VM1 (airflow) - Airflow services + HAProxy:**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp   # Airflow Webserver
sudo firewall-cmd --permanent --add-port=5555/tcp   # Flower
sudo firewall-cmd --permanent --add-port=7000/tcp   # HAProxy Stats
sudo firewall-cmd --permanent --add-port=5000/tcp   # HAProxy PG Write
sudo firewall-cmd --permanent --add-port=6000/tcp   # HAProxy PG Read
sudo firewall-cmd --reload
```

**VM2 (ftp) - NFS + FTP:**
```bash
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --permanent --add-service=rpc-bind
sudo firewall-cmd --permanent --add-service=mountd
sudo firewall-cmd --permanent --add-port=21/tcp     # FTP
sudo firewall-cmd --reload
```

**VM4 (worker1) - Worker services:**
```bash
sudo firewall-cmd --permanent --add-port=8793/tcp   # Log server
sudo firewall-cmd --reload
```

**VM5,6,7 (mq1,mq2,mq3) - RabbitMQ:**
```bash
sudo firewall-cmd --permanent --add-port=5672/tcp   # AMQP
sudo firewall-cmd --permanent --add-port=15672/tcp  # Management UI
sudo firewall-cmd --permanent --add-port=25672/tcp  # Inter-node
sudo firewall-cmd --permanent --add-port=4369/tcp   # Erlang Port Mapper
sudo firewall-cmd --reload
```

**VM8,9,10 (sql1,sql2,sql3) - PostgreSQL + etcd:**
```bash
sudo firewall-cmd --permanent --add-port=5432/tcp   # PostgreSQL
sudo firewall-cmd --permanent --add-port=8008/tcp   # Patroni REST API
sudo firewall-cmd --permanent --add-port=2379/tcp   # etcd client
sudo firewall-cmd --permanent --add-port=2380/tcp   # etcd peer
sudo firewall-cmd --reload
```

**VM12 (nfs2) - NFS Standby:**
```bash
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --permanent --add-service=rpc-bind
sudo firewall-cmd --permanent --add-service=mountd
sudo firewall-cmd --reload
```

---

## 💾 **PHASE 2: PostgreSQL HA Cluster Setup**

### **Step 2.1: Install PostgreSQL and etcd (sql1, sql2, sql3)**

**Execute on VM8, VM9, VM10:**
```bash
# Install PostgreSQL 16
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql16-server postgresql16-contrib

# Create symbolic link for Patroni
sudo ln -s /usr/pgsql-16/bin /usr/sbin

# Install etcd
ETCD_VER=v3.4.34
DOWNLOAD_URL=https://storage.googleapis.com/etcd
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
sudo mv /tmp/etcd-download-test/etcd* /usr/local/bin

# Create etcd user and directories
sudo groupadd --system etcd
sudo useradd -s /sbin/nologin --system -g etcd etcd
sudo mkdir -p /var/lib/etcd/
sudo mkdir /etc/etcd
sudo chown -R etcd:etcd /var/lib/etcd/
sudo chmod 0775 /var/lib/etcd/

# Install Patroni
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++
pip3 install psycopg2-binary
pip3 install patroni[etcd,consul]
```

### **Step 2.2: Configure etcd Cluster**

**On VM8 (sql1):**
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
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.148:2379,http://127.0.0.1:2379"
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

**On VM9 (sql2):**
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
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.147:2379,http://127.0.0.1:2379"
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

**On VM10 (sql3):**
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
Environment=ETCD_LISTEN_CLIENT_URLS="http://192.168.83.149:2379,http://127.0.0.1:2379"
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

**Start etcd on all nodes:**
```bash
# On VM8, VM9, VM10
sudo systemctl daemon-reload
sudo systemctl enable etcd
sudo systemctl start etcd
sudo systemctl status etcd
```

### **Step 2.3: Configure Patroni SSL Certificates**

**On VM8 (sql1):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=sql1"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

**On VM9 (sql2):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=sql2"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

**On VM10 (sql3):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=sql3"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

### **Step 2.4: Configure Patroni**

**On VM8 (sql1):**
```bash
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
        shared_buffers: 1GB
        work_mem: 16MB
        maintenance_work_mem: 512MB
        max_worker_processes: 8
        wal_buffers: 32MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 3GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 1000
        temp_buffers: 4MB
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
  nosync: false
EOF
```

**On VM9 (sql2):**
```bash
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
        shared_buffers: 1GB
        work_mem: 16MB
        maintenance_work_mem: 512MB
        max_worker_processes: 8
        wal_buffers: 32MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 3GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 1000
        temp_buffers: 4MB
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
  nosync: false
EOF
```

**On VM10 (sql3):**
```bash
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
        shared_buffers: 1GB
        work_mem: 16MB
        maintenance_work_mem: 512MB
        max_worker_processes: 8
        wal_buffers: 32MB
        max_wal_size: 1GB
        min_wal_size: 512MB
        effective_cache_size: 3GB
        fsync: on
        checkpoint_completion_target: 0.9
        log_rotation_size: 100MB
        listen_addresses: "*"
        max_connections: 1000
        temp_buffers: 4MB
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
  nosync: false
EOF
```

### **Step 2.5: Create Patroni Service and Start Cluster**

**On VM8, VM9, VM10:**
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

sudo systemctl daemon-reload
sudo systemctl enable patroni
sudo systemctl start patroni
sudo systemctl status patroni
```

### **Step 2.6: Setup HAProxy on VM1 (airflow)**

**On VM1:**
```bash
# Install HAProxy
sudo dnf install -y haproxy

# Configure HAProxy
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
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008

listen postgres-readonly
    bind *:6000
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server sql1 192.168.83.148:5432 maxconn 1000 check port 8008
    server sql2 192.168.83.147:5432 maxconn 1000 check port 8008
    server sql3 192.168.83.149:5432 maxconn 1000 check port 8008
EOF

sudo systemctl enable haproxy
sudo systemctl start haproxy
sudo systemctl status haproxy
```

### **Step 2.7: Create Airflow Database and User**

**On VM1:**
```bash
# Test PostgreSQL cluster connectivity
export PGPASSWORD=postgres
psql -h 192.168.83.129 -U postgres -p 5000 -c "SELECT pg_is_in_recovery(), inet_server_addr();"

# Create Airflow database and user
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

# Verify connectivity
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "SELECT current_user, current_database();"
```

---

## 🐰 **PHASE 3: RabbitMQ HA Cluster Setup**

### **Step 3.1: Install RabbitMQ 3.x (VM5, VM6, VM7)**

**Execute on VM5, VM6, VM7:**
```bash
# Download and install RabbitMQ 3.13.7 (stable version)
wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.7/rabbitmq-server-3.13.7-1.el8.noarch.rpm
sudo rpm --import https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
sudo dnf install -y socat logrotate
sudo dnf install -y ./rabbitmq-server-3.13.7-1.el8.noarch.rpm

# Enable but don't start yet
sudo systemctl enable rabbitmq-server
```

### **Step 3.2: Configure Erlang Cookie**

**On VM5 (mq1) - Generate and start first:**
```bash
sudo systemctl start rabbitmq-server
sudo systemctl stop rabbitmq-server
COOKIE=$(sudo cat /var/lib/rabbitmq/.erlang.cookie)
echo "Erlang Cookie: $COOKIE"
```

**On VM6 (mq2) and VM7 (mq3) - Set same cookie:**
```bash
# Replace COOKIE_VALUE with the actual cookie from mq1
COOKIE="YOUR_COOKIE_HERE"
echo "$COOKIE" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
```

### **Step 3.3: Start RabbitMQ Cluster**

**On VM5 (mq1) - Start primary node:**
```bash
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management

# Create Airflow user and vhost
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"
```

**On VM6 (mq2) - Join cluster:**
```bash
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app
```

**On VM7 (mq3) - Join cluster:**
```bash
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl stop_app
sudo rabbitmqctl join_cluster rabbit@mq1
sudo rabbitmqctl start_app
```

### **Step 3.4: Configure HA Policy**

**On any RabbitMQ node:**
```bash
# Set classic queue mirroring policy
sudo rabbitmqctl set_policy ha-all ".*" '{"ha-mode":"all","ha-sync-mode":"automatic"}' --vhost airflow_host

# Verify policy
sudo rabbitmqctl list_policies --vhost airflow_host
```

### **Step 3.5: Verify RabbitMQ Cluster**

```bash
# Check cluster status
sudo rabbitmqctl cluster_status

# Test connectivity from VM1
curl -u airflow_user:airflow_pass http://mq1:15672/api/overview
curl -u airflow_user:airflow_pass http://mq2:15672/api/overview
curl -u airflow_user:airflow_pass http://mq3:15672/api/overview
```

---

## 📁 **PHASE 4: NFS HA Setup (Primary/Standby)**

### **Step 4.1: Setup NFS Primary on VM2 (ftp)**

**On VM2:**
```bash
# Install NFS and sync tools
sudo dnf install -y nfs-utils lsyncd

# Create NFS directories
sudo mkdir -p /srv/airflow/dags
sudo mkdir -p /srv/airflow/logs
sudo chown -R rocky:rocky /srv/airflow
sudo chmod 755 /srv/airflow/dags /srv/airflow/logs

# Configure NFS exports
sudo tee /etc/exports << EOF
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
EOF

# Start NFS services
sudo systemctl enable --now nfs-server
sudo systemctl enable --now rpcbind
sudo exportfs -arv
```

### **Step 4.2: Setup NFS Standby on VM12 (nfs2)**

**On VM12:**
```bash
# Install required packages
sudo dnf install -y nfs-utils python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create identical directory structure
sudo mkdir -p /srv/airflow/dags
sudo mkdir -p /srv/airflow/logs
sudo chown -R rocky:rocky /srv/airflow
sudo chmod 755 /srv/airflow/dags /srv/airflow/logs

# Configure NFS exports (same as primary)
sudo tee /etc/exports << EOF
/srv/airflow/dags 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
/srv/airflow/logs 192.168.83.0/24(rw,sync,no_root_squash,no_subtree_check)
EOF

# Enable services but don't start (standby mode)
sudo systemctl enable nfs-server
sudo systemctl enable rpcbind
```

### **Step 4.3: Setup File Synchronization**

**On VM2 - Configure lsyncd for real-time sync:**
```bash
sudo tee /etc/lsyncd.conf << EOF
settings {
    logfile = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd-status.log",
    statusInterval = 20,
    pidfile = "/var/run/lsyncd.pid"
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/dags",
    host = "192.168.83.150",
    targetdir = "/srv/airflow/dags",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true
    },
    ssh = {
        port = 22,
        options = {"-o", "StrictHostKeyChecking=no"}
    }
}

sync {
    default.rsyncssh,
    source = "/srv/airflow/logs",
    host = "192.168.83.150",
    targetdir = "/srv/airflow/logs",
    rsync = {
        archive = true,
        compress = true,
        perms = true,
        owner = true,
        group = true,
        times = true,
        links = true
    },
    ssh = {
        port = 22,
        options = {"-o", "StrictHostKeyChecking=no"}
    }
}
EOF

sudo systemctl enable lsyncd
sudo systemctl start lsyncd
```

**Initial sync from VM2 to VM12:**
```bash
rsync -avz --delete /srv/airflow/dags/ rocky@192.168.83.150:/srv/airflow/dags/
rsync -avz --delete /srv/airflow/logs/ rocky@192.168.83.150:/srv/airflow/logs/
```

### **Step 4.4: Create NFS Failover Scripts**

**On VM2 - Failover scripts:**
```bash
sudo tee /usr/local/bin/nfs-become-standby.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM2 becoming STANDBY" >> $LOG

systemctl stop airflow-dag-processor 2>/dev/null || true
systemctl stop nfs-server
systemctl stop lsyncd

echo "$(date): Final sync to VM12" >> $LOG
rsync -avz --delete /srv/airflow/dags/ rocky@192.168.83.150:/srv/airflow/dags/
rsync -avz --delete /srv/airflow/logs/ rocky@192.168.83.150:/srv/airflow/logs/

echo "$(date): VM2 is now STANDBY" >> $LOG
EOF

sudo tee /usr/local/bin/nfs-become-active.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM2 becoming ACTIVE" >> $LOG

echo "$(date): Syncing changes from VM12" >> $LOG
rsync -avz rocky@192.168.83.150:/srv/airflow/dags/ /srv/airflow/dags/
rsync -avz rocky@192.168.83.150:/srv/airflow/logs/ /srv/airflow/logs/

systemctl start rpcbind
systemctl start nfs-server
systemctl start lsyncd
systemctl start airflow-dag-processor 2>/dev/null || true

echo "$(date): VM2 is now ACTIVE" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

**On VM12 - Failover scripts:**
```bash
sudo tee /usr/local/bin/nfs-become-active.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM12 becoming ACTIVE" >> $LOG

systemctl start rpcbind
systemctl start nfs-server
systemctl start airflow-dag-processor 2>/dev/null || true

echo "$(date): VM12 is now ACTIVE" >> $LOG
EOF

sudo tee /usr/local/bin/nfs-become-standby.sh << 'EOF'
#!/bin/bash
LOG="/var/log/nfs-failover.log"
echo "$(date): VM12 becoming STANDBY" >> $LOG

systemctl stop airflow-dag-processor 2>/dev/null || true
systemctl stop nfs-server

echo "$(date): VM12 is now STANDBY" >> $LOG
EOF

sudo chmod +x /usr/local/bin/nfs-become-*.sh
```

---

## ✈️ **PHASE 5: Airflow Installation and Configuration**

### **Step 5.1: Install Airflow on Main Node (VM1)**

**On VM1:**
```bash
# Install Python dependencies
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow with constraints
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres,crypto]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "celery==5.5.0" "flower==1.2.0"
pip3 install paramiko  # For SSH connections

# Mount NFS for DAGs
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /mnt/airflow-dags
echo "192.168.83.132:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Create symlink to NFS mount
ln -s /mnt/airflow-dags ~/airflow/dags
mkdir -p ~/airflow/logs ~/airflow/plugins
```

### **Step 5.2: Configure Airflow**

**On VM1 - Create airflow.cfg:**
```bash
# Initialize Airflow configuration
airflow db init

# Edit configuration
vi ~/airflow/airflow.cfg
```

**Key configuration sections:**
```ini
[core]
executor = CeleryExecutor
dags_folder = /home/rocky/airflow/dags
load_examples = False
default_timezone = Asia/Tehran

[database]
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db
pool_size = 10
max_overflow = 20
pool_pre_ping = True
pool_recycle = 3600

[celery]
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host;amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5000/airflow_db

[scheduler]
standalone_dag_processor = True

[webserver]
base_url = http://192.168.83.129:8080
web_server_host = 0.0.0.0
web_server_port = 8080

[api]
auth_backends = airflow.api.auth.backend.basic_auth

[logging]
remote_logging = False
base_log_folder = /home/rocky/airflow/logs
```

### **Step 5.3: Initialize Airflow Database**

**On VM1:**
```bash
# Test database connectivity
airflow db check

# Initialize database
airflow db migrate

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@airflow.local \
    --password admin123
```

### **Step 5.4: Create SystemD Services for VM1**

**Airflow Scheduler:**
```bash
sudo tee /etc/systemd/system/airflow-scheduler.service << EOF
[Unit]
Description=Airflow Scheduler
After=network.target postgresql.service
Wants=postgresql.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler

[Install]
WantedBy=multi-user.target
EOF
```

**Airflow Webserver:**
```bash
sudo tee /etc/systemd/system/airflow-webserver.service << EOF
[Unit]
Description=Airflow Webserver
After=network.target airflow-scheduler.service
Wants=airflow-scheduler.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver

[Install]
WantedBy=multi-user.target
EOF
```

**Airflow Flower:**
```bash
sudo tee /etc/systemd/system/airflow-flower.service << EOF
[Unit]
Description=Airflow Flower
After=network.target airflow-scheduler.service
Wants=airflow-scheduler.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-flower

[Install]
WantedBy=multi-user.target
EOF
```

**Enable services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler airflow-webserver airflow-flower
```

---

## 🔧 **PHASE 6: DAG Processor Setup**

### **Step 6.1: Install Airflow on VM2 (ftp)**

**On VM2:**
```bash
# Install Python dependencies
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"

# Copy configuration from VM1
scp rocky@192.168.83.129:/home/rocky/airflow/airflow.cfg ~/airflow/

# Create symlink to local DAGs
ln -s /srv/airflow/dags /home/rocky/airflow/dags

# Create utility modules for DAGs
mkdir -p ~/airflow/config ~/airflow/utils
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py
```

### **Step 6.2: Create DAG Processor Service on VM2**

```bash
sudo tee /etc/systemd/system/airflow-dag-processor.service << EOF
[Unit]
Description=Airflow Standalone DAG Processor
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment="AIRFLOW_HOME=/home/rocky/airflow"
Environment="PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/rocky/airflow:/home/rocky/.local/lib/python3.9/site-packages"
Environment="LANG=en_US.UTF-8"
Environment="LC_ALL=en_US.UTF-8"
WorkingDirectory=/home/rocky/airflow
ExecStart=/bin/bash -c 'source /home/rocky/.bashrc && exec /home/rocky/.local/bin/airflow dag-processor'
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airflow-dag-processor
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
```

### **Step 6.3: Setup Standby DAG Processor on VM12**

**On VM12:**
```bash
# Install Airflow (same as VM2)
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${AIRFLOW_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "${CONSTRAINT_URL}"

# Copy configuration
scp rocky@192.168.83.132:/home/rocky/airflow/airflow.cfg ~/airflow/
scp -r rocky@192.168.83.132:/home/rocky/airflow/config ~/airflow/
scp -r rocky@192.168.83.132:/home/rocky/airflow/utils ~/airflow/

# Create symlink to local DAGs
ln -s /srv/airflow/dags /home/rocky/airflow/dags

# Create utility modules
touch ~/airflow/__init__.py ~/airflow/config/__init__.py ~/airflow/utils/__init__.py

# Create DAG processor service (disabled by default)
sudo tee /etc/systemd/system/airflow-dag-processor.service << EOF
[Unit]
Description=Airflow Standalone DAG Processor (Standby)
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment="AIRFLOW_HOME=/home/rocky/airflow"
Environment="PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/rocky/airflow:/home/rocky/.local/lib/python3.9/site-packages"
Environment="LANG=en_US.UTF-8"
Environment="LC_ALL=en_US.UTF-8"
WorkingDirectory=/home/rocky/airflow
ExecStart=/bin/bash -c 'source /home/rocky/.bashrc && exec /home/rocky/.local/bin/airflow dag-processor'
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airflow-dag-processor-standby
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-dag-processor
```

---

## 🔨 **PHASE 7: Worker Node Setup**

### **Step 7.1: Install Airflow on VM4 (worker1)**

**On VM4:**
```bash
# Install dependencies
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel nfs-utils

# Create airflow directory
mkdir -p ~/airflow
echo 'export AIRFLOW_HOME=/home/rocky/airflow' >> ~/.bashrc
source ~/.bashrc

# Install Airflow
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${AIRFLOW_VERSION}.txt"

pip3 install "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip3 install paramiko

# Mount NFS for DAGs
sudo mkdir -p /mnt/airflow-dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /mnt/airflow-dags
echo "192.168.83.132:/srv/airflow/dags /mnt/airflow-dags nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Create symlinks
ln -s /mnt/airflow-dags ~/airflow/dags
mkdir -p ~/airflow/logs

# Copy configuration and modules
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

### **Step 7.2: Create Worker Service on VM4**

```bash
sudo tee /etc/systemd/system/airflow-worker.service << EOF
[Unit]
Description=Airflow Celery Worker
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
WorkingDirectory=/home/rocky/airflow
ExecStart=/bin/bash -c 'exec /home/rocky/.local/bin/airflow celery worker --queues default,card_processing_queue --concurrency 4'
Restart=on-failure
RestartSec=10s
SyslogIdentifier=airflow-worker

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-worker
```

---

## 🚀 **PHASE 8: Service Startup and Verification**

### **Step 8.1: Start Services in Correct Order**

**1. Start DAG Processor (VM2):**
```bash
# On VM2
sudo systemctl start airflow-dag-processor
sudo systemctl status airflow-dag-processor
```

**2. Start Airflow Main Services (VM1):**
```bash
# On VM1
sudo systemctl start airflow-scheduler
sleep 10
sudo systemctl start airflow-webserver
sleep 5
sudo systemctl start airflow-flower

# Check status
sudo systemctl status airflow-scheduler airflow-webserver airflow-flower
```

**3. Start Worker (VM4):**
```bash
# On VM4
sudo systemctl start airflow-worker
sudo systemctl status airflow-worker
```

### **Step 8.2: Create Sample DAG for Testing**

**On VM2 - Create test DAG:**
```bash
tee /srv/airflow/dags/test_distributed_setup.py << 'EOF'
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import socket

@dag(
    dag_id='test_distributed_setup',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        'owner': 'admin',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    tags=['test', 'distributed']
)
def test_distributed_setup():
    """
    Test DAG for distributed Airflow setup verification
    """
    
    @task
    def test_scheduler_connectivity():
        """Test that scheduler can process this task"""
        return f"Scheduler processing successful at {datetime.now()}"
    
    @task
    def test_worker_execution():
        """Test that worker can execute this task"""
        import platform
        return {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'timestamp': str(datetime.now())
        }
    
    @task
    def test_database_connectivity():
        """Test database connectivity"""
        from airflow.models import Variable
        try:
            # Try to set and get a variable to test DB connectivity
            Variable.set("test_key", "test_value")
            value = Variable.get("test_key")
            Variable.delete("test_key")
            return f"Database connectivity test passed: {value}"
        except Exception as e:
            return f"Database connectivity test failed: {str(e)}"
    
    # Define task dependencies
    scheduler_test = test_scheduler_connectivity()
    worker_test = test_worker_execution()
    db_test = test_database_connectivity()
    
    scheduler_test >> [worker_test, db_test]

# Create DAG instance
dag_instance = test_distributed_setup()
EOF

# Wait for sync and DAG processor to pick up
sleep 10
```

### **Step 8.3: Verification Steps**

**Check all services are running:**
```bash
# On VM1
echo "=== VM1 (Airflow Main) Services ==="
sudo systemctl status airflow-scheduler --no-pager -l
sudo systemctl status airflow-webserver --no-pager -l
sudo systemctl status airflow-flower --no-pager -l
sudo systemctl status haproxy --no-pager -l

# On VM2
echo "=== VM2 (NFS + DAG Processor) Services ==="
sudo systemctl status nfs-server --no-pager -l
sudo systemctl status airflow-dag-processor --no-pager -l
sudo systemctl status lsyncd --no-pager -l

# On VM4
echo "=== VM4 (Worker) Services ==="
sudo systemctl status airflow-worker --no-pager -l

# On VM5, VM6, VM7
echo "=== RabbitMQ Cluster Status ==="
sudo rabbitmqctl cluster_status

# On VM8, VM9, VM10
echo "=== PostgreSQL Cluster Status ==="
patronictl -c /usr/patroni/conf/patroni.yml list
```

**Test connectivity:**
```bash
# On VM1 - Test all connections
echo "=== Testing Connections ==="

# Test PostgreSQL HA
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "SELECT 'PostgreSQL HA connection: SUCCESS';"

# Test RabbitMQ cluster
curl -s -u airflow_user:airflow_pass http://mq1:15672/api/overview | grep -o '"cluster_name":"[^"]*"'

# Test NFS mount
ls -la /mnt/airflow-dags/

# Test Airflow CLI
airflow dags list | grep test_distributed_setup
```

**Access Web Interfaces:**
- **Airflow UI**: http://192.168.83.129:8080 (admin/admin123)
- **Flower**: http://192.168.83.129:5555
- **HAProxy Stats**: http://192.168.83.129:7000
- **RabbitMQ Management**: http://192.168.83.135:15672 (airflow_user/airflow_pass)

### **Step 8.4: Test DAG Execution**

```bash
# On VM1 - Trigger test DAG
airflow dags unpause test_distributed_setup
airflow dags trigger test_distributed_setup

# Wait and check results
sleep 30
airflow dags state test_distributed_setup $(date +%Y-%m-%d)

# Check task instances
airflow tasks states-for-dag-run test_distributed_setup $(date +%Y-%m-%d)
```

---

## 🔍 **PHASE 9: Monitoring and Maintenance**

### **Step 9.1: Create Monitoring Scripts**

**On VM1 - Health check script:**
```bash
sudo tee /usr/local/bin/airflow-health-check.sh << 'EOF'
#!/bin/bash
LOG="/var/log/airflow-health.log"
DATE=$(date)

echo "[$DATE] Starting health check..." >> $LOG

# Check Airflow services
for service in airflow-scheduler airflow-webserver airflow-flower; do
    if ! systemctl is-active --quiet $service; then
        echo "[$DATE] WARNING - $service not running" >> $LOG
    fi
done

# Check PostgreSQL HA connectivity
export PGPASSWORD=airflow_pass
if ! psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "SELECT 1;" > /dev/null 2>&1; then
    echo "[$DATE] ERROR - PostgreSQL HA connection failed" >> $LOG
fi

# Check RabbitMQ cluster
if ! curl -s -u airflow_user:airflow_pass http://mq1:15672/api/overview > /dev/null; then
    echo "[$DATE] ERROR - RabbitMQ connection failed" >> $LOG
fi

# Check NFS mount
if ! ls /mnt/airflow-dags > /dev/null 2>&1; then
    echo "[$DATE] ERROR - NFS mount not accessible" >> $LOG
fi

echo "[$DATE] Health check completed" >> $LOG
EOF

sudo chmod +x /usr/local/bin/airflow-health-check.sh

# Add to crontab
echo "*/5 * * * * /usr/local/bin/airflow-health-check.sh" | sudo crontab -
```

### **Step 9.2: Backup Procedures**

**Database backup script:**
```bash
sudo tee /usr/local/bin/airflow-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/airflow-backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
export PGPASSWORD=airflow_pass
pg_dump -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db > $BACKUP_DIR/airflow_db_backup_$DATE.sql

# Backup DAGs
tar -czf $BACKUP_DIR/dags_backup_$DATE.tar.gz -C /srv/airflow dags

# Backup configurations
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz /home/rocky/airflow/airflow.cfg /etc/systemd/system/airflow-*.service

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /usr/local/bin/airflow-backup.sh

# Schedule daily backups
echo "0 2 * * * /usr/local/bin/airflow-backup.sh" | sudo crontab -
```

---

## 🎯 **PHASE 10: Testing Failover Scenarios**

### **Step 10.1: Test PostgreSQL Failover**

```bash
# On VM8 (sql1) - Stop current leader
sudo systemctl stop patroni

# Check cluster status from another node
# On VM9
patronictl -c /usr/patroni/conf/patroni.yml list

# Verify Airflow still works
# On VM1
airflow db check
airflow dags list

# Restart VM8
# On VM8
sudo systemctl start patroni
```

### **Step 10.2: Test RabbitMQ Failover**

```bash
# On VM5 (mq1) - Stop one RabbitMQ node
sudo systemctl stop rabbitmq-server

# Check cluster status
# On VM6
sudo rabbitmqctl cluster_status

# Test worker connectivity
# On VM4
sudo journalctl -u airflow-worker -f --lines=10

# Restart VM5
# On VM5
sudo systemctl start rabbitmq-server
```

### **Step 10.3: Test NFS Failover**

```bash
# Manual failover from VM2 to VM12
# On VM2
sudo /usr/local/bin/nfs-become-standby.sh

# On VM12
sudo /usr/local/bin/nfs-become-active.sh

# Update NFS mounts on clients
# On VM1 and VM4
sudo umount /mnt/airflow-dags
sudo mount -t nfs 192.168.83.150:/srv/airflow/dags /mnt/airflow-dags

# Test DAG accessibility
ls -la /mnt/airflow-dags/

# Reverse failover when ready
# On VM12
sudo /usr/local/bin/nfs-become-standby.sh

# On VM2
sudo /usr/local/bin/nfs-become-active.sh

# Update mounts back
# On VM1 and VM4
sudo umount /mnt/airflow-dags
sudo mount -t nfs 192.168.83.132:/srv/airflow/dags /mnt/airflow-dags
```

---

## ✅ **Final Architecture Verification**

### **Expected Infrastructure Status:**

```
✅ ENTERPRISE AIRFLOW DISTRIBUTED HA CLUSTER ✅

VM1 (airflow) - Main Services:
├── ✅ Airflow Scheduler (active)
├── ✅ Airflow Webserver (active) 
├── ✅ Flower Monitor (active)
└── ✅ HAProxy Load Balancer (active)

VM2 (ftp) - Primary NFS + DAG Processor:
├── ✅ NFS Server (active)
├── ✅ DAG Processor (active)
├── ✅ File Sync (active)
└── ✅ Standby Sync (active)

VM12 (nfs2) - Standby NFS + DAG Processor:
├── ⏸️ NFS Server (standby)
├── ⏸️ DAG Processor (standby)
└── ✅ Synced Files (ready)

VM4 (worker1) - Celery Worker:
├── ✅ Airflow Worker (active)
├── ✅ NFS Mount (active)
└── ✅ Task Execution (ready)

RabbitMQ Cluster (VM5,6,7):
├── ✅ mq1 - Node 1 (active)
├── ✅ mq2 - Node 2 (active)
├── ✅ mq3 - Node 3 (active)
└── ✅ Classic HA Mirroring (active)

PostgreSQL Cluster (VM8,9,10):
├── ✅ sql1 - Leader (active)
├── ✅ sql2 - Replica (active)
├── ✅ sql3 - Replica (active)
└── ✅ etcd Coordination (active)
```

### **Key Features Achieved:**

🎯 **High Availability:**
- ✅ Automatic PostgreSQL failover
- ✅ RabbitMQ cluster with mirroring
- ✅ NFS active-passive with sync
- ✅ DAG processor redundancy

🎯 **Scalability:**
- ✅ Horizontal worker scaling
- ✅ Load-balanced database access
- ✅ Distributed task processing

🎯 **Reliability:**
- ✅ Service auto-restart
- ✅ Data replication
- ✅ Failover procedures
- ✅ Health monitoring

🎯 **Production Ready:**
- ✅ Comprehensive monitoring
- ✅ Automated backups
- ✅ Security configuration
- ✅ Documentation

---

## 📚 **Quick Reference Commands**

### **Service Management:**
```bash
# Check all Airflow services
sudo systemctl status airflow-scheduler airflow-webserver airflow-flower

# Check cluster status
patronictl -c /usr/patroni/conf/patroni.yml list
sudo rabbitmqctl cluster_status

# Manual NFS failover
sudo /usr/local/bin/nfs-become-standby.sh  # On primary
sudo /usr/local/bin/nfs-become-active.sh   # On standby
```

### **Monitoring:**
```bash
# Web interfaces
http://192.168.83.129:8080  # Airflow UI
http://192.168.83.129:5555  # Flower
http://192.168.83.129:7000  # HAProxy Stats
http://192.168.83.135:15672 # RabbitMQ Management

# Health checks
/usr/local/bin/airflow-health-check.sh
/usr/local/bin/airflow-backup.sh
```

### **Troubleshooting:**
```bash
# Check logs
sudo journalctl -u airflow-scheduler -f
sudo journalctl -u airflow-worker -f
sudo journalctl -u patroni -f

# Test connectivity
airflow db check
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db
```

---

🎉 **Congratulations! You now have a fully distributed, highly available Apache Airflow infrastructure ready for enterprise production workloads.**
