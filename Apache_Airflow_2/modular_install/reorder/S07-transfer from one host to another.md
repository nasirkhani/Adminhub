comprehensive step-by-step guide for what needs to be changed in each VM after transfer from one host to another. 

## **IP Mapping (Old → New)**
```
192.168.230.148 postgresql-1 → 10.101.20.204 postgresql-1
192.168.230.145 postgresql-2 → 10.101.20.166 postgresql-2  
192.168.230.146 postgresql-3 → 10.101.20.137 postgresql-3
192.168.230.131 haproxy-1 → 10.101.20.202 HAproxy-1
192.168.230.132 haproxy-2 → 10.101.20.146 HAproxy-2
192.168.230.133 rabbit-1 → 10.101.20.205 Rabbit-1
192.168.230.134 rabbit-2 → 10.101.20.147 Rabbit-2
192.168.230.135 rabbit-3 → 10.101.20.206 Rabbit-3
192.168.230.140 celery-1 → 10.101.20.199 Celery-1
192.168.230.136 nfs-1 → 10.101.20.165 NFS-1
192.168.230.137 nfs-2 → 10.101.20.203 NFS-2
192.168.230.139 scheduler-2 → 10.101.20.132 Scheduler-1

VIPs (choose new ones in 10.101.20.x range):
192.168.230.210 airflow-vip → 10.101.20.210 (suggested)
192.168.230.220 nfs-vip → 10.101.20.220 (suggested)
```

## **Step-by-Step Changes Required**

### **STEP 1: Update /etc/hosts on ALL VMs**
**Location**: All 12 VMs  
**File**: `/etc/hosts`

Replace the existing host entries:
```bash
# Remove old entries and add new ones
sudo sed -i '/192.168.230/d' /etc/hosts

# Add new entries
sudo tee -a /etc/hosts << EOF
10.101.20.202 haproxy-1
10.101.20.146 haproxy-2
10.101.20.132 scheduler-2
10.101.20.165 nfs-1
10.101.20.203 nfs-2
10.101.20.205 rabbit-1
10.101.20.147 rabbit-2
10.101.20.206 rabbit-3
10.101.20.204 postgresql-1
10.101.20.166 postgresql-2
10.101.20.137 postgresql-3
10.101.20.199 celery-1
10.101.20.210 airflow-vip
10.101.20.220 nfs-vip
EOF
```

### **STEP 2: Database Cluster Configuration**

**VMs**: postgresql-1 (10.101.20.204), postgresql-2 (10.101.20.166), postgresql-3 (10.101.20.137)

#### **2.1 Update etcd service files**
**File**: `/etc/systemd/system/etcd.service`

On **postgresql-1**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /etc/systemd/system/etcd.service
```

On **postgresql-2**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /etc/systemd/system/etcd.service
```

On **postgresql-3**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /etc/systemd/system/etcd.service
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /etc/systemd/system/etcd.service
```

#### **2.2 Update Patroni configuration**
**File**: `/usr/patroni/conf/patroni.yml`

On **postgresql-1**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /usr/patroni/conf/patroni.yml
```

On **postgresql-2**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /usr/patroni/conf/patroni.yml
```

On **postgresql-3**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /usr/patroni/conf/patroni.yml
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /usr/patroni/conf/patroni.yml
```

### **STEP 3: HAProxy and Load Balancer Configuration**

**VMs**: haproxy-1 (10.101.20.202), haproxy-2 (10.101.20.146)

#### **3.1 Update HAProxy configuration**
**File**: `/etc/haproxy/haproxy.cfg`

On **both haproxy-1 and haproxy-2**:
```bash
sudo sed -i 's/192.168.230.148/10.101.20.204/g' /etc/haproxy/haproxy.cfg
sudo sed -i 's/192.168.230.145/10.101.20.166/g' /etc/haproxy/haproxy.cfg
sudo sed -i 's/192.168.230.146/10.101.20.137/g' /etc/haproxy/haproxy.cfg
sudo sed -i 's/192.168.230.131/10.101.20.202/g' /etc/haproxy/haproxy.cfg
sudo sed -i 's/192.168.230.132/10.101.20.146/g' /etc/haproxy/haproxy.cfg
```

#### **3.2 Update Keepalived configuration**
**File**: `/etc/keepalived/keepalived.conf`

On **haproxy-1**:
```bash
sudo sed -i 's/192.168.230.210/10.101.20.210/g' /etc/keepalived/keepalived.conf
```

On **haproxy-2**:
```bash
sudo sed -i 's/192.168.230.210/10.101.20.210/g' /etc/keepalived/keepalived.conf
```

### **STEP 4: RabbitMQ Cluster Configuration**

**VMs**: rabbit-1 (10.101.20.205), rabbit-2 (10.101.20.147), rabbit-3 (10.101.20.206)

#### **4.1 Update monitoring scripts**
**File**: `/usr/local/bin/check_rabbitmq_cluster.sh` (if exists on haproxy-1)

