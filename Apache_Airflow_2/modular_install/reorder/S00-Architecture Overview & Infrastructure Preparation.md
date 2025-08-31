# **Enterprise Apache Airflow 2.9.0 - Complete Distributed HA Infrastructure Setup**
## **Production-Ready, Highly Available Apache Airflow from Scratch**

---

## **SECTION 1:  Architecture Overview & Infrastructure Preparation**

### **Final Target Architecture**

```
                    ┌─────────────────────────────────────────────┐
                    │        ENTERPRISE AIRFLOW HA CLUSTER       │
                    │         Zero Single Points of Failure      │
                    └─────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  VM1 (haproxy-1)│    │VM3 (scheduler-2)│    │VM2 (haproxy-2)  │
│ • Scheduler HA  │    │ • Scheduler HA  │    │ • Webserver HA  │
│ • Webserver HA  │    │ • Multi-sched   │    │ • HAProxy HA    │
│ • HAProxy Prim. │    │   Coordination  │    │ • Keepalived    │
│ • Keepalived    │    │                 │    │   Standby       │
│ • VIP Primary   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌────┴────┬──────────────────┼───────────────────────┘
    │         │                  │
    │    VIP: <MAIN_VIP> (Main Services Access)
    │         │
┌───▼───┐ ┌──▼────┐    ┌─────────▼─────────┐
│VM12   │ │VM4    │    │   VM5 (nfs-2)     │
│Celery │ │(nfs-1)│    │ • NFS Standby     │
│Worker │ │NFS Prim│    │ • DAG Proc HA     │
│       │ │DAG Proc│    │ • Keepalived      │
│       │ │Keepalvd│    │ • File Sync       │
└───────┘ └───────┘    └───────────────────┘
              │               │
         VIP: <NFS_VIP> (NFS Access)
              │               │
    ┌─────────┴───────────────┴─────────┐
    │                                   │
┌───▼────┐ ┌────────┐ ┌────────┐ ┌─────▼────┐
│VM6     │ │VM7     │ │VM8     │ │VM13      │
│rabbit-1│ │rabbit-2│ │rabbit-3│ │target-1  │
│RabbitMQ│ │RabbitMQ│ │RabbitMQ│ │ Target   │
│Cluster │ │Cluster │ │Cluster │ │ System   │
└────────┘ └────────┘ └────────┘ └──────────┘
    │         │         │
    └─────────┼─────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼────┐ ┌──▼───┐ ┌───▼────┐
│VM9     │ │VM10  │ │VM11    │
│postgres│ │postgres│ │postgres│
│-1 +etcd│ │-2 Repl│ │-3 Repl │
│Primary │ │Patroni│ │Patroni │
└────────┘ └──────┘ └────────┘
```

### **Infrastructure Specifications**

**⚠️ IMPORTANT: Replace all IP placeholders with your actual VM IP addresses**

| VM | Hostname | IP Placeholder | Role | RAM | CPU | Disk | HA Component |
|---|---|---|---|---|---|---|---|
| VM1 | haproxy-1 | `<HAPROXY_1_IP>` | Scheduler + Webserver + HAProxy Primary | 4GB | 2 | 20GB | Multi-scheduler, Load Balancer |
| VM2 | haproxy-2 | `<HAPROXY_2_IP>` | Webserver + HAProxy Standby | 4GB | 2 | 20GB | Load Balancer, Webserver |
| VM3 | scheduler-2 | `<SCHEDULER_2_IP>` | Scheduler HA | 2GB | 2 | 15GB | Multi-scheduler |
| VM4 | nfs-1 | `<NFS_1_IP>` | NFS Primary + DAG Processor | 2GB | 1 | 15GB | Storage HA |
| VM5 | nfs-2 | `<NFS_2_IP>` | NFS Standby + DAG Processor | 2GB | 1 | 15GB | Storage HA |
| VM6 | rabbit-1 | `<RABBIT_1_IP>` | RabbitMQ Node 1 | 2GB | 1 | 10GB | Message Queue HA |
| VM7 | rabbit-2 | `<RABBIT_2_IP>` | RabbitMQ Node 2 | 2GB | 1 | 10GB | Message Queue HA |
| VM8 | rabbit-3 | `<RABBIT_3_IP>` | RabbitMQ Node 3 | 2GB | 1 | 10GB | Message Queue HA |
| VM9 | postgresql-1 | `<POSTGRESQL_1_IP>` | PostgreSQL + etcd Node 1 | 4GB | 2 | 20GB | Database HA |
| VM10 | postgresql-2 | `<POSTGRESQL_2_IP>` | PostgreSQL + etcd Node 2 | 4GB | 2 | 20GB | Database HA |
| VM11 | postgresql-3 | `<POSTGRESQL_3_IP>` | PostgreSQL + etcd Node 3 | 4GB | 2 | 20GB | Database HA |
| VM12 | celery-1 | `<CELERY_1_IP>` | Celery Worker | 2GB | 2 | 15GB | Horizontal scaling |
| VM13 | target-1 | `<TARGET_1_IP>` | Target System | 1GB | 1 | 10GB | External system |

