Perfect! Let me clarify the architecture - you actually **DON'T need separate HAProxy instances**. We can use **ONE HAProxy setup** that handles **BOTH** PostgreSQL load balancing AND Webserver load balancing.

## 🏗️ **Clarified HA Architecture**

### **Current State:**
- **VM1**: HAProxy (PostgreSQL) + Webserver + Scheduler

### **Target HA State:**
- **VM1**: HAProxy Primary (PostgreSQL + Webserver) + Webserver + Scheduler + Keepalived
- **VM13**: Scheduler (dedicated)
- **VM14**: HAProxy Standby (PostgreSQL + Webserver) + Webserver + Keepalived
- **VIP**: 192.168.83.200 (floating between VM1 and VM14)

## 📋 **VM Allocation Plan**

**We only need 2 new VMs:**
- ✅ **VM13 (192.168.83.151)**: Dedicated Scheduler
- ✅ **VM14 (192.168.83.154)**: HAProxy Standby + Webserver + Keepalived

**VM15 and VM16**: Reserved for future use

## 🎯 **How This Works**

### **Single HAProxy Configuration (on VM1 and VM14):**
```yaml
HAProxy handles:
├── PostgreSQL Load Balancing (existing)
│   ├── Port 5000: Write traffic → sql1/sql2/sql3
│   └── Port 6000: Read traffic → sql1/sql2/sql3
│
└── Webserver Load Balancing (new)
    └── Port 8080: Web traffic → VM1:8080 + VM14:8080
```

### **Traffic Flow:**
```
Users → VIP:8080 → HAProxy → Webserver (VM1 or VM14)
Airflow → VIP:5000 → HAProxy → PostgreSQL cluster
```

### **Failover Scenarios:**
1. **VM1 fails**: VIP moves to VM14, all traffic continues
2. **VM14 fails**: VM1 keeps VIP, no disruption  
3. **Scheduler fails**: Other scheduler continues processing
4. **Webserver fails**: HAProxy routes to healthy webserver

## 🚀 **Implementation Plan**

### **Phase 1: Scheduler HA (Priority 1)**
- Setup VM13 as dedicated scheduler
- Configure multi-scheduler coordination
- Test scheduler failover

### **Phase 2: Load Balancer HA (Priority 2)** 
- Setup VM14 with HAProxy + Keepalived
- Configure VIP (192.168.83.200)
- Test HAProxy failover

### **Phase 3: Webserver HA (Priority 3)**
- Add webserver to VM14
- Configure HAProxy to load balance webservers
- Test webserver failover

## ❓ **Final Confirmation Questions**

1. **VIP Address**: Is `192.168.83.200` available and routable in your VMware network?

2. **DNS**: Should we create a DNS entry like `airflow-cluster.local` pointing to the VIP?

3. **Maintenance**: Can we modify VM1 configuration, or do you need zero-downtime implementation?

4. **Resource Allocation**: 
   - VM13 (Scheduler): 2GB RAM, 1 CPU sufficient?
   - VM14 (HAProxy + Webserver): 4GB RAM, 2 CPU sufficient?

5. **Testing Approach**: Should we implement all phases at once, or one by one with testing between each phase?

**Does this architecture make sense to you? Should we proceed with Phase 1 (Scheduler HA) first?**
