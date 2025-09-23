## **You're Largely Correct About Traffic Flow**

Your understanding is mostly accurate. Since clients only use the VIP (10.101.20.210) in their configurations, traffic does indeed only go to whichever node currently holds the VIP. Here's the nuanced reality:

**Why Your Setup Works**:
- Clients connect only to VIP → traffic goes to active node only
- Keepalived properly moves VIP between nodes
- Load balancing decisions are made by whichever HAProxy holds the VIP

**Minor Issues with Multiple Active HAProxy**:
- **Resource waste**: Both nodes consuming CPU/memory for HAProxy
- **Monitoring confusion**: Health checks running on both nodes simultaneously
- **Failover complexity**: Brief moment during VIP transition where both might be active
- **Log confusion**: Two HAProxy instances generating separate logs

**Bottom Line**: Your current setup is functionally correct for traffic handling, just not optimally efficient. If you're comfortable with it and it's working reliably, you can keep it as-is.

## **NFS Keepalived Unicast Configuration**

**On NFS-1 (10.101.20.165) - PRIMARY:**
```bash
sudo tee /etc/keepalived/keepalived.conf << 'EOF'
global_defs {
    router_id NFS_HA_PRIMARY
    script_user root
    enable_script_security
}

vrrp_script chk_nfs_services {
    script "/usr/local/bin/check_nfs_services.sh"
    interval 5
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_NFS {
    state MASTER
    interface ens160
    virtual_router_id 52
    priority 110
    advert_int 1
    
    # Unicast configuration for NFS
    unicast_src_ip 10.101.20.165
    unicast_peer {
        10.101.20.203
    }
    
    authentication {
        auth_type PASS
        auth_pass nfs_ha1
    }
    virtual_ipaddress {
        10.101.20.220/24 dev ens160
    }
    track_script {
        chk_nfs_services
    }
    notify_master "/usr/local/bin/nfs-become-master.sh"
    notify_backup "/usr/local/bin/nfs-become-backup.sh"
    notify_fault "/usr/local/bin/nfs-become-backup.sh"
}
EOF
```

**On NFS-2 (10.101.20.203) - STANDBY:**
```bash
sudo tee /etc/keepalived/keepalived.conf << 'EOF'
global_defs {
    router_id NFS_HA_STANDBY
    script_user root
    enable_script_security
}

vrrp_script chk_nfs_services {
    script "/usr/local/bin/check_nfs_services.sh"
    interval 5
    timeout 3
    weight -50
    fall 2
    rise 2
}

vrrp_instance VI_NFS {
    state BACKUP
    interface ens160
    virtual_router_id 52
    priority 100
    advert_int 1
    
    # Unicast configuration for NFS
    unicast_src_ip 10.101.20.203
    unicast_peer {
        10.101.20.165
    }
    
    authentication {
        auth_type PASS
        auth_pass nfs_ha1
    }
    virtual_ipaddress {
        10.101.20.220/24 dev ens160
    }
    track_script {
        chk_nfs_services
    }
    notify_master "/usr/local/bin/nfs-become-master.sh"
    notify_backup "/usr/local/bin/nfs-become-backup.sh"
    notify_fault "/usr/local/bin/nfs-become-backup.sh"
}
EOF
```

**Apply the configuration:**
```bash
# On both NFS nodes
sudo systemctl restart keepalived
sudo systemctl status keepalived

# Verify NFS VIP assignment (should be on NFS-1 initially)
ip addr show ens160 | grep 10.101.20.220
```

This converts your NFS keepalived to use unicast communication, matching the HAProxy setup and avoiding any multicast issues in your vRA environment.
