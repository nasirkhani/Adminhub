# PostgreSQL High Availability with repmgr on 3-node RHEL 9 Cluster

## 1. Prerequisites

- Three RHEL 9 nodes: `node1`, `node2`, `node3` with static IPs.
- PostgreSQL 14+ installed on all nodes.
- All nodes can reach each other via SSH (preferably with key-based auth for `postgres` user).
- Synchronized clocks (e.g., via `chronyd`).

---

## 2. Install repmgr

On **ALL nodes**:
```bash
sudo dnf install epel-release
sudo dnf install repmgr
```

---

## 3. Configure PostgreSQL for Replication

### a. Edit `/var/lib/pgsql/data/postgresql.conf`

Set the following parameters (adjust for your PG version):
```
listen_addresses = '*'
wal_level = replica
max_wal_senders = 10
wal_keep_size = 128
archive_mode = on
archive_command = 'cp %p /var/lib/pgsql/wal_archive/%f'
hot_standby = on
```

### b. Edit `/var/lib/pgsql/data/pg_hba.conf`

Add lines for replication:
```
host    replication    repmgr    192.168.1.0/24    md5
host    repmgr         repmgr    192.168.1.0/24    md5
```
Replace `192.168.1.0/24` with your subnet.

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## 4. Create repmgr User and Database

On **node1 (primary)**:
```bash
sudo -u postgres psql
```
```sql
CREATE USER repmgr WITH SUPERUSER PASSWORD 'yourpassword';
CREATE DATABASE repmgr OWNER repmgr;
```

---

## 5. Configure `repmgr.conf` on All Nodes

Example for **node1** (`/etc/repmgr/14/repmgr.conf`):
```
node_id=1
node_name='node1'
conninfo='host=node1_ip user=repmgr dbname=repmgr password=yourpassword'
data_directory='/var/lib/pgsql/data'
log_file='/var/log/repmgr/repmgr.log'
```
Do similarly for node2 (node_id=2, node_name='node2', host=node2_ip) and node3.

---

## 6. Register Primary Node

On **node1**:
```bash
repmgr -f /etc/repmgr/14/repmgr.conf primary register
```

---

## 7. Clone Standby Nodes

On **node2** and **node3**:
```bash
repmgr -h node1_ip -U repmgr -d repmgr -f /etc/repmgr/14/repmgr.conf standby clone
sudo systemctl start postgresql
repmgr -f /etc/repmgr/14/repmgr.conf standby register
```

---

## 8. Verify Cluster

On any node:
```bash
repmgr -f /etc/repmgr/14/repmgr.conf cluster show
```

---

## 9. Enable and Start repmgrd Daemon

On **ALL nodes**:
```bash
sudo systemctl enable repmgrd
sudo systemctl start repmgrd
```

---

## 10. Test Failover

Stop PostgreSQL on node1 and watch node2 or node3 promote to primary.

---

## 11. Rejoin Failed Node

After a failover, re-clone or re-attach the failed node as a standby.

---

## Tips

- Adjust firewall rules to allow PostgreSQL and repmgr ports.
- Consider using a load balancer or virtual IP for automatic failover handling.
- repmgr can manage witness nodes for split-brain avoidance.

---

## References

- [repmgr Documentation](https://repmgr.org/docs/)
- [PostgreSQL Replication](https://www.postgresql.org/docs/current/warm-standby.html)