```bash
sudo sed -i 's/192.168.230.133/10.101.20.205/g' /usr/local/bin/check_rabbitmq_cluster.sh
sudo sed -i 's/192.168.230.134/10.101.20.147/g' /usr/local/bin/check_rabbitmq_cluster.sh
sudo sed -i 's/192.168.230.135/10.101.20.206/g' /usr/local/bin/check_rabbitmq_cluster.sh
```

### **STEP 5: NFS Storage Configuration**

**VMs**: nfs-1 (10.101.20.165), nfs-2 (10.101.20.203)

#### **5.1 Update service management scripts**
**Files**: `/usr/local/bin/nfs-become-master.sh`, `/usr/local/bin/nfs-become-backup.sh`

On **nfs-1**:
```bash
sudo sed -i 's/192.168.230.137/10.101.20.203/g' /usr/local/bin/nfs-become-*.sh
```

On **nfs-2**:
```bash
sudo sed -i 's/192.168.230.136/10.101.20.165/g' /usr/local/bin/nfs-become-*.sh
```

#### **5.2 Update Keepalived configuration**
**File**: `/etc/keepalived/keepalived.conf`

On **nfs-1**:
```bash
sudo sed -i 's/192.168.230.220/10.101.20.220/g' /etc/keepalived/keepalived.conf
```

On **nfs-2**:
```bash
sudo sed -i 's/192.168.230.220/10.101.20.220/g' /etc/keepalived/keepalived.conf
```

#### **5.3 Update NFS exports**
**File**: `/etc/exports`

On **both nfs-1 and nfs-2**:
```bash
sudo sed -i 's/192.168.230.0\/24/10.101.20.0\/24/g' /etc/exports
```

### **STEP 6: Update NFS Client Mounts**

**VMs**: haproxy-1, haproxy-2, scheduler-2, celery-1

#### **6.1 Update /etc/fstab**
**File**: `/etc/fstab`

On **all client VMs**:
```bash
sudo sed -i 's/192.168.230.220/10.101.20.220/g' /etc/fstab
```

#### **6.2 Remount NFS shares**
On **all client VMs**:
```bash
sudo umount /mnt/airflow-dags /mnt/airflow-logs 2>/dev/null || true
sudo mount -a
```

### **STEP 7: Airflow Configuration Updates**

**VMs**: haproxy-1, haproxy-2, scheduler-2, celery-1, nfs-1, nfs-2

#### **7.1 Update airflow.cfg**
**File**: `~/airflow/airflow.cfg`

On **all Airflow VMs**:
```bash
sed -i 's/192.168.230.210/10.101.20.210/g' ~/airflow/airflow.cfg
```

### **STEP 8: Restart Services in Correct Order**

#### **8.1 Stop all services first**
```bash
# On all PostgreSQL VMs
sudo systemctl stop patroni etcd

# On all HAProxy VMs  
sudo systemctl stop keepalived haproxy

# On all RabbitMQ VMs
sudo systemctl stop rabbitmq-server

# On all NFS VMs
sudo systemctl stop keepalived lsyncd nfs-server airflow-dag-processor

# On all Airflow VMs
sudo systemctl stop airflow-*
```

#### **8.2 Start services in correct order**

**First - Database cluster:**
```bash
# On all PostgreSQL VMs
sudo systemctl daemon-reload
sudo systemctl start etcd
sleep 10
sudo systemctl start patroni
```

**Second - Load balancers:**
```bash
# On both HAProxy VMs
sudo systemctl start haproxy
sudo systemctl start keepalived
```

**Third - Message queue:**
```bash
# On all RabbitMQ VMs  
sudo systemctl start rabbitmq-server
```

**Fourth - Storage:**
```bash
# On both NFS VMs
sudo systemctl start keepalived
```

**Fifth - Airflow services:**
```bash
# Start in this order:
# 1. DAG processors (will start automatically with NFS failover)
# 2. Schedulers
# 3. Webservers  
# 4. Workers
```

### **STEP 9: Verification**

#### **9.1 Test VIP accessibility**
```bash
ping -c 3 10.101.20.210  # Main VIP
ping -c 3 10.101.20.220  # NFS VIP
```

#### **9.2 Test database connectivity**
```bash
export PGPASSWORD=airflow_pass
psql -h 10.101.20.210 -U airflow_user -p 5000 -d airflow_db -c "SELECT 1;"
```

#### **9.3 Test Airflow UI**
```bash
curl -I http://10.101.20.210:8081
```

## **Critical Notes:**

1. **VIP Selection**: Make sure 10.101.20.210 and 10.101.20.220 are not assigned to any existing devices
2. **Network Interface**: Verify the network interface name hasn't changed in keepalived configs
3. **Firewall**: Ensure firewall rules allow the new IP ranges
4. **Service Dependencies**: Start services in the specified order to avoid dependency issues

