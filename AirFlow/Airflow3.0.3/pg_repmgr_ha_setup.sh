#!/bin/bash

# Interactive script for setting up PostgreSQL High Availability with repmgr
# and SSH key-based authentication between all nodes, for RHEL 9
# Must be run as root or with sudo privileges

set -e

echo "=================================================="
echo "PostgreSQL + repmgr High Availability Setup Script"
echo "        For RHEL 9 - Interactive Edition"
echo "=================================================="
echo
echo "This script will:"
echo "  - Set up SSH key-based authentication for the postgres user between all nodes"
echo "  - Install PostgreSQL and repmgr"
echo "  - Configure basic replication settings"
echo
read -p "Enter number of nodes in your cluster: " NODECOUNT
if ! [[ "$NODECOUNT" =~ ^[0-9]+$ ]] || [ "$NODECOUNT" -lt 2 ]; then
    echo "You must specify at least 2 nodes."
    exit 1
fi

declare -a HOSTS
for ((i=1;i<=NODECOUNT;i++)); do
    read -p "Enter hostname or IP for node #$i: " NODE
    HOSTS+=("$NODE")
done
echo "Nodes: ${HOSTS[*]}"
echo

# Step 1: Ensure SSH key for postgres user exists on all nodes
for HOST in "${HOSTS[@]}"; do
    echo
    echo ">>> Ensuring SSH key exists for postgres@$HOST ..."
    ssh "$HOST" "sudo -u postgres bash -c 'mkdir -p ~/.ssh && chmod 700 ~/.ssh; [ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 4096 -N \"\" -f ~/.ssh/id_rsa'"
done

# Step 2: Collect all public keys
declare -a PUBKEYS
echo
echo ">>> Collecting public keys from all nodes..."
for HOST in "${HOSTS[@]}"; do
    PUBKEY=$(ssh "$HOST" "sudo -u postgres cat ~/.ssh/id_rsa.pub")
    PUBKEYS+=("$PUBKEY")
done

# Step 3: Distribute all public keys to all nodes (authorized_keys)
echo
echo ">>> Distributing authorized_keys to all nodes..."
for HOST in "${HOSTS[@]}"; do
    TMPFILE=$(mktemp)
    for KEY in "${PUBKEYS[@]}"; do
        echo "$KEY" >> "$TMPFILE"
    done
    sort -u "$TMPFILE" -o "$TMPFILE"
    cat "$TMPFILE" | ssh "$HOST" "sudo -u postgres tee ~/.ssh/authorized_keys > /dev/null"
    ssh "$HOST" "sudo -u postgres chmod 600 ~/.ssh/authorized_keys"
    rm "$TMPFILE"
done

# Step 4: Test SSH connectivity
echo
echo ">>> Testing SSH connectivity between nodes (as postgres user)..."
for FROM in "${HOSTS[@]}"; do
    for TO in "${HOSTS[@]}"; do
        if [ "$FROM" != "$TO" ]; then
            echo -n "From $FROM to $TO: "
            ssh "$FROM" "sudo -u postgres ssh -o BatchMode=yes -o StrictHostKeyChecking=no $TO hostname" && echo "OK" || echo "FAILED"
        fi
    done
done

# Step 5: Install PostgreSQL and repmgr on all nodes
echo
echo ">>> Installing PostgreSQL and repmgr on all nodes..."
for HOST in "${HOSTS[@]}"; do
    ssh "$HOST" "sudo dnf install -y postgresql-server postgresql-contrib repmgr"
done

echo
read -p "Which node will be the initial primary? (enter the hostname/IP): " PRIMARY_NODE

# Step 6: Initialize and configure PostgreSQL and repmgr
echo
echo ">>> Initializing and configuring PostgreSQL cluster ..."
for HOST in "${HOSTS[@]}"; do
    echo "Configuring $HOST ..."
    ssh "$HOST" "sudo postgresql-setup --initdb"
    ssh "$HOST" "sudo systemctl enable --now postgresql"
