# 🚀 Airflow PostgreSQL HA Migration Plan

## **📋 Pre-Migration Setup & Validation**

### **Step 1: Create Migration Workspace on VM1**
```bash
# On VM1 (airflow)
sudo mkdir -p /opt/airflow-migration/{backups,logs,scripts}
sudo chown rocky:rocky /opt/airflow-migration/ -R
cd /opt/airflow-migration
```

### **Step 2: Create Migration User on HA Cluster**
```bash
# On VM1 - Connect to HA cluster as postgres user
export PGPASSWORD=postgres
psql -h 192.168.83.129 -U postgres -p 5000 -c "
CREATE DATABASE airflow_db 
    WITH OWNER postgres 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8';"

psql -h 192.168.83.129 -U postgres -p 5000 -c "
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER USER airflow_user CREATEDB;"

# Connect to the new database and grant schema permissions
psql -h 192.168.83.129 -U postgres -p 5000 -d airflow_db -c "
GRANT ALL ON SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow_user;"
```

**✅ Validation:**
```bash
# Verify database and user creation
psql -h 192.168.83.129 -U postgres -p 5000 -c "\l airflow_db"
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "SELECT current_user, current_database();"
```

---

## **🛑 PHASE 1: Airflow Services Shutdown**

### **Step 3: Stop All Airflow Services**
```bash
# On VM1 (airflow)
echo "Stopping Airflow services..."
sudo systemctl stop airflow-webserver
sudo systemctl stop airflow-scheduler
sudo systemctl stop airflow-flower

# On VM4 (celery worker)
sudo systemctl stop airflow-celery-worker

# Verify all services are stopped
sudo systemctl status airflow-webserver airflow-scheduler airflow-flower
```

**✅ Validation:**
```bash
# Ensure no active connections to database
sudo -u postgres psql -d airflow_db -c "
SELECT pid, usename, application_name, state 
FROM pg_stat_activity 
WHERE datname = 'airflow_db' AND state = 'active';"
```

---

## **💾 PHASE 2: Database Backup & Export**

### **Step 4: Create Full Database Backup**
```bash
# On VM1 - Create backup of current database
sudo -u postgres pg_dump airflow_db > /opt/airflow-migration/backups/airflow_db_backup_$(date +%Y%m%d_%H%M%S).sql

# Create compressed backup
sudo -u postgres pg_dump -Fc airflow_db > /opt/airflow-migration/backups/airflow_db_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup files
ls -lh /opt/airflow-migration/backups/
```

**✅ Validation:**
```bash
# Verify backup integrity
sudo -u postgres pg_restore --list /opt/airflow-migration/backups/airflow_db_backup_*.dump | head -20
```

### **Step 5: Export Schema and Data Separately (for PostgreSQL 13→16 compatibility)**
```bash
# Export schema only
sudo -u postgres pg_dump --schema-only --no-owner --no-privileges airflow_db > /opt/airflow-migration/backups/airflow_schema.sql

# Export data only
sudo -u postgres pg_dump --data-only --no-owner airflow_db > /opt/airflow-migration/backups/airflow_data.sql

# Verify export files
wc -l /opt/airflow-migration/backups/airflow_*.sql
```

---

## **📤 PHASE 3: Data Import to HA Cluster**

### **Step 6: Import Schema to HA Cluster**
```bash
# On VM1 - Import schema first
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -f /opt/airflow-migration/backups/airflow_schema.sql > /opt/airflow-migration/logs/schema_import.log 2>&1

# Check for any errors
grep -i error /opt/airflow-migration/logs/schema_import.log
```

**✅ Validation:**
```bash
# Verify all tables were created
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "\dt+ | wc -l"
# Should show 44 tables (same as source)
```

### **Step 7: Import Data to HA Cluster**
```bash
# Import data
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -f /opt/airflow-migration/backups/airflow_data.sql > /opt/airflow-migration/logs/data_import.log 2>&1

# Check for any errors
grep -i error /opt/airflow-migration/logs/data_import.log
```

**✅ Validation:**
```bash
# Compare table row counts between source and destination
echo "=== SOURCE DATABASE ROW COUNTS ==="
sudo -u postgres psql -d airflow_db -c "
SELECT schemaname,tablename,n_tup_ins-n_tup_del AS row_count 
FROM pg_stat_user_tables 
WHERE schemaname='public' 
ORDER BY tablename;"

echo "=== DESTINATION DATABASE ROW COUNTS ==="
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT schemaname,tablename,n_tup_ins-n_tup_del AS row_count 
FROM pg_stat_user_tables 
WHERE schemaname='public' 
ORDER BY tablename;"
```

---

## **⚙️ PHASE 4: Configuration Updates**

### **Step 8: Backup Current Airflow Configuration**
```bash
# On VM1
cp /home/rocky/airflow/airflow.cfg /opt/airflow-migration/backups/airflow.cfg.backup
```