### **🔗 High Availability Features**

**Virtual IPs (VIPs) - User Configuration Required**:
- **Main VIP**: `<MAIN_VIP>` - Database, HAProxy, Webserver access
- **NFS VIP**: `<NFS_VIP>` - Shared storage access

**📌 VIP Selection Guidelines:**
- Choose IPs from the **same subnet** as your VMs
- Ensure VIPs are **NOT assigned** to any existing device
- VIPs should be **consecutive or easily memorable**
- Example: If your VMs are in 192.168.1.0/24, choose VIPs like 192.168.1.210 and 192.168.1.220

**Zero Single Points of Failure**:
- ✅ **Scheduler HA**: VM1 + VM3 (multi-scheduler coordination)
- ✅ **Webserver HA**: VM1 + VM2 (load balanced via HAProxy)
- ✅ **Load Balancer HA**: VM1 + VM2 (active/passive with keepalived)
- ✅ **Database HA**: VM9,10,11 (Patroni cluster with automatic failover)
- ✅ **Message Queue HA**: VM6,7,8 (RabbitMQ cluster with mirroring)
- ✅ **Storage HA**: VM4 + VM5 (NFS active/passive with real-time sync)
- ✅ **DAG Processor HA**: VM4 + VM5 (coordinated with NFS failover)

---

## **🔧 Step 1: Base System Preparation (ALL VMs)**

### **Step 1.1: Execute on ALL VMs (VM1 through VM13)**

**⚠️ Run these commands on every single VM in your infrastructure:**

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

**Execute the appropriate command on each VM:**

```bash
# On VM1:
sudo nmcli general hostname haproxy-1

# On VM2:
sudo nmcli general hostname haproxy-2

# On VM3:
sudo nmcli general hostname scheduler-2

# On VM4:
sudo nmcli general hostname nfs-1

# On VM5:
sudo nmcli general hostname nfs-2

# On VM6:
sudo nmcli general hostname rabbit-1

# On VM7:
sudo nmcli general hostname rabbit-2

# On VM8:
sudo nmcli general hostname rabbit-3

# On VM9:
sudo nmcli general hostname postgresql-1

# On VM10:
sudo nmcli general hostname postgresql-2

# On VM11:
sudo nmcli general hostname postgresql-3

# On VM12:
sudo nmcli general hostname celery-1

# On VM13:
sudo nmcli general hostname target-1

# Reboot all VMs after hostname changes
sudo reboot
```

### **Step 1.3: Configure /etc/hosts (ALL VMs)**

**⚠️ CRITICAL: Replace ALL IP placeholders with your actual VM IP addresses before executing:**

```bash
# Execute on ALL VMs - REPLACE <VM_IP> placeholders with your actual IPs
sudo tee -a /etc/hosts << EOF
# Airflow HA Cluster Infrastructure - REPLACE ALL IPs WITH YOUR ACTUAL VALUES
<HAPROXY_1_IP> haproxy-1
<HAPROXY_2_IP> haproxy-2
<SCHEDULER_2_IP> scheduler-2
<NFS_1_IP> nfs-1
<NFS_2_IP> nfs-2
<RABBIT_1_IP> rabbit-1
<RABBIT_2_IP> rabbit-2
<RABBIT_3_IP> rabbit-3
<POSTGRESQL_1_IP> postgresql-1
<POSTGRESQL_2_IP> postgresql-2
<POSTGRESQL_3_IP> postgresql-3
<CELERY_1_IP> celery-1
<TARGET_1_IP> target-1

# Virtual IPs - REPLACE WITH YOUR CHOSEN VIP ADDRESSES
<MAIN_VIP> airflow-vip
<NFS_VIP> nfs-vip
EOF
```

