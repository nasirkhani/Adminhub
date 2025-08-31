# S01-Database_HA_Cluster_Setup.md

## PostgreSQL High Availability Cluster with Patroni and etcd

### Step 1.1:  Install PostgreSQL and etcd (VM9, VM10, VM11)

**Execute on all three database nodes (postgresql-1, postgresql-2, postgresql-3):**

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

### Step 1.2: Configure etcd Cluster

**IMPORTANT: Replace all `<POSTGRESQL_*_IP>` placeholders with your actual PostgreSQL VM IP addresses**

**On VM9 (postgresql-1):**
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
Environment=ETCD_NAME=postgresql-1
Environment=ETCD_LISTEN_PEER_URLS="http://<POSTGRESQL_1_IP>:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://<POSTGRESQL_1_IP>:2379,http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://<POSTGRESQL_1_IP>:2380"
Environment=ETCD_INITIAL_CLUSTER="postgresql-1=http://<POSTGRESQL_1_IP>:2380,postgresql-2=http://<POSTGRESQL_2_IP>:2380,postgresql-3=http://<POSTGRESQL_3_IP>:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://<POSTGRESQL_1_IP>:2379"
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

**On VM10 (postgresql-2):**
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
Environment=ETCD_NAME=postgresql-2
Environment=ETCD_LISTEN_PEER_URLS="http://<POSTGRESQL_2_IP>:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://<POSTGRESQL_2_IP>:2379,http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://<POSTGRESQL_2_IP>:2380"
Environment=ETCD_INITIAL_CLUSTER="postgresql-1=http://<POSTGRESQL_1_IP>:2380,postgresql-2=http://<POSTGRESQL_2_IP>:2380,postgresql-3=http://<POSTGRESQL_3_IP>:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://<POSTGRESQL_2_IP>:2379"
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

**On VM11 (postgresql-3):**
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
Environment=ETCD_NAME=postgresql-3
Environment=ETCD_LISTEN_PEER_URLS="http://<POSTGRESQL_3_IP>:2380,http://127.0.0.1:7001"
Environment=ETCD_LISTEN_CLIENT_URLS="http://<POSTGRESQL_3_IP>:2379,http://127.0.0.1:2379"
Environment=ETCD_INITIAL_ADVERTISE_PEER_URLS="http://<POSTGRESQL_3_IP>:2380"
Environment=ETCD_INITIAL_CLUSTER="postgresql-1=http://<POSTGRESQL_1_IP>:2380,postgresql-2=http://<POSTGRESQL_2_IP>:2380,postgresql-3=http://<POSTGRESQL_3_IP>:2380"
Environment=ETCD_ADVERTISE_CLIENT_URLS="http://<POSTGRESQL_3_IP>:2379"
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

**🔧 Automated IP Replacement Helper for etcd Configuration:**
```bash
# Create script to replace IP placeholders in etcd configuration
# CUSTOMIZE these values with your actual PostgreSQL VM IPs:
POSTGRESQL_1_IP="192.168.1.18"  # Replace with VM9 IP
POSTGRESQL_2_IP="192.168.1.19"  # Replace with VM10 IP  
POSTGRESQL_3_IP="192.168.1.20"  # Replace with VM11 IP

# Replace placeholders in etcd service file
sudo sed -i "s/<POSTGRESQL_1_IP>/$POSTGRESQL_1_IP/g" /etc/systemd/system/etcd.service
sudo sed -i "s/<POSTGRESQL_2_IP>/$POSTGRESQL_2_IP/g" /etc/systemd/system/etcd.service
sudo sed -i "s/<POSTGRESQL_3_IP>/$POSTGRESQL_3_IP/g" /etc/systemd/system/etcd.service

echo "etcd configuration updated. Verifying:"
grep -E "ETCD_.*IP" /etc/systemd/system/etcd.service
```

**Start etcd on all nodes:**
```bash
# On VM9, VM10, VM11 - Start etcd services
sudo systemctl daemon-reload
sudo systemctl enable etcd
sudo systemctl start etcd
sudo systemctl status etcd
```

### Step 1.3: Configure Patroni SSL Certificates

**On VM9 (postgresql-1):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=postgresql-1"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

**On VM10 (postgresql-2):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=postgresql-2"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

