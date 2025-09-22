## **Download on Windows (Git Bash)**

```bash
# In Git Bash on Windows
cd /c/Users/m_fereidoon

# Download etcd v3.4.34
curl -L https://storage.googleapis.com/etcd/v3.4.34/etcd-v3.4.34-linux-amd64.tar.gz -o etcd-v3.4.34-linux-amd64.tar.gz

# Verify download
ls -la etcd-v3.4.34-linux-amd64.tar.gz
```

## **Transfer and Install (Your Original Process)**

**Transfer to VMs:**
```bash
# Copy to all PostgreSQL VMs (adjust IPs as needed)
scp etcd-v3.4.34-linux-amd64.tar.gz rocky@10.101.20.204:/tmp/
scp etcd-v3.4.34-linux-amd64.tar.gz rocky@10.101.20.166:/tmp/
scp etcd-v3.4.34-linux-amd64.tar.gz rocky@10.101.20.137:/tmp/
```

**On each VM - follow your original guideline exactly:**
```bash
# Complete removal first
sudo systemctl stop etcd patroni 2>/dev/null
sudo rm -f /usr/local/bin/etcd*
sudo rm -rf /var/lib/etcd
sudo rm -rf /etc/etcd

sudo userdel etcd 2>/dev/null
sudo groupdel etcd 2>/dev/null

# Fresh installation using your guideline
ETCD_VER=v3.4.34

rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test
# Copy the file from where you transferred it
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
# rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

/tmp/etcd-download-test/etcd --version
/tmp/etcd-download-test/etcdctl version

cd /tmp/etcd-download-test/
sudo mv etcd* /usr/local/bin

etcd --version
etcdctl version

# Configure ETCD System Service
sudo mkdir -p /var/lib/etcd/
sudo mkdir /etc/etcd

sudo groupadd --system etcd
sudo useradd -s /sbin/nologin --system -g etcd etcd

sudo chown -R etcd:etcd /var/lib/etcd/
sudo chmod 0775 /var/lib/etcd/
```

Then continue with Step 1.2 in your guideline using the new IP addresses (10.101.20.204, 10.101.20.166, 10.101.20.137).





# On postgresql-1, (and 2, 3) edit the file
sudo nano /var/lib/pgsql/16/data/pg_hba.conf

# Change these lines:
host replication replicator 192.168.230.148/32 md5  # OLD postgresql-1
host replication replicator 192.168.230.145/32 md5  # OLD postgresql-2
host replication replicator 192.168.230.146/32 md5  # OLD postgresql-3

# To these new IP addresses:
host replication replicator 10.101.20.204/32 md5    # NEW postgresql-1
host replication replicator 10.101.20.166/32 md5    # NEW postgresql-2
host replication replicator 10.101.20.137/32 md5    # NEW postgresql-3