done

# Step 7: Create repmgr user and database on primary
echo
echo ">>> Creating repmgr user and database on primary node ($PRIMARY_NODE)..."
read -s -p "Enter password for repmgr user: " REPMGRPASS
echo
ssh "$PRIMARY_NODE" "sudo -u postgres psql -c \"CREATE USER repmgr WITH SUPERUSER PASSWORD '$REPMGRPASS';\""
ssh "$PRIMARY_NODE" "sudo -u postgres psql -c \"CREATE DATABASE repmgr OWNER repmgr;\""

# Step 8: Configure postgresql.conf and pg_hba.conf on all nodes
echo
echo ">>> Configuring postgresql.conf and pg_hba.conf on all nodes..."
for HOST in "${HOSTS[@]}"; do
    # Get the cluster subnet for pg_hba.conf
    CLUSTER_NET="$(echo "${HOSTS[0]}" | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}')/24"
    ssh "$HOST" "sudo sed -i \"/^#listen_addresses/s/.*/listen_addresses = '*'/
                  /^#wal_level/s/.*/wal_level = replica/
                  /^#max_wal_senders/s/.*/max_wal_senders = 10/
                  /^#wal_keep_size/s/.*/wal_keep_size = 128/
                  /^#archive_mode/s/.*/archive_mode = on/
                  /^#archive_command/s|.*|archive_command = 'cd .'/ # minimal, user to customize
                  /^#hot_standby/s/.*/hot_standby = on/
                  " /var/lib/pgsql/data/postgresql.conf"
    # Setup basic replication access
    ssh "$HOST" "echo \"host    replication    repmgr    $CLUSTER_NET    md5
host    repmgr         repmgr    $CLUSTER_NET    md5\" | sudo tee -a /var/lib/pgsql/data/pg_hba.conf"
    ssh "$HOST" "sudo systemctl restart postgresql"
done

# Step 9: Configure repmgr.conf on all nodes
echo
echo ">>> Configuring repmgr.conf on all nodes..."
for i in "${!HOSTS[@]}"; do
    NODEID=$((i+1))
    NODENAME="node$NODEID"
    HOSTADDR="${HOSTS[$i]}"
    ssh "$HOSTADDR" "sudo bash -c 'cat > /etc/repmgr/14/repmgr.conf <<EOF
node_id=$NODEID
node_name=\"$NODENAME\"
conninfo=\"host=$HOSTADDR user=repmgr dbname=repmgr password=$REPMGRPASS\"
data_directory='/var/lib/pgsql/data'
log_file='/var/log/repmgr/repmgr.log'
EOF
'"
done

# Step 10: Register primary and clone standbys
echo
echo ">>> Registering primary node with repmgr..."
ssh "$PRIMARY_NODE" "sudo -u postgres repmgr -f /etc/repmgr/14/repmgr.conf primary register"

for HOST in "${HOSTS[@]}"; do
    if [ "$HOST" != "$PRIMARY_NODE" ]; then
        echo ">>> Cloning $HOST from primary and registering as standby..."
        ssh "$HOST" "sudo systemctl stop postgresql"
        ssh "$HOST" "sudo -u postgres repmgr -h $PRIMARY_NODE -U repmgr -d repmgr -f /etc/repmgr/14/repmgr.conf standby clone"
        ssh "$HOST" "sudo systemctl start postgresql"
        ssh "$HOST" "sudo -u postgres repmgr -f /etc/repmgr/14/repmgr.conf standby register"
    fi
done

# Step 11: Enable and start repmgrd
echo
echo ">>> Enabling and starting repmgrd on all nodes..."
for HOST in "${HOSTS[@]}"; do
    ssh "$HOST" "sudo systemctl enable --now repmgrd"
done

echo
echo "==========================================================="
echo "PostgreSQL HA with repmgr setup is complete!"
echo "Check cluster status with: repmgr -f /etc/repmgr/14/repmgr.conf cluster show"
echo "==========================================================="