**On VM11 (postgresql-3):**
```bash
sudo mkdir -p /usr/patroni/conf
cd /usr/patroni/conf
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=US/ST=State/L=City/O=Company/OU=IT/CN=postgresql-3"
sudo chmod 400 server.*
sudo chown postgres:postgres server.*
```

### Step 1.4: Configure Patroni

**⚠️ IMPORTANT: Replace `<POSTGRESQL_*_IP>` placeholders with your actual PostgreSQL VM IP addresses**

**On VM9 (postgresql-1):**
```bash
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: postgresql-1
restapi:
  listen: <POSTGRESQL_1_IP>:8008
  connect_address: <POSTGRESQL_1_IP>:8008
etcd:
  hosts: <POSTGRESQL_1_IP>:2379,<POSTGRESQL_2_IP>:2379,<POSTGRESQL_3_IP>:2379
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
    - host replication replicator <POSTGRESQL_1_IP>/32 md5
    - host replication replicator <POSTGRESQL_2_IP>/32 md5
    - host replication replicator <POSTGRESQL_3_IP>/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: <POSTGRESQL_1_IP>:5432
  connect_address: <POSTGRESQL_1_IP>:5432
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

**On VM10 (postgresql-2):**
```bash
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: postgresql-2
restapi:
  listen: <POSTGRESQL_2_IP>:8008
  connect_address: <POSTGRESQL_2_IP>:8008
etcd:
  hosts: <POSTGRESQL_1_IP>:2379,<POSTGRESQL_2_IP>:2379,<POSTGRESQL_3_IP>:2379
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
    - host replication replicator <POSTGRESQL_1_IP>/32 md5
    - host replication replicator <POSTGRESQL_2_IP>/32 md5
    - host replication replicator <POSTGRESQL_3_IP>/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: <POSTGRESQL_2_IP>:5432
  connect_address: <POSTGRESQL_2_IP>:5432
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

**On VM11 (postgresql-3):**
```bash
sudo tee /usr/patroni/conf/patroni.yml << EOF
scope: postgres
namespace: AirflowPatroni
name: postgresql-3
restapi:
  listen: <POSTGRESQL_3_IP>:8008
  connect_address: <POSTGRESQL_3_IP>:8008
etcd:
  hosts: <POSTGRESQL_1_IP>:2379,<POSTGRESQL_2_IP>:2379,<POSTGRESQL_3_IP>:2379
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
    - host replication replicator <POSTGRESQL_1_IP>/32 md5
    - host replication replicator <POSTGRESQL_2_IP>/32 md5
    - host replication replicator <POSTGRESQL_3_IP>/32 md5
    - host all all 0.0.0.0/0 md5
users:
  admin:
    password: admin
    options:
      - createrole
      - createdb
postgresql:
  listen: <POSTGRESQL_3_IP>:5432
  connect_address: <POSTGRESQL_3_IP>:5432
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

**🔧 Automated IP Replacement Helper for Patroni Configuration:**
```bash
# Run this on each PostgreSQL VM after creating patroni.yml
# CUSTOMIZE these values with your actual PostgreSQL VM IPs:
POSTGRESQL_1_IP="192.168.1.18"  # Replace with VM9 IP
POSTGRESQL_2_IP="192.168.1.19"  # Replace with VM10 IP  
POSTGRESQL_3_IP="192.168.1.20"  # Replace with VM11 IP

# Replace placeholders in Patroni configuration
sudo sed -i "s/<POSTGRESQL_1_IP>/$POSTGRESQL_1_IP/g" /usr/patroni/conf/patroni.yml
sudo sed -i "s/<POSTGRESQL_2_IP>/$POSTGRESQL_2_IP/g" /usr/patroni/conf/patroni.yml
sudo sed -i "s/<POSTGRESQL_3_IP>/$POSTGRESQL_3_IP/g" /usr/patroni/conf/patroni.yml

echo "Patroni configuration updated. Verifying:"
grep -E "listen:|connect_address:|hosts:" /usr/patroni/conf/patroni.yml
```

### Step 1.5: Create Patroni Service and Start Cluster

**On VM9, VM10, VM11:**
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

### Step 1.6: Configure Firewall for Database Cluster

**On VM9, VM10, VM11:**
```bash
sudo firewall-cmd --permanent --add-port=5432/tcp   # PostgreSQL
sudo firewall-cmd --permanent --add-port=8008/tcp   # Patroni REST API
sudo firewall-cmd --permanent --add-port=2379/tcp   # etcd client
sudo firewall-cmd --permanent --add-port=2380/tcp   # etcd peer
sudo firewall-cmd --reload
```

### Step 1.7: Verify Database Cluster Setup

**Test cluster functionality using hostnames (from any PostgreSQL node):**
```bash
echo "=== PostgreSQL HA Cluster Verification ==="

