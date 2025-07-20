# 🚀 **PostgreSQL HA Implementation Plan**


---

## **📋 Implementation Overview**

### **Current State:**
- **VM1**: PostgreSQL 13.20 with `airflow_db`, `airflow_user`, `airflow_pass`
- **Target**: 3-node PostgreSQL cluster with Patroni + etcd + HAProxy

### **New Infrastructure:**
```
VM8 (192.168.83.140) - psg1 - Primary PostgreSQL + Patroni + etcd
VM9 (192.168.83.144) - psg2 - Replica PostgreSQL + Patroni + etcd  
VM10 (192.168.83.145) - psg3 - Replica PostgreSQL + Patroni + etcd
VM1 (192.168.83.129) - HAProxy (added to existing services)
```

---

## **🔧 Phase 1: VM Preparation & Networking**

### **Step 1.1: Create VMs in VMware**
Create 3 new VMs with Rocky Linux 9:
- **CPU**: 1 core each
- **RAM**: 1GB each (can scale later)
- **Disk**: 20GB minimum (for PostgreSQL data)
- **Network**: Same subnet as existing VMs

### **Step 1.2: Basic OS Configuration**
```bash
# On each new VM (VM8, VM9, VM10):

# Update system
sudo dnf update -y

# Set hostnames
sudo hostctl set-hostname psg1    # On VM8
sudo hostctl set-hostname psg2    # On VM9  
sudo hostctl set-hostname psg3    # On VM10

# Add host entries on ALL VMs (including existing ones)
sudo tee -a /etc/hosts << EOF
192.168.83.140 psg1
192.168.83.144 psg2
192.168.83.145 psg3
EOF
```

### **Step 1.3: SSH Key Setup**
```bash
# On VM1 (generate key if not exists):
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy SSH key to new PostgreSQL VMs:
ssh-copy-id rocky@192.168.83.140  # psg1
ssh-copy-id rocky@192.168.83.144  # psg2
ssh-copy-id rocky@192.168.83.145  # psg3

# Also setup keys between PostgreSQL VMs themselves:
# On psg1:
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id rocky@psg2
ssh-copy-id rocky@psg3

# Repeat for psg2 and psg3
```

### **Step 1.4: Firewall Configuration**
```bash
# On each PostgreSQL VM (VM8, VM9, VM10):

# PostgreSQL port
sudo firewall-cmd --permanent --add-port=5432/tcp

# Patroni REST API
sudo firewall-cmd --permanent --add-port=8008/tcp

# etcd client port
sudo firewall-cmd --permanent --add-port=2379/tcp

# etcd peer port  
sudo firewall-cmd --permanent --add-port=2380/tcp

# Reload firewall
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

---

## **🗄️ Phase 2: PostgreSQL Installation**

### **Step 2.1: Install PostgreSQL 13 on New VMs**
```bash
# On VM8, VM9, VM10:

# Install PostgreSQL 13 (same version as VM1)
sudo dnf install -y postgresql-server postgresql-contrib

# Verify version matches VM1
postgres --version
# Should show: postgres (PostgreSQL) 13.20
```

### **Step 2.2: Initial PostgreSQL Setup**
```bash
# On each new VM - DO NOT initialize yet (Patroni will handle this)
# Just install the packages for now

# Create postgres user directories
sudo mkdir -p /var/lib/postgresql/13/main
sudo chown postgres:postgres /var/lib/postgresql/13/main
```

---

## **🔄 Phase 3: etcd Cluster Setup**

### **Step 3.1: Install etcd**
```bash
# On VM8, VM9, VM10:

# Download and install etcd
ETCD_VER=v3.5.9
wget https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzf etcd-${ETCD_VER}-linux-amd64.tar.gz
sudo mv etcd-${ETCD_VER}-linux-amd64/etcd* /usr/local/bin/
sudo chmod +x /usr/local/bin/etcd*

