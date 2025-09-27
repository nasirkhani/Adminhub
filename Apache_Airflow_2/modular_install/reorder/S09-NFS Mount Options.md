

## **1. NFS Mount Options - PREVENT CLIENT HANGS**

The previous mount options can cause client halts. Replace the fstab entries with resilient NFS options:

### **Update /etc/fstab on ALL client VMs**
**VMs**: haproxy-1, haproxy-2, scheduler-2, celery-1

**Remove old entries:**
```bash
sudo sed -i '/airflow-dags/d' /etc/fstab
sudo sed -i '/airflow-logs/d' /etc/fstab
```

**Add new resilient entries:**
```bash
echo "10.101.20.220:/srv/airflow/dags /mnt/airflow-dags nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0" | sudo tee -a /etc/fstab
echo "10.101.20.220:/srv/airflow/logs /mnt/airflow-logs nfs soft,timeo=10,retrans=3,intr,bg,_netdev,rsize=8192,wsize=8192 0 0" | sudo tee -a /etc/fstab
```

### **NFS Mount Options Explained:**
- **`soft`**: Allows timeouts instead of hanging indefinitely
- **`timeo=10`**: Timeout after 1 second (10 deciseconds)
- **`retrans=3`**: Retry 3 times before giving up
- **`intr`**: Allows interruption of hung operations
- **`bg`**: If mount fails, retry in background
- **`_netdev`**: Wait for network before mounting
- **`rsize=8192,wsize=8192`**: Optimized read/write buffer sizes

### **Test the new mounts:**
```bash
# Unmount existing mounts
sudo umount /mnt/airflow-dags /mnt/airflow-logs 2>/dev/null || true

# Mount with new options
sudo mount -a

# Verify mounts work
ls -la /mnt/airflow-dags/
ls -la /mnt/airflow-logs/

# Test behavior during NFS failure simulation
# (The mounts should timeout gracefully instead of hanging)
```


This way, if NFS becomes unavailable:
1. Clients won't hang (due to `soft` mount)
2. Operations can continue with local directories
3. Service remains available during NFS maintenance