# 1. Check etcd cluster health
echo "1. etcd Cluster Status:"
etcdctl --endpoints=postgresql-1:2379,postgresql-2:2379,postgresql-3:2379 endpoint health

# 2. Check Patroni cluster status  
echo ""
echo "2. Patroni Cluster Status:"
patronictl -c /usr/patroni/conf/patroni.yml list

# 3. Test database connectivity to each node
echo ""
echo "3. Database Connectivity Test:"
for host in postgresql-1 postgresql-2 postgresql-3; do
    export PGPASSWORD=postgres
    if psql -h $host -U postgres -p 5432 -c "SELECT 'Connection to $host: SUCCESS', pg_is_in_recovery();" 2>/dev/null; then
        echo "✅ $host: Database accessible"
    else
        echo "❌ $host: Database connection failed"
    fi
done

# 4. Identify current leader
echo ""
echo "4. Current Leader Identification:"
export PGPASSWORD=postgres
LEADER_IP=$(psql -h postgresql-1 -U postgres -p 5432 -t -c "SELECT CASE WHEN pg_is_in_recovery() THEN 'replica' ELSE inet_server_addr() END;" 2>/dev/null | xargs)
echo "Current Leader IP: $LEADER_IP"

# 5. Test replication
echo ""
echo "5. Replication Test:"
export PGPASSWORD=postgres
TEST_VALUE="test_$(date +%s)"
psql -h postgresql-1 -U postgres -p 5432 -c "CREATE TABLE IF NOT EXISTS replication_test (id serial, data text, created_at timestamp DEFAULT now());" >/dev/null 2>&1
psql -h postgresql-1 -U postgres -p 5432 -c "INSERT INTO replication_test (data) VALUES ('$TEST_VALUE');" >/dev/null 2>&1

sleep 5

# Check replication on all nodes
for host in postgresql-1 postgresql-2 postgresql-3; do
    RESULT=$(psql -h $host -U postgres -p 5432 -t -c "SELECT data FROM replication_test WHERE data = '$TEST_VALUE';" 2>/dev/null | xargs)
    if [ "$RESULT" = "$TEST_VALUE" ]; then
        echo "✅ $host: Replication working"
    else
        echo "❌ $host: Replication failed"
    fi
done

# Cleanup test table
psql -h postgresql-1 -U postgres -p 5432 -c "DROP TABLE IF EXISTS replication_test;" >/dev/null 2>&1

echo ""
echo "=== Database HA Cluster Setup Complete ==="
```

**🔧 Alternative Verification Using IP Addresses:**
```bash
# If hostname resolution isn't working, use IPs directly
# REPLACE with your actual PostgreSQL VM IPs:
POSTGRESQL_1_IP="192.168.1.18"  # Replace with VM9 IP
POSTGRESQL_2_IP="192.168.1.19"  # Replace with VM10 IP  
POSTGRESQL_3_IP="192.168.1.20"  # Replace with VM11 IP

echo "=== PostgreSQL HA Cluster Verification (Using IPs) ==="

# Check connectivity to each node
for ip in $POSTGRESQL_1_IP $POSTGRESQL_2_IP $POSTGRESQL_3_IP; do
    export PGPASSWORD=postgres
    if psql -h $ip -U postgres -p 5432 -c "SELECT 'Connection to $ip: SUCCESS';" 2>/dev/null; then
        echo "✅ $ip: Database accessible"
    else
        echo "❌ $ip: Database connection failed"
    fi
done
```

This completes the PostgreSQL High Availability cluster setup with:

✅ **3-Node etcd Cluster**: Distributed consensus for leader election  
✅ **3-Node PostgreSQL Cluster**: Primary-replica setup with automatic failover  
✅ **Patroni Orchestration**: Automated cluster management and failover  
✅ **SSL Encryption**: Secure database connections  
✅ **Streaming Replication**: Real-time data synchronization  
✅ **Health Monitoring**: REST API endpoints for cluster monitoring  

**Next Steps**: Proceed to **S02-HAProxy_Load_Balancer_HA_Setup.md** to configure load balancing and VIP management for the database cluster.

