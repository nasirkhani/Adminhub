# 🛠️ HA Components Deep Dive

## **🎯 Core HA Stack Overview**

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT ACCESS                        │
│           Virtual IP: 192.168.83.200                   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │       KEEPALIVED          │
        │   (Virtual IP Manager)    │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        │    APPLICATION LAYER      │
        │  (NFS Server + DAG Proc)  │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        │         DRBD              │
        │   (Storage Replication)   │
        └───────────────────────────┘
```

---

## **🔧 Component Roles & Relationships**

### **1. DRBD (Distributed Replicated Block Device)**
```
VM2: /dev/drbd0 ←→ VM12: /dev/drbd0
     Primary         Secondary
```

**Role:** Real-time storage replication
- **What it does:** Mirrors disk blocks between VM2 and VM12 in real-time
- **Active/Passive:** Only PRIMARY can write, SECONDARY receives copies
- **Failure handling:** If PRIMARY fails, SECONDARY can be promoted instantly
- **Data guarantee:** Zero data loss (synchronous replication)

**Example:**
```bash
# VM2 writes file → Immediately replicated to VM12
# VM2 fails → VM12 promoted → Same file available
```

### **2. Keepalived (Virtual IP Manager)**
```
VM2: Priority 110 (MASTER) ←→ VM12: Priority 100 (BACKUP)
     Owns 192.168.83.200        Standby for 192.168.83.200
```

**Role:** Virtual IP failover management
- **What it does:** Manages floating IP address between nodes
- **How it works:** Uses VRRP (Virtual Router Redundancy Protocol)
- **Health checking:** Monitors services (NFS, DAG processor)
- **Failover trigger:** If VM2 unhealthy → Move IP to VM12

**Example:**
```bash
# Normal: 192.168.83.200 → VM2
# VM2 fails: 192.168.83.200 → VM12 (automatic, ~10 seconds)
```

### **3. Virtual IP (VIP)**
```
Clients connect to: 192.168.83.200
Actually served by: VM2 OR VM12 (transparent to clients)
```

**Role:** Single access point for HA service
- **What it provides:** Fixed IP that clients always use
- **Transparency:** Clients don't know which physical server responds
- **Seamless failover:** IP moves between servers automatically

### **4. Pacemaker + Corosync (Advanced - NOT used in our setup)**
```
Pacemaker: Resource manager (starts/stops services)
Corosync: Cluster communication layer
```

**Note:** We use **Keepalived instead** because it's simpler for our 2-node setup.

---

## **🔄 How Components Work Together**

### **Normal Operation (VM2 Active):**
```
1. Client requests file from 192.168.83.200
2. Keepalived routes to VM2 (current MASTER)
3. VM2 serves file from DRBD primary device
4. DRBD replicates any changes to VM12
```

### **Failover Scenario (VM2 Fails):**
```
1. Keepalived detects VM2 unhealthy
2. Keepalived moves 192.168.83.200 to VM12
3. VM12 promotes DRBD from secondary to primary
4. VM12 starts NFS server + DAG processor
5. Client requests continue transparently
```

---

## **⚡ Timing & Process Flow**

### **Failover Sequence (30-60 seconds total):**
```
T+0s:  VM2 crashes
T+10s: Keepalived detects failure
T+15s: Virtual IP moves to VM12
T+20s: VM12 promotes DRBD to primary
T+25s: VM12 mounts filesystem
T+30s: VM12 starts NFS + DAG processor
T+35s: Services fully available on VM12
```

### **Recovery Sequence (VM2 comes back):**
```
T+0s:  VM2 reboots and joins cluster
T+5s:  VM2 becomes DRBD secondary
T+10s: VM2 syncs any missed data from VM12
T+15s: VM2 ready as backup (but VM12 stays active)
```

**Note:** Failback is typically manual to avoid flip-flopping.

---

## **🎯 Why This Architecture?**

### **DRBD Benefits:**
- ✅ **Synchronous replication** (zero data loss)
- ✅ **Block-level** (works with any filesystem)
- ✅ **Real-time** (immediate consistency)
- ✅ **Proven technology** (used in enterprise environments)

### **Keepalived Benefits:**
- ✅ **Simple setup** (vs Pacemaker complexity)
- ✅ **Built-in health checks** (monitors actual services)
- ✅ **VRRP standard** (industry-standard protocol)
- ✅ **Fast failover** (sub-minute detection and switching)

### **Virtual IP Benefits:**
- ✅ **Client transparency** (no config changes needed)
- ✅ **DNS-friendly** (single hostname for HA service)
- ✅ **Application-agnostic** (works with any TCP/IP service)
- ✅ **Load balancer integration** (can be backend target)

---

## **📊 Component Dependencies**

```
Virtual IP (Top Layer)
    ↕
Keepalived (Service Manager)
    ↕
NFS Server + DAG Processor (Applications)
    ↕
Filesystem Mount (Local Access)
    ↕
DRBD (Storage Layer)
    ↕
Physical Disk (Bottom Layer)
```

**Startup Order:**
1. DRBD starts and syncs storage
2. Primary node mounts filesystem
3. Applications (NFS/DAG processor) start
4. Keepalived manages Virtual IP
5. Clients connect via Virtual IP

**Shutdown Order:** Reverse of startup

This architecture provides **enterprise-grade HA** with automatic failover, zero data loss, and transparent client access! 🎯
