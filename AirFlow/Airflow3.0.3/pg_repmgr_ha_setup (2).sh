#!/bin/bash

# Interactive script for setting up PostgreSQL HA cluster with repmgr on multiple RHEL 9 nodes
# Features:
# - SSH key-based setup for the postgres user
# - Cluster network and archiving config (advanced tuning options)
# - Works with custom PostgreSQL/repmgr versions or paths
#
# Run as root or with sudo.
# You need passwordless SSH access between all cluster nodes for the postgres user.

set -euo pipefail

DEFAULT_PG_VERSION="15"
DEFAULT_REPMGR_VERSION="5"
DEFAULT_PG_DATA="/var/lib/pgsql/15/data"
DEFAULT_REPMGR_CONF="/etc/repmgr/15/repmgr.conf"
DEFAULT_ARCHIVE_PATH="/var/lib/pgsql/wal_archive"
DEFAULT_NETWORK="192.168.10.0/24"
DEFAULT_PORT="5432"
DEFAULT_REPLICATION_SLOTS="10"
DEFAULT_WAL_KEEP_SIZE="512"
DEFAULT_ARCHIVE_TIMEOUT="60"
DEFAULT_ARCHIVE_COMMAND="cp %p $DEFAULT_ARCHIVE_PATH/%f"
DEFAULT_MAX_CONNECTIONS="200"
DEFAULT_SHARED_BUFFERS="2GB"
DEFAULT_EFFECTIVE_CACHE_SIZE="6GB"
DEFAULT_MAINTENANCE_WORK_MEM="512MB"
DEFAULT_WORK_MEM="16MB"
DEFAULT_LOG_MIN_DURATION_STATEMENT="500"

echo "=================================================================="
echo "PostgreSQL + repmgr High Availability Cluster Setup for RHEL 9"
echo "=================================================================="
echo
echo "This script will:"
echo "- Set up SSH key-based authentication for postgres user"
echo "- Configure advanced PostgreSQL and repmgr settings"
echo "- Enable archiving and advanced network configs"
echo "- Prepare nodes for streaming replication and HA"
echo
echo ">>> NOTE: You must run this script on each node, and provide all node hostnames/IPs. <<<"
echo

# Ask for cluster details
read -p "PostgreSQL version [${DEFAULT_PG_VERSION}]: " PG_VERSION
: "${PG_VERSION:=$DEFAULT_PG_VERSION}"

read -p "repmgr version [${DEFAULT_REPMGR_VERSION}]: " REPMGR_VERSION
: "${REPMGR_VERSION:=$DEFAULT_REPMGR_VERSION}"

read -p "Data directory [${DEFAULT_PG_DATA}]: " PGDATA
: "${PGDATA:=$DEFAULT_PG_DATA}"

read -p "Archive directory [${DEFAULT_ARCHIVE_PATH}]: " ARCHIVE_DIR
: "${ARCHIVE_DIR:=$DEFAULT_ARCHIVE_PATH}"

read -p "Cluster network (CIDR) [${DEFAULT_NETWORK}]: " CLUSTER_NET
: "${CLUSTER_NET:=$DEFAULT_NETWORK}"

read -p "PostgreSQL listen port [${DEFAULT_PORT}]: " PGPORT
: "${PGPORT:=$DEFAULT_PORT}"

read -p "How many nodes in your cluster? [3]: " NODE_COUNT
: "${NODE_COUNT:=3}"

echo "Enter node hostnames or IPs (one per line):"
NODES=()
for i in $(seq 1 $NODE_COUNT); do
  read -p "  Node $i: " N
  NODES+=("$N")
done

echo
echo "Configuring for nodes:"
for i in "${!NODES[@]}"; do
  echo "  Node $((i+1)): ${NODES[$i]}"
done
echo

# Advanced PostgreSQL tuning
echo "------ Advanced PostgreSQL Settings ------"
read -p "max_connections [${DEFAULT_MAX_CONNECTIONS}]: " MAX_CONNECTIONS
: "${MAX_CONNECTIONS:=$DEFAULT_MAX_CONNECTIONS}"
read -p "shared_buffers [${DEFAULT_SHARED_BUFFERS}]: " SHARED_BUFFERS
: "${SHARED_BUFFERS:=$DEFAULT_SHARED_BUFFERS}"
read -p "effective_cache_size [${DEFAULT_EFFECTIVE_CACHE_SIZE}]: " EFFECTIVE_CACHE_SIZE
: "${EFFECTIVE_CACHE_SIZE:=$DEFAULT_EFFECTIVE_CACHE_SIZE}"
read -p "maintenance_work_mem [${DEFAULT_MAINTENANCE_WORK_MEM}]: " MAINTENANCE_WORK_MEM
: "${MAINTENANCE_WORK_MEM:=$DEFAULT_MAINTENANCE_WORK_MEM}"
read -p "work_mem [${DEFAULT_WORK_MEM}]: " WORK_MEM
: "${WORK_MEM:=$DEFAULT_WORK_MEM}"
read -p "log_min_duration_statement [${DEFAULT_LOG_MIN_DURATION_STATEMENT}]: " LOG_MIN_DURATION_STATEMENT
: "${LOG_MIN_DURATION_STATEMENT:=$DEFAULT_LOG_MIN_DURATION_STATEMENT}"

