## Production-Ready Installation Guide: PostgreSQL 16 with TimescaleDB on RHEL 9

This document provides a streamlined, idempotent, and secure process for installing PostgreSQL 16 alongside TimescaleDB on RHEL 9. It includes best practices for repository management, cluster initialization, security hardening, and optional optimizations.

---

### Prerequisites

* **Operating System**: RHEL 9, fully updated.
* **SELinux**: Enforcing (default). We will ensure proper port and policy configurations.
* **FirewallD**: Installed and active (default on RHEL).

```bash
sudo dnf update -y
```

---

### 1. Enable Repositories (Idempotent)

```bash
# Import PGDG repository if not already present
data="$(rpm -qa | grep -w pgdg-redhat-repo)"
if [ -z "$data" ]; then
  sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
fi

# Disable built-in PostgreSQL module
sudo dnf -qy module disable postgresql
```

> **Rationale:**
>
> * Checks for existing PGDG repo to avoid redundant downloads.
> * Disables Red Hat’s default module to ensure usage of the latest PGDG builds.

---

### 2. Install PostgreSQL 16 & Contrib

```bash
sudo dnf install -y postgresql16-server postgresql16-contrib
```

> **Tip:** Pin exact package versions for deterministic installs, e.g., `postgresql16-server-16.1-1.el9`.

---

### 3. Initialize, Enable & Start Service

```bash
DATA_DIR=/var/lib/pgsql/16/data
# Initialize only if directory is empty
test -d "$DATA_DIR" && [ -z "$(ls -A $DATA_DIR)" ] && \
  sudo /usr/pgsql-16/bin/postgresql-16-setup initdb

# Enable and start in one step
sudo systemctl enable --now postgresql-16
```

> **Rationale:** Guards against re-initializing an existing cluster and ensures atomic enable/start.

---

### 4. Add TimescaleDB Repository

```bash
REPO_FILE=/etc/yum.repos.d/timescale_timescaledb.repo
if [ ! -f "$REPO_FILE" ]; then
  sudo tee "$REPO_FILE" > /dev/null <<'EOL'
[timescale_timescaledb]
name=timescale_timescaledb
baseurl=https://packagecloud.io/timescale/timescaledb/el/9/$basearch
repo_gpgcheck=1
gpgcheck=1
enabled=1
gpgkey=https://packagecloud.io/timescale/timescaledb/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
EOL
  sudo rpm --import https://packagecloud.io/timescale/timescaledb/gpgkey
fi

sudo dnf makecache
```

> **Security:** Enables GPG verification for repository metadata and packages.

---

### 5. Install TimescaleDB Extension

```bash
sudo dnf install -y timescaledb-2-postgresql-16
```

---

### 6. Auto-Tune Configuration & Restart

```bash
# Non-interactive tuning
timescaledb-tune --pg-config=/usr/pgsql-16/bin/pg_config --yes
sudo systemctl restart postgresql-16
```

> **Tip:** Review changes in `postgresql.conf.d/timescaledb.conf` before applying in production.

---

### 7. Create & Prepare TSDB Database

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'EOF'
CREATE DATABASE IF NOT EXISTS tsdb;
\c tsdb
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EOF
```

> **Safety:** Uses `IF NOT EXISTS` and `ON_ERROR_STOP` to make scripting robust.

---

### 8. Verify Installation

```bash
sudo -u postgres psql -d tsdb -c \
  "SELECT name, default_version, installed_version \
   FROM pg_available_extensions \
   WHERE name = 'timescaledb';"
```

You should see matching `default_version` and `installed_version` (e.g., `2.14.1`).

---

### 9. Firewall & SELinux Configuration

```bash
# FirewallD: Open PostgreSQL port
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --reload

# SELinux: Allow PostgreSQL port (ignoring duplicate errors)
sudo semanage port -a -t postgresql_port_t -p tcp 5432 || true
```

> **Note:** Ensures remote connectivity while maintaining policy enforcement.

---

### 10. Optional: Sample Hypertable

```bash
sudo -u postgres psql -d tsdb <<'EOF'
CREATE TABLE IF NOT EXISTS conditions (
    time        TIMESTAMPTZ       NOT NULL,
    location    TEXT              NOT NULL,
    temperature DOUBLE PRECISION
);
SELECT create_hypertable('conditions', 'time', if_not_exists => TRUE);
INSERT INTO conditions VALUES (NOW(), 'office', 70.0);
SELECT * FROM conditions LIMIT 5;
EOF
```

Provides a quick test of TimescaleDB functionality.

---

## Further Recommendations

1. **Automation & Infrastructure as Code**: Implement this guide as a single Bash script, Ansible role, or Terraform provisioner for repeatability.
2. **Backups**: Use `pgBackRest` or `Barman` for reliable, continuous archiving and point-in-time recovery.
3. **Monitoring**: Deploy solutions like `Prometheus` + `timescaledb-prometheus` or `pgwatch2` for metrics collection and alerting.
4. **High Availability**: Consider `Patroni` or `repmgr` for automatic failover and cluster management.
5. **Performance Tuning**: Adjust memory and WAL settings (`shared_buffers`, `work_mem`, `max_connections`, `wal_compression`) based on workload and hardware.
