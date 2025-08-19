## PostgreSQL High Availability Cluster with Patroni and etcd

### Step 1.1: Install PostgreSQL and etcd (VM8, VM9, VM10)

Execute on all three database nodes:

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

### Step 1.3: Configure Patroni SSL Certificates

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

### Step 1.4: Configure Patroni

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

### Step 1.5: Create Patroni Service and Start Cluster

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

### Step 1.6: Configure Firewall for Database Cluster

**On VM8, VM9, VM10:**
```bash
sudo firewall-cmd --permanent --add-port=5432/tcp   # PostgreSQL
sudo firewall-cmd --permanent --add-port=8008/tcp   # Patroni REST API
sudo firewall-cmd --permanent --add-port=2379/tcp   # etcd client
sudo firewall-cmd --permanent --add-port=2380/tcp   # etcd peer
sudo firewall-cmd --reload
```