# Create etcd user and directories
sudo useradd --system --shell /bin/false etcd
sudo mkdir -p /var/lib/etcd
sudo chown etcd:etcd /var/lib/etcd
```

### **Step 3.2: Configure etcd Cluster**

---

## **🔧 Quick Fix: Correct etcd Configuration per VM**

### **On VM8 (psg1 - 192.168.83.140):**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd distributed reliable key-value store
After=network.target

[Service]
Type=notify
User=etcd
ExecStart=/usr/local/bin/etcd \\
  --name psg1 \\
  --data-dir /var/lib/etcd \\
  --initial-advertise-peer-urls http://192.168.83.140:2380 \\
  --listen-peer-urls http://192.168.83.140:2380 \\
  --advertise-client-urls http://192.168.83.140:2379 \\
  --listen-client-urls http://192.168.83.140:2379,http://127.0.0.1:2379 \\
  --initial-cluster psg1=http://192.168.83.140:2380,psg2=http://192.168.83.144:2380,psg3=http://192.168.83.145:2380 \\
  --initial-cluster-state new \\
  --initial-cluster-token etcd-cluster-airflow
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### **On VM9 (psg2 - 192.168.83.144):**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd distributed reliable key-value store
After=network.target

[Service]
Type=notify
User=etcd
ExecStart=/usr/local/bin/etcd \\
  --name psg2 \\
  --data-dir /var/lib/etcd \\
  --initial-advertise-peer-urls http://192.168.83.144:2380 \\
  --listen-peer-urls http://192.168.83.144:2380 \\
  --advertise-client-urls http://192.168.83.144:2379 \\
  --listen-client-urls http://192.168.83.144:2379,http://127.0.0.1:2379 \\
  --initial-cluster psg1=http://192.168.83.140:2380,psg2=http://192.168.83.144:2380,psg3=http://192.168.83.145:2380 \\
  --initial-cluster-state new \\
  --initial-cluster-token etcd-cluster-airflow
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### **On VM10 (psg3 - 192.168.83.145):**
```bash
sudo tee /etc/systemd/system/etcd.service << EOF
[Unit]
Description=etcd distributed reliable key-value store
After=network.target

[Service]
Type=notify
User=etcd
ExecStart=/usr/local/bin/etcd \\
  --name psg3 \\
  --data-dir /var/lib/etcd \\
  --initial-advertise-peer-urls http://192.168.83.145:2380 \\
  --listen-peer-urls http://192.168.83.145:2380 \\
  --advertise-client-urls http://192.168.83.145:2379 \\
  --listen-client-urls http://192.168.83.145:2379,http://127.0.0.1:2379 \\
  --initial-cluster psg1=http://192.168.83.140:2380,psg2=http://192.168.83.144:2380,psg3=http://192.168.83.145:2380 \\
  --initial-cluster-state new \\
  --initial-cluster-token etcd-cluster-airflow
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

---

## **🧹 Clean Start Required:**

### **On ALL VMs (VM8, VM9, VM10):**
```bash
# Stop etcd
sudo systemctl stop etcd

# Clean existing data (important!)
sudo rm -rf /var/lib/etcd/*

# Reload systemd
sudo systemctl daemon-reload

# Start etcd on ONE VM first (psg1):
sudo systemctl start etcd
sudo systemctl status etcd

# Then start on other VMs
```

---

## **⚡ Start Order:**
1. **Start VM8 (psg1) first** - it will wait for cluster
2. **Start VM9 (psg2) second** - cluster will form
3. **Start VM10 (psg3) third** - joins existing cluster

**Fix the configuration files first, then restart in order!**
---

## **🎛️ Phase 4: Patroni Installation**

### **Step 4.1: Install Patroni**
```bash
# On VM8, VM9, VM10:

# Install Python and pip
sudo dnf install -y python3 python3-pip python3-devel

# Install Patroni with PostgreSQL and etcd support
sudo pip3 install patroni[etcd,postgresql]

# Create Patroni directories
sudo mkdir -p /etc/patroni
sudo mkdir -p /var/log/patroni
```

### **Step 4.2: Patroni Configuration**
```yaml
# On VM8 (psg1) - /etc/patroni/patroni.yml:
scope: airflow-cluster
namespace: /airflow/
name: psg1

restapi:
  listen: 192.168.83.140:8008
  connect_address: 192.168.83.140:8008

etcd:
  hosts: 192.168.83.140:2379,192.168.83.144:2379,192.168.83.145:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 30
    maximum_lag_on_failover: 1048576
    synchronous_mode: true
    postgresql:
      use_pg_rewind: true
      parameters:
        max_connections: 200
        shared_preload_libraries: ''
        wal_level: replica
        hot_standby: 'on'
        wal_keep_segments: 100
        max_wal_senders: 10
        synchronous_commit: 'on'
        synchronous_standby_names: '*'
        
  initdb:
    - encoding: UTF8
    - data-checksums
    
  pg_hba:
    - host replication replicator 192.168.83.0/24 md5
    - host all all 192.168.83.0/24 md5
    - host all all 127.0.0.1/32 md5

  users:
    admin:
      password: admin_secure_pass
      options:
        - createrole
        - createdb

postgresql:
  listen: 192.168.83.140:5432
  connect_address: 192.168.83.140:5432
  data_dir: /var/lib/postgresql/13/main
  bin_dir: /usr/bin
  authentication:
    replication:
      username: replicator
      password: replicator_secure_pass
    superuser:
      username: postgres
      password: postgres_secure_pass

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

---

## **🔧 Phase 5: Service Setup & Bootstrap**

### **Step 5.1: Create Systemd Services**
```bash
# On all PostgreSQL VMs - /etc/systemd/system/patroni.service:
sudo tee /etc/systemd/system/patroni.service << EOF
[Unit]
Description=Patroni PostgreSQL Cluster Manager
After=network.target etcd.service
Requires=etcd.service