**🔧 Automated IP Replacement Helper:**
```bash
# Create a script to help replace IP placeholders - customize with your IPs
sudo tee /tmp/replace_ips.sh << 'EOF'
#!/bin/bash
# CUSTOMIZE THESE VALUES WITH YOUR ACTUAL IPs:
HAPROXY_1_IP="192.168.1.10"      # Replace with VM1 IP
HAPROXY_2_IP="192.168.1.11"      # Replace with VM2 IP
SCHEDULER_2_IP="192.168.1.12"    # Replace with VM3 IP
NFS_1_IP="192.168.1.13"          # Replace with VM4 IP
NFS_2_IP="192.168.1.14"          # Replace with VM5 IP
RABBIT_1_IP="192.168.1.15"       # Replace with VM6 IP
RABBIT_2_IP="192.168.1.16"       # Replace with VM7 IP
RABBIT_3_IP="192.168.1.17"       # Replace with VM8 IP
POSTGRESQL_1_IP="192.168.1.18"   # Replace with VM9 IP
POSTGRESQL_2_IP="192.168.1.19"   # Replace with VM10 IP
POSTGRESQL_3_IP="192.168.1.20"   # Replace with VM11 IP
CELERY_1_IP="192.168.1.21"       # Replace with VM12 IP
TARGET_1_IP="192.168.1.22"       # Replace with VM13 IP
MAIN_VIP="192.168.1.210"         # Replace with your chosen Main VIP
NFS_VIP="192.168.1.220"          # Replace with your chosen NFS VIP

# Apply replacements to /etc/hosts
sudo sed -i "s/<HAPROXY_1_IP>/$HAPROXY_1_IP/g" /etc/hosts
sudo sed -i "s/<HAPROXY_2_IP>/$HAPROXY_2_IP/g" /etc/hosts
sudo sed -i "s/<SCHEDULER_2_IP>/$SCHEDULER_2_IP/g" /etc/hosts
sudo sed -i "s/<NFS_1_IP>/$NFS_1_IP/g" /etc/hosts
sudo sed -i "s/<NFS_2_IP>/$NFS_2_IP/g" /etc/hosts
sudo sed -i "s/<RABBIT_1_IP>/$RABBIT_1_IP/g" /etc/hosts
sudo sed -i "s/<RABBIT_2_IP>/$RABBIT_2_IP/g" /etc/hosts
sudo sed -i "s/<RABBIT_3_IP>/$RABBIT_3_IP/g" /etc/hosts
sudo sed -i "s/<POSTGRESQL_1_IP>/$POSTGRESQL_1_IP/g" /etc/hosts
sudo sed -i "s/<POSTGRESQL_2_IP>/$POSTGRESQL_2_IP/g" /etc/hosts
sudo sed -i "s/<POSTGRESQL_3_IP>/$POSTGRESQL_3_IP/g" /etc/hosts
sudo sed -i "s/<CELERY_1_IP>/$CELERY_1_IP/g" /etc/hosts
sudo sed -i "s/<TARGET_1_IP>/$TARGET_1_IP/g" /etc/hosts
sudo sed -i "s/<MAIN_VIP>/$MAIN_VIP/g" /etc/hosts
sudo sed -i "s/<NFS_VIP>/$NFS_VIP/g" /etc/hosts

echo "IP replacement completed. Verify /etc/hosts file:"
cat /etc/hosts | tail -15
EOF

sudo chmod +x /tmp/replace_ips.sh
# After customizing the script with your IPs, run it:
# sudo /tmp/replace_ips.sh
```

### **Step 1.4: SSH Key Setup (From VM1)**

**Execute on VM1 (haproxy-1) - Generate and distribute SSH keys:**

```bash
# On VM1 (haproxy-1) - Generate and distribute SSH keys
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy to all VMs using hostnames (after /etc/hosts is configured)
for host in haproxy-2 scheduler-2 nfs-1 nfs-2 rabbit-1 rabbit-2 rabbit-3 postgresql-1 postgresql-2 postgresql-3 celery-1 target-1; do
    ssh-copy-id rocky@$host
done

# Test connectivity using hostnames
for host in haproxy-2 scheduler-2 nfs-1 nfs-2 rabbit-1 rabbit-2 rabbit-3 postgresql-1 postgresql-2 postgresql-3 celery-1 target-1; do
    ssh rocky@$host "echo 'SSH to $host: SUCCESS'"
done
```