# Advanced archiving/network
echo "------ Advanced Archiving/Replication Settings ------"
read -p "max_wal_senders [${DEFAULT_REPLICATION_SLOTS}]: " MAX_WAL_SENDERS
: "${MAX_WAL_SENDERS:=$DEFAULT_REPLICATION_SLOTS}"
read -p "wal_keep_size (MB) [${DEFAULT_WAL_KEEP_SIZE}]: " WAL_KEEP_SIZE
: "${WAL_KEEP_SIZE:=$DEFAULT_WAL_KEEP_SIZE}"
read -p "archive_timeout (s) [${DEFAULT_ARCHIVE_TIMEOUT}]: " ARCHIVE_TIMEOUT
: "${ARCHIVE_TIMEOUT:=$DEFAULT_ARCHIVE_TIMEOUT}"
read -p "archive_command [${DEFAULT_ARCHIVE_COMMAND}]: " ARCHIVE_COMMAND
: "${ARCHIVE_COMMAND:=$DEFAULT_ARCHIVE_COMMAND}"

echo
echo "----- SSH Key Setup (for postgres user) -----"
echo "Ensuring SSH keys are generated for postgres user..."
if ! sudo -i -u postgres test -f ~/.ssh/id_rsa; then
  sudo -i -u postgres mkdir -p ~/.ssh
  sudo -i -u postgres chmod 700 ~/.ssh
  sudo -i -u postgres ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
fi

echo "Distributing public key to cluster nodes..."
PUBKEY=$(sudo -i -u postgres cat ~/.ssh/id_rsa.pub)
for NODE in "${NODES[@]}"; do
  if [ "$NODE" != "$(hostname -s)" ] && [ "$NODE" != "$(hostname -I | awk '{print $1}')" ]; then
    ssh "$NODE" "sudo -i -u postgres mkdir -p ~/.ssh; sudo -i -u postgres chmod 700 ~/.ssh"
    echo "$PUBKEY" | ssh "$NODE" "sudo -i -u postgres tee -a ~/.ssh/authorized_keys"
    ssh "$NODE" "sudo -i -u postgres chmod 600 ~/.ssh/authorized_keys"
  fi
done

echo "Testing SSH connectivity between all nodes (as postgres user):"
for FROM in "${NODES[@]}"; do
  for TO in "${NODES[@]}"; do
    if [ "$FROM" != "$TO" ]; then
      echo -n "  From $FROM to $TO: "
      ssh "$FROM" "sudo -i -u postgres ssh -o StrictHostKeyChecking=no -o BatchMode=yes $TO echo OK" || echo "FAILED"
    fi
  done
done

echo "----- PostgreSQL Configuration Tuning -----"
PGCONF="$PGDATA/postgresql.conf"
PGHBA="$PGDATA/pg_hba.conf"

sudo -u postgres mkdir -p "$ARCHIVE_DIR"
sudo -u postgres chmod 700 "$ARCHIVE_DIR"

sudo sed -i "/^#*listen_addresses/d" "$PGCONF"
sudo sed -i "/^#*port[ ]*=/d" "$PGCONF"
echo "listen_addresses = '*'" | sudo tee -a "$PGCONF"
echo "port = $PGPORT" | sudo tee -a "$PGCONF"
echo "max_connections = $MAX_CONNECTIONS" | sudo tee -a "$PGCONF"
echo "shared_buffers = $SHARED_BUFFERS" | sudo tee -a "$PGCONF"
echo "effective_cache_size = $EFFECTIVE_CACHE_SIZE" | sudo tee -a "$PGCONF"
echo "maintenance_work_mem = $MAINTENANCE_WORK_MEM" | sudo tee -a "$PGCONF"
echo "work_mem = $WORK_MEM" | sudo tee -a "$PGCONF"
echo "log_min_duration_statement = $LOG_MIN_DURATION_STATEMENT" | sudo tee -a "$PGCONF"
echo "wal_level = replica" | sudo tee -a "$PGCONF"
echo "max_wal_senders = $MAX_WAL_SENDERS" | sudo tee -a "$PGCONF"
echo "wal_keep_size = $WAL_KEEP_SIZE" | sudo tee -a "$PGCONF"
echo "hot_standby = on" | sudo tee -a "$PGCONF"
echo "archive_mode = on" | sudo tee -a "$PGCONF"
echo "archive_timeout = $ARCHIVE_TIMEOUT" | sudo tee -a "$PGCONF"
echo "archive_command = '$ARCHIVE_COMMAND'" | sudo tee -a "$PGCONF"
echo "primary_conninfo = 'application_name=%h user=repmgr password=YOUR_REPMGR_PASSWORD'" | sudo tee -a "$PGCONF"
echo "tcp_keepalives_idle = 60" | sudo tee -a "$PGCONF"
echo "tcp_keepalives_interval = 10" | sudo tee -a "$PGCONF"
echo "tcp_keepalives_count = 10" | sudo tee -a "$PGCONF"
echo "log_connections = on" | sudo tee -a "$PGCONF"
echo "log_disconnections = on" | sudo tee -a "$PGCONF"
echo "log_line_prefix = '%m [%p] %q%u@%d '" | sudo tee -a "$PGCONF"