### **Step 9: Update Airflow Configuration**
```bash
# On VM1 - Update airflow.cfg
sed -i.bak 's/sql_alchemy_conn = postgresql:\/\/airflow_user:airflow_pass@localhost:5432\/airflow_db/sql_alchemy_conn = postgresql:\/\/airflow_user:airflow_pass@192.168.83.129:5000\/airflow_db/' /home/rocky/airflow/airflow.cfg

sed -i 's/result_backend = db+postgresql:\/\/airflow_user:airflow_pass@localhost:5432\/airflow_db/result_backend = db+postgresql:\/\/airflow_user:airflow_pass@192.168.83.129:5000\/airflow_db/' /home/rocky/airflow/airflow.cfg

# Add connection pooling for HA setup
sed -i '/\[database\]/a\
pool_size = 10\
max_overflow = 20\
pool_pre_ping = True\
pool_recycle = 3600' /home/rocky/airflow/airflow.cfg
```

**✅ Validation:**
```bash
# Verify configuration changes
grep -A5 -B5 "sql_alchemy_conn\|result_backend" /home/rocky/airflow/airflow.cfg
```

### **Step 10: Test Database Connection**
```bash
# Test new connection
airflow db check
```

---

## **🚀 PHASE 5: Service Restart & Validation**

### **Step 11: Start Airflow Services**
```bash
# On VM1
sudo systemctl start airflow-scheduler
sleep 10
sudo systemctl start airflow-webserver
sleep 5
sudo systemctl start airflow-flower

# On VM4
sudo systemctl start airflow-celery-worker

# Check service status
sudo systemctl status airflow-scheduler airflow-webserver airflow-flower
```

**✅ Validation:**
```bash
# Check Airflow connectivity
airflow dags list | head -5

# Check database connectivity through HA cluster
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT COUNT(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = 'airflow_db';"

# Verify on all cluster nodes that connections are working
psql -h 192.168.83.148 -U airflow_user -p 5432 -d airflow_db -c "SELECT 'sql1 direct connection works';"
psql -h 192.168.83.147 -U airflow_user -p 5432 -d airflow_db -c "SELECT 'sql2 direct connection works';"
psql -h 192.168.83.149 -U airflow_user -p 5432 -d airflow_db -c "SELECT 'sql3 direct connection works';"
```

### **Step 12: Web UI Verification**
```bash
# Access Airflow Web UI
echo "Access Airflow UI at: http://192.168.83.129:8080"
echo "Login with your existing credentials"

# Check HAProxy stats
echo "Check HAProxy stats at: http://192.168.83.129:7000"
```

---

## **🔄 PHASE 6: Final Testing & Cleanup**

### **Step 13: Test DAG Execution**
```bash
# Trigger a simple DAG to test end-to-end functionality
airflow dags unpause tutorial
airflow dags trigger tutorial
sleep 30
airflow dags state tutorial $(date +%Y-%m-%d)
```

### **Step 14: Test Failover (Optional but Recommended)**
```bash
# On sql1 - Stop current leader to test automatic failover
sudo systemctl stop patroni

# Wait 30 seconds and check cluster status from sql2
# On sql2:
patronictl -c /usr/patroni/conf/patroni.yml list

# Verify Airflow still works during failover
airflow db check

# Restart sql1 to restore full cluster
# On sql1:
sudo systemctl start patroni
```

---

## **🛡️ ROLLBACK PROCEDURE (if needed)**

### **Emergency Rollback Steps:**
```bash
# 1. Stop all Airflow services
sudo systemctl stop airflow-webserver airflow-scheduler airflow-flower
sudo systemctl stop airflow-celery-worker  # On VM4

# 2. Restore original configuration
cp /opt/airflow-migration/backups/airflow.cfg.backup /home/rocky/airflow/airflow.cfg

# 3. Start local PostgreSQL service (if stopped)
sudo systemctl start postgresql

# 4. Restore database (if corrupted)
sudo -u postgres dropdb airflow_db
sudo -u postgres createdb airflow_db -O airflow_user
sudo -u postgres psql airflow_db < /opt/airflow-migration/backups/airflow_db_backup_*.sql

# 5. Restart Airflow services
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver
sudo systemctl start airflow-flower
sudo systemctl start airflow-celery-worker  # On VM4
```

---

## **📊 Post-Migration Monitoring**

### **Key Metrics to Monitor:**
```bash
# 1. Monitor HA cluster health
watch -n 30 "patronictl -c /usr/patroni/conf/patroni.yml list"

# 2. Monitor Airflow connections
watch -n 60 "airflow db check"

# 3. Monitor HAProxy stats
curl -s http://192.168.83.129:7000/stats

# 4. Check PostgreSQL connection counts
export PGPASSWORD=airflow_pass
psql -h 192.168.83.129 -U airflow_user -p 5000 -d airflow_db -c "
SELECT count(*), state 
FROM pg_stat_activity 
WHERE datname = 'airflow_db' 
GROUP BY state;"
```

---

## **✅ Success Criteria:**

- [ ] All Airflow services running and connected to HA cluster
- [ ] Web UI accessible and functional
- [ ] DAGs can be triggered and executed successfully
- [ ] Database failover works transparently
- [ ] All original data preserved and accessible
- [ ] No connection errors in Airflow logs

---

## **📁 File Locations:**
- **Backups:** `/opt/airflow-migration/backups/`
- **Logs:** `/opt/airflow-migration/logs/`
- **Original Config:** `/opt/airflow-migration/backups/airflow.cfg.backup`

---