**🔧 Alternative with IP addresses (if hostnames not working yet):**
```bash
# Alternative method using IP addresses - REPLACE with your actual IPs
# Copy to all VMs using IP addresses
for ip in <HAPROXY_2_IP> <SCHEDULER_2_IP> <NFS_1_IP> <NFS_2_IP> <RABBIT_1_IP> <RABBIT_2_IP> <RABBIT_3_IP> <POSTGRESQL_1_IP> <POSTGRESQL_2_IP> <POSTGRESQL_3_IP> <CELERY_1_IP> <TARGET_1_IP>; do
    ssh-copy-id rocky@$ip
done
```

### **Step 1.5: Network Validation**

**Verify network connectivity and hostname resolution:**

```bash
# Test hostname resolution
echo "=== Testing Hostname Resolution ==="
for host in haproxy-1 haproxy-2 scheduler-2 nfs-1 nfs-2 rabbit-1 rabbit-2 rabbit-3 postgresql-1 postgresql-2 postgresql-3 celery-1 target-1; do
    if ping -c 1 $host >/dev/null 2>&1; then
        echo "✅ $host: REACHABLE"
    else
        echo "❌ $host: FAILED"
    fi
done

# Test VIP availability (should fail initially - VIPs not configured yet)
echo ""
echo "=== Testing VIP Availability (Should fail initially) ==="
ping -c 1 <MAIN_VIP> && echo "⚠️ MAIN_VIP already in use!" || echo "✅ MAIN_VIP available"
ping -c 1 <NFS_VIP> && echo "⚠️ NFS_VIP already in use!" || echo "✅ NFS_VIP available"

# Test SSH connectivity
echo ""
echo "=== Testing SSH Connectivity ==="
for host in haproxy-2 scheduler-2 nfs-1 nfs-2 rabbit-1 rabbit-2 rabbit-3 postgresql-1 postgresql-2 postgresql-3 celery-1 target-1; do
    if ssh -o ConnectTimeout=5 rocky@$host "echo 'Connected'" 2>/dev/null; then
        echo "✅ SSH to $host: SUCCESS"
    else
        echo "❌ SSH to $host: FAILED"
    fi
done
```

### **📋 Pre-Implementation Checklist**

Before proceeding to the next sections, ensure:

```bash
# Run this validation script on VM1 (haproxy-1)
echo "=== INFRASTRUCTURE PREPARATION CHECKLIST ==="
echo ""

# 1. Check all hostnames are set correctly
echo "1. Hostname Verification:"
for host in haproxy-1 haproxy-2 scheduler-2 nfs-1 nfs-2 rabbit-1 rabbit-2 rabbit-3 postgresql-1 postgresql-2 postgresql-3 celery-1 target-1; do
    hostname_result=$(ssh -o ConnectTimeout=5 rocky@$host "hostname" 2>/dev/null)
    if [ "$hostname_result" = "$host" ]; then
        echo "   ✅ $host hostname correct"
    else
        echo "   ❌ $host hostname incorrect (got: $hostname_result)"
    fi
done

# 2. Check /etc/hosts configuration
echo ""
echo "2. /etc/hosts Configuration:"
if grep -q "<.*_IP>" /etc/hosts; then
    echo "   ❌ IP placeholders still exist in /etc/hosts - REPLACE THEM!"
    grep "<.*_IP>" /etc/hosts
else
    echo "   ✅ All IP placeholders replaced"
fi

# 3. Check VIP availability
echo ""
echo "3. VIP Availability:"
ping -c 1 <MAIN_VIP> >/dev/null 2>&1 && echo "   ❌ MAIN_VIP already in use!" || echo "   ✅ MAIN_VIP available"
ping -c 1 <NFS_VIP> >/dev/null 2>&1 && echo "   ❌ NFS_VIP already in use!" || echo "   ✅ NFS_VIP available"

echo ""
echo "=== READY FOR NEXT PHASE: Database HA Cluster Setup ==="
```

**🚨 IMPORTANT NOTES:**

1. **IP Address Replacement**: You MUST replace all `<*_IP>` placeholders with your actual VM IP addresses before proceeding
2. **VIP Selection**: Choose VIPs that are in the same subnet but not assigned to any device
3. **Hostname Resolution**: Ensure all VMs can resolve each other by hostname
4. **SSH Connectivity**: Passwordless SSH must work between all VMs
5. **Network Subnet**: Update example subnets (192.168.1.0/24) with your actual network range

**Next Steps**: Once this infrastructure preparation is complete and validated, proceed to **S01-Database_HA_Cluster_Setup.md** for PostgreSQL cluster configuration.

---

**Infrastructure Foundation Complete! ✅**
- 13 VMs configured with proper hostnames
- Network connectivity established
- SSH key distribution completed  
- Ready for HA component installation

