## Deployment Guide: Zabbix 7 with TimescaleDB on RHEL 9 Servers

This document describes a complete, production-ready deployment of Zabbix 7 using TimescaleDB as the storage backend on separate RHEL 9 hosts. It covers:

1. Prerequisites 2. TimescaleDB Server Setup 3. Zabbix Server Setup 4. Firewall Configuration 5. Final Steps 6. Additional Considerations

---

### 1. Prerequisites

* Two clean RHEL 9 servers:

  * **DB Server** (TimescaleDB)
  * **Zabbix Server** (application & frontend)
* Root or sudo-capable user on both hosts
* Proper DNS or `/etc/hosts` entries so both servers can resolve each other by name or IP
* Time synchronization (e.g., chrony or ntpd) configured on both servers

---

### 2. TimescaleDB Server Setup

#### 2.1 Add Repositories & Install Packages

```bash
# PostgreSQL 16 repo
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql

# TimescaleDB repo
sudo tee /etc/yum.repos.d/timescale_timescaledb.repo << 'EOL'
[timescale_timescaledb]
name=timescale_timescaledb
baseurl=https://packagecloud.io/timescale/timescaledb/el/9/$basearch
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/timescale/timescaledb/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
EOL

# Install
sudo dnf install -y postgresql16-server postgresql16-contrib timescaledb-2-postgresql-16
```

#### 2.2 Initialize & Tune

```bash
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo timescaledb-tune --quiet --yes
```

*TimescaleDB-tune* will suggest `shared_buffers`, `work_mem`, etc., based on system RAM. Review and adjust in `/var/lib/pgsql/16/data/postgresql.conf` if needed.

#### 2.3 Configure Remote Access

* **postgresql.conf** (`/var/lib/pgsql/16/data/postgresql.conf`)

  ```ini
  listen_addresses = '*'
  ```

* **pg\_hba.conf** (`/var/lib/pgsql/16/data/pg_hba.conf`)

  ```ini
  # Allow Zabbix server host
  host    all             all             <ZABBIX_SERVER_IP>/32       scram-sha-256
  ```

#### 2.4 Start the Database

```bash
sudo systemctl enable --now postgresql-16
```

#### 2.5 Create Zabbix Database & User

```bash
sudo -i -u postgres psql << 'EOSQL'
CREATE USER zabbix WITH PASSWORD 'YourStrongPassword';
CREATE DATABASE zabbix WITH OWNER zabbix;
\c zabbix
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EOSQL
```

---

### 3. Zabbix Server Setup

#### 3.1 Add Zabbix Repo & Install

```bash
sudo rpm -Uvh https://repo.zabbix.com/zabbix/7.0/rhel/9/x86_64/zabbix-release-7.0-1.el9.noarch.rpm
sudo dnf install -y \
  zabbix-server-pgsql \
  zabbix-web-pgsql \
  zabbix-nginx-conf \
  zabbix-sql-scripts \
  zabbix-agent
```

#### 3.2 Import Schema

```bash
zcat /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz \
  | psql -h <TIMESCALEDB_IP> -U zabbix zabbix
# Password: YourStrongPassword
```

#### 3.3 Configure Zabbix Server

Edit `/etc/zabbix/zabbix_server.conf`:

```ini
DBHost=<TIMESCALEDB_IP>
DBName=zabbix
DBUser=zabbix
DBPassword=YourStrongPassword
TimescaleDB=1
```

#### 3.4 Configure Web Frontend

* **Zabbix PHP config**: `/etc/zabbix/web/zabbix.conf.php`

  ```php
  <?php
  $DB['TYPE']     = 'POSTGRESQL';
  $DB['SERVER']   = '<TIMESCALEDB_IP>';
  $DB['PORT']     = '5432';
  $DB['DATABASE'] = 'zabbix';
  $DB['USER']     = 'zabbix';
  $DB['PASSWORD'] = 'YourStrongPassword';
  $ZBX_SERVER     = 'localhost';
  $ZBX_SERVER_PORT= '10051';
  $ZBX_SERVER_NAME= 'Zabbix Server';
  ```

* **Nginx**: `/etc/nginx/conf.d/zabbix.conf`

  ```nginx
  server {
      listen       80;
      server_name  your_zabbix_domain_or_ip;
      root         /usr/share/zabbix;
      index        index.php;
  }
  ```

#### 3.5 Start Zabbix Services

```bash
sudo systemctl enable --now zabbix-server zabbix-agent nginx php-fpm
```

---

### 4. Firewall Configuration

* **TimescaleDB Server**

  ```bash
  sudo firewall-cmd --add-service=postgresql --permanent
  sudo firewall-cmd --reload
  ```

* **Zabbix Server**

  ```bash
  sudo firewall-cmd --add-service={http,https} --permanent
  sudo firewall-cmd --add-port=10051/tcp --permanent
  sudo firewall-cmd --reload
  ```

---

### 5. Final Steps

1. Open your browser to `http://<ZABBIX_SERVER_IP>/`
2. Follow the setup wizard. When asked for DB details, use the same credentials as above.
3. Log in with:

   * **User:** Admin
   * **Pass:** zabbix
4. Verify TimescaleDB integration under **Administration → General → TimescaleDB**.

---

### 6. Additional Considerations

#### 6.1 Security & SELinux

* Enable SELinux and configure booleans:

  ```bash
  sudo setsebool -P httpd_can_network_connect_db on
  sudo setsebool -P zabbix_can_network on    # if applicable
  ```
* Use a dedicated firewall zone for Zabbix traffic.

#### 6.2 High-Availability & Pooling

* Deploy Patroni or repmgr for PostgreSQL replication and failover.
* Stand up PgBouncer between Zabbix and TimescaleDB for connection pooling.
* Configure Zabbix proxies or high-availability servers if required.

#### 6.3 TimescaleDB Tuning

* After baseline install, adjust in `postgresql.conf`:

  * `shared_buffers = 25%` of RAM
  * `max_worker_processes` and `max_parallel_workers_per_gather`
* Create hypertables and retention policies:

  ```sql
  SELECT create_hypertable('history', 'clock', if_not_exists => TRUE);
  SELECT add_retention_policy('history', INTERVAL '90 days', if_not_exists => TRUE);
  ```
* Define continuous aggregates for trend data.

#### 6.4 Automation

* Convert these steps into an Ansible role for repeatable deployments.
* Use Terraform for provisioning and inventory management.

#### 6.5 Monitoring & Backups

* Install and configure `pgBackRest` (or Barman) for PITR backups.
* Import a Zabbix template to monitor database health (connections, replication lag, disk space).

#### 6.6 Logging & Auditing

* Centralize logs with rsyslog or the ELK stack.
* Enable PostgreSQL `log_min_duration_statement` to surface slow queries.

---

*End of document.*
