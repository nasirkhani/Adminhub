#!/bin/bash

# Interactive PostgreSQL High Availability (HA) cluster setup with repmgr and SSH key-based auth for RHEL 9 nodes

# This script assumes:
#  - You run it as root or with sudo privileges on ONE node
#  - You have password SSH access to all nodes as root
#  - All nodes run RHEL 9 with PostgreSQL and repmgr installed (or will be installed by the script)
#  - Network, firewall, and SELinux configs are compatible (may require manual adjustments)
#  - Intended for educational use – adjust for production

set -e

PG_VER_DEFAULT="15"
REPMGR_VER_DEFAULT="5"
DATA_DIR_DEFAULT="/var/lib/pgsql/data"
ARCHIVE_DIR_DEFAULT="/var/lib/pgsql/wal_archive"

echo "========== PostgreSQL + repmgr HA Cluster Setup =========="

# 1. Collect cluster details
read -p "Enter comma-separated hostnames or IPs for all nodes (e.g. 192.168.1.10,192.168.1.11,192.168.1.12): " NODES_CSV
IFS=',' read -ra NODES <<< "$NODES_CSV"

echo "Detected nodes: ${NODES[*]}"
NODE_COUNT=${#NODES[@]}

read -p "Which node should be primary? Enter hostname or IP from above: " PRIMARY_NODE

read -p "PostgreSQL version to use [${PG_VER_DEFAULT}]: " PG_VER
PG_VER="${PG_VER:-$PG_VER_DEFAULT}"

read -p "repmgr version to use [${REPMGR_VER_DEFAULT}]: " REPMGR_VER
REPMGR_VER="${REPMGR_VER:-$REPMGR_VER_DEFAULT}"

read -p "PG data directory [${DATA_DIR_DEFAULT}]: " DATA_DIR
DATA_DIR="${DATA_DIR:-$DATA_DIR_DEFAULT}"

read -p "WAL archive directory [${ARCHIVE_DIR_DEFAULT}]: " ARCHIVE_DIR
ARCHIVE_DIR="${ARCHIVE_DIR:-$ARCHIVE_DIR_DEFAULT}"

read -p "Cluster network/subnet (e.g. 192.168.1.0/24): " CLUSTER_NET

read -p "Password for repmgr PostgreSQL user: " -s REPMGR_PW
echo

# 2. Install PostgreSQL & repmgr (and dependencies) on all nodes
echo "== Installing PostgreSQL and repmgr on all nodes =="
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "dnf install -y epel-release && dnf install -y postgresql-server postgresql-contrib repmgr"
done

# 3. Enable and initialize PostgreSQL on each node
echo "== Initializing PostgreSQL cluster on all nodes =="
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "mkdir -p $ARCHIVE_DIR && chown postgres:postgres $ARCHIVE_DIR"
  ssh root@"$NODE" "sudo -u postgres /usr/bin/initdb -D $DATA_DIR || true"
  ssh root@"$NODE" "systemctl enable --now postgresql"
done

sleep 3

# 4. Generate SSH keys for postgres user, collect, and distribute
echo "== Setting up SSH key-based authentication for postgres user =="
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "sudo -u postgres mkdir -p ~/.ssh && sudo -u postgres chmod 700 ~/.ssh"
  ssh root@"$NODE" "sudo -u postgres bash -c 'if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -t rsa -b 4096 -N \"\" -f ~/.ssh/id_rsa; fi'"
done

# Collect all keys and assemble authorized_keys
ALL_PUBKEYS=""
for NODE in "${NODES[@]}"; do
  PUBKEY=$(ssh root@"$NODE" "sudo -u postgres cat ~/.ssh/id_rsa.pub")
  ALL_PUBKEYS="$ALL_PUBKEYS$PUBKEY"$'\n'
done

for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "echo \"$ALL_PUBKEYS\" | sudo -u postgres tee ~/.ssh/authorized_keys > /dev/null"
  ssh root@"$NODE" "sudo -u postgres chmod 600 ~/.ssh/authorized_keys"
done

# 5. Configure postgresql.conf and pg_hba.conf for replication and archiving
echo "== Configuring PostgreSQL for replication and archiving =="
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "sudo -u postgres sed -i \"/^#*listen_addresses/s/.*/listen_addresses = '*'/
    /^#*wal_level/s/.*/wal_level = replica/
    /^#*max_wal_senders/s/.*/max_wal_senders = 10/
    /^#*wal_keep_size/s/.*/wal_keep_size = 256/
    /^#*archive_mode/s/.*/archive_mode = on/
    /^#*archive_command/s?.*?archive_command = 'cp %p $ARCHIVE_DIR/%f'?
    /^#*hot_standby/s/.*/hot_standby = on/
    \" $DATA_DIR/postgresql.conf"
  
  # Add/replace necessary lines for network access
  ssh root@"$NODE" "grep -q 'repmgr' $DATA_DIR/pg_hba.conf || echo \"
host    replication    repmgr    $CLUSTER_NET    md5
host    repmgr         repmgr    $CLUSTER_NET    md5
\" >> $DATA_DIR/pg_hba.conf"
done

# 6. Restart PostgreSQL to apply configs
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "systemctl restart postgresql"
done

# 7. Create repmgr user & database on primary
echo "== Creating repmgr user and database on primary ($PRIMARY_NODE) =="
ssh root@"$PRIMARY_NODE" "sudo -u postgres psql -c \"CREATE USER repmgr WITH SUPERUSER PASSWORD '$REPMGR_PW';\""
ssh root@"$PRIMARY_NODE" "sudo -u postgres psql -c \"CREATE DATABASE repmgr OWNER repmgr;\""

# 8. Write repmgr.conf on all nodes
echo "== Writing repmgr.conf on all nodes =="
NODE_ID=1
for NODE in "${NODES[@]}"; do
  cat <<EOF | ssh root@"$NODE" "cat > /etc/repmgr/${PG_VER}/repmgr.conf"
node_id=$NODE_ID
node_name='node$NODE_ID'
conninfo='host=$NODE user=repmgr dbname=repmgr password=$REPMGR_PW'
data_directory='$DATA_DIR'
log_file='/var/log/repmgr/repmgr.log'
pg_bindir='/usr/pgsql-${PG_VER}/bin'
EOF
  NODE_ID=$((NODE_ID+1))
done

# 9. Register primary node with repmgr
echo "== Registering primary node with repmgr =="
ssh root@"$PRIMARY_NODE" "repmgr -f /etc/repmgr/${PG_VER}/repmgr.conf primary register"

# 10. Clone and register standby nodes
echo "== Cloning and registering standby nodes =="
NODE_ID=1
for NODE in "${NODES[@]}"; do
  if [[ "$NODE" == "$PRIMARY_NODE" ]]; then
    NODE_ID=$((NODE_ID+1))
    continue
  fi
  echo "Cloning standby on $NODE from primary ($PRIMARY_NODE)..."
  ssh root@"$NODE" "sudo -u postgres pg_ctl stop -D $DATA_DIR || true"
  ssh root@"$NODE" "rm -rf $DATA_DIR/*"
  ssh root@"$NODE" "repmgr -h $PRIMARY_NODE -U repmgr -d repmgr -f /etc/repmgr/${PG_VER}/repmgr.conf standby clone"
  ssh root@"$NODE" "systemctl start postgresql"
  ssh root@"$NODE" "repmgr -f /etc/repmgr/${PG_VER}/repmgr.conf standby register"
  NODE_ID=$((NODE_ID+1))
done

# 11. Start repmgrd on all nodes
echo "== Enabling and starting repmgrd on all nodes =="
for NODE in "${NODES[@]}"; do
  ssh root@"$NODE" "systemctl enable --now repmgrd"
done

# 12. Cluster status check
echo "== Final cluster status =="
ssh root@"$PRIMARY_NODE" "repmgr -f /etc/repmgr/${PG_VER}/repmgr.conf cluster show"

echo "========== PostgreSQL HA cluster setup complete =========="
echo "Validate cluster status and test failover as needed."