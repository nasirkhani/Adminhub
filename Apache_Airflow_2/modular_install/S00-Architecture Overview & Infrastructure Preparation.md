# **🚀 Enterprise Apache Airflow 2.9.0 - Complete Distributed HA Infrastructure Setup**
## **Production-Ready, Highly Available Apache Airflow from Scratch**

---

## **📋 SECTION 1: Architecture Overview & Infrastructure Preparation**

### **🎯 Final Target Architecture**

```
                    ┌─────────────────────────────────────────────┐
                    │        ENTERPRISE AIRFLOW HA CLUSTER       │
                    │         Zero Single Points of Failure      │
                    └─────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VM1 (airflow) │    │VM13 (scheduler2)│    │VM14 (haproxy2)  │
│ • Scheduler HA  │    │ • Scheduler HA  │    │ • Webserver HA  │
│ • Webserver HA  │    │ • Multi-sched   │    │ • HAProxy HA    │
│ • HAProxy Prim. │    │   Coordination  │    │ • Keepalived    │
│ • Keepalived    │    │                 │    │   Standby       │
│ • VIP Primary   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌────┴────┬──────────────────┼───────────────────────┘
    │         │                  │
    │    VIP: 192.168.83.210 (Main Services Access)
    │         │
┌───▼───┐ ┌──▼────┐    ┌─────────▼─────────┐
│  VM4  │ │VM2(ftp│    │   VM12 (nfs2)     │
│Worker │ │NFS Prim│    │ • NFS Standby     │
│       │ │DAG Proc│    │ • DAG Proc HA     │
│       │ │Keepalvd│    │ • Keepalived      │
└───────┘ └───────┘    │ • File Sync       │
              │        └───────────────────┘
              │               │
         VIP: 192.168.83.220 (NFS Access)
              │               │
    ┌─────────┴───────────────┴─────────┐
    │                                   │
┌───▼────┐ ┌────────┐ ┌────────┐ ┌─────▼────┐
│VM5(mq1)│ │VM6(mq2)│ │VM7(mq3)│ │VM3(card1)│
│RabbitMQ│ │RabbitMQ│ │RabbitMQ│ │ Target   │
│Cluster │ │Cluster │ │Cluster │ │ System   │
└────────┘ └────────┘ └────────┘ └──────────┘
    │         │         │
    └─────────┼─────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼────┐ ┌──▼───┐ ┌───▼────┐
│VM8(sql1│ │VM9   │ │VM10    │
│Patroni │ │(sql2)│ │(sql3)  │
│Primary │ │Patroni│ │Patroni │
│+ etcd  │ │Replic│ │Replica │
└────────┘ └──────┘ └────────┘
```

### **🏗️ Infrastructure Specifications**

| VM | Hostname | IP Address | Role | RAM | CPU | Disk | HA Component |
|---|---|---|---|---|---|---|---|
| VM1 | airflow | 192.168.83.129 | Scheduler + Webserver + HAProxy Primary | 4GB | 2 | 20GB | Multi-scheduler, Load Balancer |
| VM13 | scheduler2 | 192.168.83.151 | Scheduler HA | 2GB | 2 | 15GB | Multi-scheduler |
| VM14 | haproxy2 | 192.168.83.154 | Webserver + HAProxy Standby | 4GB | 2 | 20GB | Load Balancer, Webserver |
| VM2 | ftp | 192.168.83.132 | NFS Primary + DAG Processor | 2GB | 1 | 15GB | Storage HA |
| VM12 | nfs2 | 192.168.83.150 | NFS Standby + DAG Processor | 2GB | 1 | 15GB | Storage HA |
| VM4 | worker1 | 192.168.83.131 | Celery Worker | 2GB | 2 | 15GB | Horizontal scaling |
| VM3 | card1 | 192.168.83.133 | Target System | 1GB | 1 | 10GB | External system |
| VM5 | mq1 | 192.168.83.135 | RabbitMQ Node 1 | 2GB | 1 | 10GB | Message Queue HA |
| VM6 | mq2 | 192.168.83.136 | RabbitMQ Node 2 | 2GB | 1 | 10GB | Message Queue HA |
| VM7 | mq3 | 192.168.83.137 | RabbitMQ Node 3 | 2GB | 1 | 10GB | Message Queue HA |
| VM8 | sql1 | 192.168.83.148 | PostgreSQL + etcd Node 1 | 4GB | 2 | 20GB | Database HA |
| VM9 | sql2 | 192.168.83.147 | PostgreSQL + etcd Node 2 | 4GB | 2 | 20GB | Database HA |
| VM10 | sql3 | 192.168.83.149 | PostgreSQL + etcd Node 3 | 4GB | 2 | 20GB | Database HA |

