Setting up a Patroni cluster for PostgreSQL on Rocky Linux 9 with your specified VM configurations involves a series of steps. Patroni provides high availability, load balancing, and automatic failover for PostgreSQL, using ETCD for coordination and HAProxy for load balancing.

-----

### **Infrastructure Prerequisites**

Ensure you have the following before beginning the setup:

  * **Four hosts (physical or virtual) with Rocky Linux 9 installed:**
      * **sql1:** IP: `192.168.83.148`
      * **sql2:** IP: `192.168.83.147`
      * **sql3:** IP: `192.168.83.149`
      * **airflow (Master/HAProxy node):** IP: `192.168.83.129`
  * All OS packages are updated.
  * All nodes can connect to each other internally.
  * **Username:** `Rocky` (for all VMs)
  * **Password:** `111` (for all VMs)

-----

### **1. Set Hostnames**

On each respective node, set the hostname using the `nmcli` command and then reboot.

  * **On sql1:**
    ```bash
    nmcli general hostname sql1
    reboot
    ```
  * **On sql2:**
    ```bash
    nmcli general hostname sql2
    reboot
    ```
  * **On sql3:**
    ```bash
    nmcli general hostname sql3
    reboot
    ```
  * **On airflow (Master Node):**
    ```bash
    nmcli general hostname airflow
    reboot
    ```

-----

### **2. Add IP Addresses to `/etc/hosts`**

On **all four hosts** (sql1, sql2, sql3, and airflow), add the IP addresses and hostnames to the `/etc/hosts` file.

```bash
sudo vi /etc/hosts
```

Add the following entries:

```
192.168.83.129 airflow
192.168.83.148 sql1
192.168.83.147 sql2
192.168.83.149 sql3
```

-----

### **3. Setup ETCD on sql1, sql2, and sql3**