# Advanced network config
echo "ssl = on" | sudo tee -a "$PGCONF"
echo "# Adjust and configure SSL certificates as needed" | sudo tee -a "$PGCONF"

echo "Configuring pg_hba.conf for replication and repmgr access..."
echo "host    replication    repmgr    $CLUSTER_NET    md5" | sudo tee -a "$PGHBA"
echo "host    repmgr         repmgr    $CLUSTER_NET    md5" | sudo tee -a "$PGHBA"
echo "host    all            all       $CLUSTER_NET    md5" | sudo tee -a "$PGHBA"

echo "Restarting PostgreSQL service..."
sudo systemctl restart postgresql-$PG_VERSION

echo "----- repmgr Configuration -----"
REPMGRCONF="/etc/repmgr/$PG_VERSION/repmgr.conf"
sudo mkdir -p "/etc/repmgr/$PG_VERSION"
sudo touch "$REPMGRCONF"
sudo chown postgres:postgres "$REPMGRCONF"

read -p "Enter this node's unique node_id [1]: " NODE_ID
: "${NODE_ID:=1}"
read -p "Enter this node's unique node_name [node${NODE_ID}]: " NODE_NAME
: "${NODE_NAME:=node${NODE_ID}}"
read -p "repmgr database password (will be stored in config): " -s REPMGR_PW
echo

echo "node_id=$NODE_ID" | sudo tee "$REPMGRCONF"
echo "node_name='$NODE_NAME'" | sudo tee -a "$REPMGRCONF"
echo "conninfo='host=$(hostname -I | awk '{print $1}') user=repmgr dbname=repmgr password=$REPMGR_PW port=$PGPORT'" | sudo tee -a "$REPMGRCONF"
echo "data_directory='$PGDATA'" | sudo tee -a "$REPMGRCONF"
echo "log_file='/var/log/repmgr/repmgr.log'" | sudo tee -a "$REPMGRCONF"
echo "use_replication_slots=yes" | sudo tee -a "$REPMGRCONF"
echo "failover=automatic" | sudo tee -a "$REPMGRCONF"
echo "promote_command='repmgr standby promote -f $REPMGRCONF --log-to-file'" | sudo tee -a "$REPMGRCONF"
echo "follow_command='repmgr standby follow -f $REPMGRCONF --log-to-file --upstream-node-id=%n'" | sudo tee -a "$REPMGRCONF"
echo "reconnect_attempts=6" | sudo tee -a "$REPMGRCONF"
echo "reconnect_interval=10" | sudo tee -a "$REPMGRCONF"
echo "monitoring_history=yes" | sudo tee -a "$REPMGRCONF"
echo "event_notification_command='/usr/bin/logger repmgr event: %e %n %m'" | sudo tee -a "$REPMGRCONF"
echo "log_level=INFO" | sudo tee -a "$REPMGRCONF"
echo "# Add witness node config here if using one" | sudo tee -a "$REPMGRCONF"

echo "Creating repmgr user and database (on primary node only)..."
sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'repmgr') THEN CREATE ROLE repmgr WITH SUPERUSER LOGIN PASSWORD '$REPMGR_PW'; END IF; END \$\$;"
sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'repmgr') THEN CREATE DATABASE repmgr OWNER repmgr; END IF; END \$\$;"

echo "Register your primary node with repmgr (on the primary only):"
echo "  sudo -u postgres repmgr -f $REPMGRCONF primary register"

echo "On standby nodes:"
echo "  sudo -u postgres repmgr -h <primary_ip> -U repmgr -d repmgr -f $REPMGRCONF standby clone"
echo "  sudo systemctl start postgresql-$PG_VERSION"
echo "  sudo -u postgres repmgr -f $REPMGRCONF standby register"

echo
echo "Enable and start repmgrd on all nodes:"
echo "  sudo systemctl enable repmgrd-$PG_VERSION"
echo "  sudo systemctl start repmgrd-$PG_VERSION"
echo
echo "Check cluster status:"
echo "  sudo -u postgres repmgr -f $REPMGRCONF cluster show"
echo
echo "All done! Tune further as needed for your environment."