### **🔗 High Availability Features**

**Virtual IPs (VIPs)**:
- **Main VIP**: `192.168.83.210` - Database, HAProxy, Webserver access
- **NFS VIP**: `192.168.83.220` - Shared storage access

**Zero Single Points of Failure**:
- ✅ **Scheduler HA**: VM1 + VM13 (multi-scheduler coordination)
- ✅ **Webserver HA**: VM1 + VM14 (load balanced via HAProxy)
- ✅ **Load Balancer HA**: VM1 + VM14 (active/passive with keepalived)
- ✅ **Database HA**: VM8,9,10 (Patroni cluster with automatic failover)
- ✅ **Message Queue HA**: VM5,6,7 (RabbitMQ cluster with mirroring)
- ✅ **Storage HA**: VM2 + VM12 (NFS active/passive with real-time sync)
- ✅ **DAG Processor HA**: VM2 + VM12 (coordinated with NFS failover)

---

## **🔧 Step 1: Base System Preparation (ALL VMs)**

### **Step 1.1: Execute on ALL VMs (VM1, VM2, VM3, VM4, VM5, VM6, VM7, VM8, VM9, VM10, VM12, VM13, VM14)**

```bash
# Update system packages
sudo dnf update -y
sudo dnf upgrade -y

# Install common packages
sudo dnf install -y vim curl wget rsync nfs-utils firewalld

# Disable SELinux for simplified setup
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Configure timezone
sudo timedatectl set-timezone Asia/Tehran

# Create rocky user with sudo privileges (if not exists)
sudo useradd -m -s /bin/bash rocky
echo "rocky:111" | sudo chpasswd
echo "rocky ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/rocky
```

### **Step 1.2: Set Hostnames (Execute on Each VM Individually)**

```bash
# On VM1:
sudo nmcli general hostname airflow

# On VM2:
sudo nmcli general hostname ftp

# On VM3:
sudo nmcli general hostname card1

# On VM4:
sudo nmcli general hostname worker1

# On VM5:
sudo nmcli general hostname mq1

# On VM6:
sudo nmcli general hostname mq2

# On VM7:
sudo nmcli general hostname mq3

# On VM8:
sudo nmcli general hostname sql1

# On VM9:
sudo nmcli general hostname sql2

# On VM10:
sudo nmcli general hostname sql3

# On VM12:
sudo nmcli general hostname nfs2

# On VM13:
sudo nmcli general hostname scheduler2

# On VM14:
sudo nmcli general hostname haproxy2

# Reboot all VMs after hostname changes
sudo reboot
```

### **Step 1.3: Configure /etc/hosts (ALL VMs)**

```bash
# Execute on ALL VMs
sudo tee -a /etc/hosts << EOF
# Airflow HA Cluster Infrastructure
192.168.83.129 airflow
192.168.83.132 ftp
192.168.83.133 card1
192.168.83.131 worker1
192.168.83.135 mq1
192.168.83.136 mq2
192.168.83.137 mq3
192.168.83.148 sql1
192.168.83.147 sql2
192.168.83.149 sql3
192.168.83.150 nfs2
192.168.83.151 scheduler2
192.168.83.154 haproxy2

# Virtual IPs
192.168.83.210 airflow-vip
192.168.83.220 nfs-vip
EOF
```

### **Step 1.4: SSH Key Setup (From VM1)**

```bash
# On VM1 (airflow) - Generate and distribute SSH keys
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy to all VMs
for host in ftp card1 worker1 mq1 mq2 mq3 sql1 sql2 sql3 nfs2 scheduler2 haproxy2; do
    ssh-copy-id rocky@$host
done

# Test connectivity
for host in ftp card1 worker1 mq1 mq2 mq3 sql1 sql2 sql3 nfs2 scheduler2 haproxy2; do
    ssh rocky@$host "echo 'SSH to $host: SUCCESS'"
done
```