First, download ETCD binaries, then copy them to the binary location. Replace `v3.4.34` with the latest stable release from [etcd-io/etcd/releases](https://github.com/etcd-io/etcd/releases).

**On sql1, sql2, and sql3:**

```bash
ETCD_VER=v3.4.34
GOOGLE_URL=https://storage.googleapis.com/etcd
GITHUB_URL=https://github.com/etcd-io/etcd/releases/download
DOWNLOAD_URL=${GOOGLE_URL}

rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

/tmp/etcd-download-test/etcd --version
/tmp/etcd-download-test/etcdctl version
```

You should see output similar to this (version might differ):

```
etcd Version: 3.4.34
Git SHA: c123b3ea3
Go Version: go1.22.7
Go OS/Arch: linux/amd64
etcdctl version: 3.4.34
API version: 3.4
```

Now, move the binaries to `/usr/local/bin`:

```bash
cd /tmp/etcd-download-test/
sudo mv etcd* /usr/local/bin
```

Verify ETCD commands after moving binaries:

```bash
etcd --version
etcdctl version
```

#### **Configure ETCD System Service**

Create directories for the library and config file:

```bash
sudo mkdir -p /var/lib/etcd/
sudo mkdir /etc/etcd
```

Create an ETCD system user:

```bash
sudo groupadd --system etcd
sudo useradd -s /sbin/nologin --system -g etcd etcd
```

Change ownership and permissions:

```bash
sudo chown -R etcd:etcd /var/lib/etcd/
sudo chmod 0775 /var/lib/etcd/
```

Create the systemd service file for the ETCD daemon on **sql1, sql2, and sql3**.

  * **On sql1:**

    ```bash
    sudo vi /etc/systemd/system/etcd.service
    ```

    Add the following content:

    ```
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
    ExecStart=/usr/local/bin/etcd \
    --enable-v2=true
    Restart=always
    RestartSec=10s
    LimitNOFILE=40000

    [Install]
    WantedBy=multi-user.target
    ```

  * **On sql2:**

    ```bash
    sudo vi /etc/systemd/system/etcd.service
    ```

    Add the following content:

    ```
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
    ExecStart=/usr/local/bin/etcd \
    --enable-v2=true
    Restart=always
    RestartSec=10s
    LimitNOFILE=40000

    [Install]
    WantedBy=multi-user.target
    ```

  * **On sql3:**

    ```bash
    sudo vi /etc/systemd/system/etcd.service
    ```

    Add the following content:

    ```
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
    ExecStart=/usr/local/bin/etcd \
    --enable-v2=true
    Restart=always
    RestartSec=10s
    LimitNOFILE=40000

    [Install]
    WantedBy=multi-user.target
    ```

If SELinux is running in enforcing mode, run the following commands to make the local policy active **on all three nodes (sql1, sql2, and sql3)**:

```bash
sudo restorecon -Rv /usr/local/bin/etcd
```

Start the ETCD service and check its status **on all three nodes (sql1, sql2, and sql3)**:

```bash
sudo systemctl start etcd
sudo systemctl status etcd
```

-----

### **4. Download and Install PostgreSQL Server 16 on sql1, sql2, and sql3**

**On sql1, sql2, and sql3:**

```bash
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql16-server postgresql16-contrib
```

After installing the PostgreSQL Server packages, create a symbolic link of PostgreSQL binaries to `/usr/sbin` for Patroni to work correctly.

```bash
sudo ln -s /usr/pgsql-16/bin /usr/sbin
```

-----

### **5. Download Patroni on sql1, sql2, and sql3**

**On sql1, sql2, and sql3:**

```bash
curl https://bootstrap.pypa.io/pip/3.6/get-pip.py -o /tmp/get-pip.py -k
python3 /tmp/get-pip.py
sudo pip install psycopg2-binary
sudo pip install patroni[etcd,consul]
```

-----

### **6. Configure Patroni on sql1, sql2, and sql3**

Create a directory, navigate to it, generate SSL certificates, set permissions, and change ownership.

  * **On sql1:**

    ```bash
    sudo mkdir -p /usr/patroni/conf
    cd /usr/patroni/conf

    sudo openssl genrsa -out server.key 2048
    sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=HuzefaPatel/OU=IT/CN=sql1"

    sudo chmod 400 server.*
    sudo chown postgres:postgres server.*
    ```

  * **On sql2:**

    ```bash
    sudo mkdir -p /usr/patroni/conf
    cd /usr/patroni/conf

    sudo openssl genrsa -out server.key 2048
    sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=HuzefaPatel/OU=IT/CN=sql2"

    sudo chmod 400 server.*
    sudo chown postgres:postgres server.*
    ```

  * **On sql3:**

    ```bash
    sudo mkdir -p /usr/patroni/conf
    cd /usr/patroni/conf

    sudo openssl genrsa -out server.key 2048
    sudo openssl req -new -x509 -days 3650 -key server.key -out server.crt -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=HuzefaPatel/OU=IT/CN=sql3"

    sudo chmod 400 server.*
    sudo chown postgres:postgres server.*
    ```

#### **Create YAML Configuration File for Patroni**

Create the Patroni YAML configuration file on **sql1, sql2, and sql3**.

  * **On sql1:**

    ```bash
    sudo vi /usr/patroni/conf/patroni.yml
    ```

    Add the following content:

    ```yaml
    scope: postgres
    namespace: HuzefasPatroni
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
            shared_buffers: 2GB
            work_mem: 16MB
            maintenance_work_mem: 1GB
            max_worker_processes: 16
            wal_buffers: 64MB
            max_wal_size: 2GB
            min_wal_size: 1GB
            effective_cache_size: 64GB
            fsync: on
            checkpoint_completion_target: 0.9
            log_rotation_size: 100MB
            listen_addresses: "*"
            max_connections: 2000
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
      nosync: true
    ```

  * **On sql2:**

    ```bash
    sudo vi /usr/patroni/conf/patroni.yml
    ```

    Add the following content:

    ```yaml
    scope: postgres
    namespace: HuzefasPatroni
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
            shared_buffers: 2GB
            work_mem: 16MB
            maintenance_work_mem: 1GB
            max_worker_processes: 16
            wal_buffers: 64MB
            max_wal_size: 2GB
            min_wal_size: 1GB
            effective_cache_size: 64GB
            fsync: on
            checkpoint_completion_target: 0.9
            log_rotation_size: 100MB
            listen_addresses: "*"
            max_connections: 2000
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
      nosync: true
    ```

  * **On sql3:**

    ```bash
    sudo vi /usr/patroni/conf/patroni.yml
    ```

    Add the following content:

    ```yaml
    scope: postgres
    namespace: HuzefasPatroni
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
            shared_buffers: 2GB
            work_mem: 16MB
            maintenance_work_mem: 1GB
            max_worker_processes: 16
            wal_buffers: 64MB
            max_wal_size: 2GB
            min_wal_size: 1GB
            effective_cache_size: 64GB
            fsync: on
            checkpoint_completion_target: 0.9
            log_rotation_size: 100MB
            listen_addresses: "*"
            max_connections: 2000
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
      nosync: true
    ```

#### **Create Patroni Service File**

Create the Patroni service file on **sql1, sql2, and sql3**.

```bash
sudo vi /usr/lib/systemd/system/patroni.service
```

Add the following content:

```
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
ExecReload=/bin/kill -HUP $MAINPID
LimitNOFILE=65536
KillMode=process
KillSignal=SIGINT
Restart=on-abnormal
RestartSec=30s
TimeoutSec=0

[Install]
WantedBy=multi-user.target
```

-----

### **7. Start the Patroni Service on sql1, sql2, and sql3**

**On sql1, sql2, and sql3:**

```bash
sudo systemctl daemon-reload
sudo systemctl start patroni
sudo systemctl status patroni
```

-----

### **8. Enable Patroni and ETCD Services on sql1, sql2, and sql3**

**On sql1, sql2, and sql3:**

```bash
sudo systemctl enable etcd
sudo systemctl enable patroni
```

-----

### **9. Configure HAProxy on airflow (Master Node)**

#### **Install HAProxy Package**

**On airflow:**

```bash
sudo yum -y install haproxy
```

#### **Create Systemd Configuration File for HAProxy**

**On airflow:**

```bash
sudo vi /etc/systemd/system/multi-user.target.wants/haproxy.service
```

Add the following content:

```
[Unit]
Description=HAProxy Load Balancer
After=network-online.target
Wants=network-online.target

[Service]
EnvironmentFile=-/etc/sysconfig/haproxy
Environment="CONFIG=/etc/haproxy/haproxy.cfg" "PIDFILE=/run/haproxy.pid" "CFGDIR=/etc/haproxy/conf.d"
ExecStartPre=/usr/sbin/haproxy -f $CONFIG -f $CFGDIR -c -q $OPTIONS
ExecStart=/usr/sbin/haproxy -Ws -f $CONFIG -f $CFGDIR -p $PIDFILE $OPTIONS
ExecReload=/usr/sbin/haproxy -f $CONFIG -f $CFGDIR -c -q $OPTIONS
ExecReload=/bin/kill -USR2 $MAINPID
KillMode=mixed
SuccessExitStatus=143
Type=notify

[Install]
WantedBy=multi-user.target
```

#### **Edit HAProxy Configuration File**

Edit the HAProxy configuration file, remove its existing content, and add the configuration below.

**On airflow:**

```bash
sudo vi /etc/haproxy/haproxy.cfg
```

Add the following content:

```
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
```

#### **Start the HAProxy Service**

**On airflow:**

```bash
sudo systemctl start haproxy
sudo systemctl status haproxy
```

#### **Enable HAProxy Service**

**On airflow:**

```bash
sudo systemctl enable haproxy
```

-----

### **10. Test the Patroni Cluster**

The Patroni cluster setup is now complete. Let's try connecting to it.

**On sql1 (or any node with `psql` installed):**

```bash
export PGPASSWORD=postgres
psql -h airflow -d postgres -U postgres -p 5000
```

You should see a `psql` prompt, indicating a successful connection.

```
psql (16.4)
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
Type "help" for help.
postgres=#
```

Per the HAProxy configuration, port `5000` is for read-write connections (to the primary/leader node), and port `6000` is for read-only connections (to a replica). Let's test this.

Query the connection on port `5000`:

```bash
psql -h airflow -d postgres -U postgres -p 5000 -c "select pg_is_in_recovery(),inet_server_addr();"
```

Expected output (the IP will be of your current leader, e.g., `192.168.83.148` for sql1 initially):

```
 pg_is_in_recovery | inet_server_addr
-------------------+------------------
 f                 | 192.168.83.148
(1 row)
```

Now, query the connection on port `6000` multiple times to see connections to different replicas:

```bash
psql -h airflow -d postgres -U postgres -p 6000 -c "select pg_is_in_recovery(),inet_server_addr();"
```

Expected output (the IP will be of a replica, e.g., `192.168.83.147` or `192.168.83.149`):

```
 pg_is_in_recovery | inet_server_addr
-------------------+------------------
 t                 | 192.168.83.147
(1 row)
```

-----

### **11. Check Cluster Status and Test Failover/Switchover**

You can check the cluster status and perform failover/switchover using the `patronictl` utility.

**On sql1 (or any Patroni node):**

```bash
patronictl -c /usr/patroni/conf/patroni.yml list
```

Example output:

```
+---------+-----------------+---------+-----------+----+-----------+--------------+
| Member  | Host            | Role    | State     | TL | Lag in MB | Tags         |
+---------+-----------------+---------+-----------+----+-----------+--------------+
| sql1    | 192.168.83.148  | Leader  | running   |  1 |           | nosync: true |
| sql2    | 192.168.83.147  | Replica | streaming |  1 |         0 | nosync: true |
| sql3    | 192.168.83.149  | Replica | streaming |  1 |         0 | nosync: true |
+---------+-----------------+---------+-----------+----+-----------+--------------+
```

You can also visit `http://airflow_ip:7000` (e.g., `http://192.168.83.129:7000`) for the HAProxy Web Dashboard.

#### **Mimic a Failover**

Let's mimic a failure by stopping the Patroni service on the current leader node (e.g., sql1).

**On sql1:**

```bash
sudo systemctl stop patroni
```

Check the status again **on any other Patroni node (e.g., sql2 or sql3)**:

```bash
patronictl -c /usr/patroni/conf/patroni.yml list
```

You should see a new leader has been elected (e.g., sql2):

```
+---------+-----------------+---------+-----------+----+-----------+--------------+
| Member  | Host            | Role    | State     | TL | Lag in MB | Tags         |
+---------+-----------------+---------+-----------+----+-----------+--------------+
| sql1    | 192.168.83.148  | Replica | stopped   |    |   unknown | nosync: true |
| sql2    | 192.168.83.147  | Leader  | running   |  2 |           | nosync: true |
| sql3    | 192.168.83.149  | Replica | streaming |  2 |         0 | nosync: true |
+---------+-----------------+---------+-----------+----+-----------+--------------+
```

Verify that connections to port `5000` now go to the new leader:

```bash
psql -h airflow -d postgres -U postgres -p 5000 -c "select pg_is_in_recovery(),inet_server_addr();"
```

Expected output:

```
 pg_is_in_recovery | inet_server_addr
-------------------+------------------
 f                 | 192.168.83.147
(1 row)
```

Start the Patroni service on the previously stopped node (sql1) to bring it back as a replica:

**On sql1:**

```bash
sudo systemctl start patroni
```

Check the status again:

```bash
patronictl -c /usr/patroni/conf/patroni.yml list
```

You should see `sql1` back in the cluster as a replica:

```
+---------+-----------------+---------+-----------+----+-----------+--------------+
| Member  | Host            | Role    | State     | TL | Lag in MB | Tags         |
+---------+-----------------+---------+-----------+----+-----------+--------------+
| sql1    | 192.168.83.148  | Replica | streaming |  2 |         0 | nosync: true |
| sql2    | 192.168.83.147  | Leader  | running   |  2 |           | nosync: true |
| sql3    | 192.168.83.149  | Replica | streaming |  2 |         0 | nosync: true |
+---------+-----------------+---------+-----------+----+-----------+--------------+
```

#### **Perform a Manual Switchover**

Now, let's perform a switchover to make `sql1` the leader again.

**On any Patroni node (e.g., sql1):**

```bash
patronictl -c /usr/patroni/conf/patroni.yml switchover
```

Follow the prompts. When asked for the candidate, type `sql1` (or your desired candidate):

```
 Current cluster topology
 Cluster: postgres (xxxxxxxxxxxxxxxxxxx) ------+----+-----------+--------------+
 | Member  | Host          | Role    | State     | TL | Lag in MB | Tags         |
 +---------+---------------+---------+-----------+----+-----------+--------------+
 | sql1    | 192.168.83.148 | Replica | streaming |  2 |         0 | nosync: true |
 | sql2    | 192.168.83.147 | Leader  | running   |  2 |           | nosync: true |
 | sql3    | 192.168.83.149 | Replica | streaming |  2 |         0 | nosync: true |
 +---------+---------------+---------+-----------+----+-----------+--------------+
 Primary [sql2]:
 Candidate ['sql1', 'sql3'] []: sql1
 When should the switchover take place (e.g. 2024-09-14T22:59 )  [now]:
 Are you sure you want to switchover cluster postgres, demoting current leader sql2? [y/N]: y
```

After successful switchover, check the cluster status again:

```bash
patronictl -c /usr/patroni/conf/patroni.yml list
```

You should see `sql1` as the new leader:

```
+---------+-----------------+---------+-----------+----+-----------+--------------+
| Member  | Host            | Role    | State     | TL | Lag in MB | Tags         |
+---------+-----------------+---------+-----------+----+-----------+--------------+
| sql1    | 192.168.83.148  | Leader  | running   |  3 |           | nosync: true |
| sql2    | 192.168.83.147  | Replica | streaming |  3 |         0 | nosync: true |
| sql3    | 192.168.83.149  | Replica | streaming |  3 |         0 | nosync: true |
+---------+---------------+---------+-----------+----+-----------+--------------+
```

Now `sql2` will become a replica if it was running. If it was stopped during the switchover, it will come up as a replica once its Patroni service is started.

This completes the customized Patroni setup on your Rocky Linux 9 VMs.