[Service]
Type=notify
User=postgres
ExecStart=/usr/local/bin/patroni /etc/patroni/patroni.yml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### **Step 5.2: Bootstrap Cluster**
```bash
# Start etcd on all nodes first:
sudo systemctl enable etcd
sudo systemctl start etcd

# Check etcd cluster health:
etcdctl --endpoints=http://192.168.83.140:2379,http://192.168.83.144:2379,http://192.168.83.145:2379 endpoint health

# Start Patroni (start with psg1 first):
sudo systemctl enable patroni
sudo systemctl start patroni

# Check cluster status:
patronictl -c /etc/patroni/patroni.yml list
```

---

## **📊 Phase 6: Data Migration from VM1**

### **Step 6.1: Backup Current Database**
```bash
# On VM1:
sudo -u postgres pg_dump airflow_db > /tmp/airflow_db_backup.sql

# Copy to psg1:
scp /tmp/airflow_db_backup.sql rocky@psg1:/tmp/
```

### **Step 6.2: Restore to New Cluster**
```bash
# On psg1 (primary):
sudo -u postgres createdb airflow_db
sudo -u postgres createuser airflow_user
sudo -u postgres psql -c "ALTER USER airflow_user WITH PASSWORD 'airflow_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;"
sudo -u postgres psql airflow_db < /tmp/airflow_db_backup.sql
```

---

## **⚖️ Phase 7: HAProxy Setup on VM1**

### **Step 7.1: Install HAProxy**
```bash
# On VM1:
sudo dnf install -y haproxy

# Configure HAProxy - /etc/haproxy/haproxy.cfg:
sudo tee /etc/haproxy/haproxy.cfg << EOF
global
    log 127.0.0.1:514 local0
    chroot /var/lib/haproxy
    user haproxy
    group haproxy
    daemon

defaults
    mode tcp
    log global
    option tcplog
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

# PostgreSQL Primary (Read/Write)
frontend postgres_primary_frontend
    bind *:5433
    default_backend postgres_primary_backend

backend postgres_primary_backend
    option httpchk GET /primary
    http-check port 8008
    server psg1 192.168.83.140:5432 check port 8008
    server psg2 192.168.83.144:5432 check port 8008 backup
    server psg3 192.168.83.145:5432 check port 8008 backup

# PostgreSQL Replica (Read-Only)
frontend postgres_replica_frontend  
    bind *:5434
    default_backend postgres_replica_backend

backend postgres_replica_backend
    option httpchk GET /replica
    http-check port 8008
    server psg2 192.168.83.144:5432 check port 8008
    server psg3 192.168.83.145:5432 check port 8008
    server psg1 192.168.83.140:5432 check port 8008 backup
EOF

# Enable and start HAProxy:
sudo systemctl enable haproxy
sudo systemctl start haproxy
```

---

## **🔧 Phase 8: Update Airflow Configuration**

### **Step 8.1: Update airflow.cfg**
```bash
# On VM1, update /home/rocky/airflow/airflow.cfg:

# Change from:
# sql_alchemy_conn = postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

# To:
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@localhost:5433/airflow_db

# Also update result_backend:
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5433/airflow_db
```

### **Step 8.2: Restart Airflow Services**
```bash
# On VM1:
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver

# On VM4:
sudo systemctl restart airflow-celery-worker
```

---

## **✅ Phase 9: Testing & Validation**

### **Step 9.1: Cluster Health Check**
```bash
# Check Patroni cluster:
patronictl -c /etc/patroni/patroni.yml list

# Check HAProxy stats:
echo "show stat" | socat stdio /var/lib/haproxy/stats

# Test connections:
psql -h localhost -p 5433 -U airflow_user -d airflow_db -c "SELECT version();"
```

### **Step 9.2: Failover Testing**
```bash
# Simulate primary failure (on psg1):
sudo systemctl stop patroni

# Verify automatic failover:
patronictl -c /etc/patroni/patroni.yml list

# Test Airflow still works:
# Trigger a simple DAG and verify it runs
```

---

## **🎯 Expected Results**

- ✅ **Zero downtime** PostgreSQL cluster
- ✅ **Automatic failover** (< 30 seconds)
- ✅ **No data loss** (synchronous replication)
- ✅ **Load balancing** (reads distributed to replicas)
- ✅ **Eliminated SPOF** for database layer

**Ready to start with Phase 1? This will give you enterprise-grade database HA for your financial card processing operations!**
