## **Implementation Instructions for Your Order**

### **S05 (Airflow Installation) - Modifications:**

**1. Use LocalExecutor temporarily:**
```ini
[core]
executor = LocalExecutor
dags_folder = /home/rocky/airflow/dags

# Skip [celery] section completely
```

**2. Create local DAG directory:**
```bash
mkdir -p ~/airflow/dags  # Don't use NFS symlink yet
```

**3. Enable services but don't start:**
```bash
sudo systemctl enable airflow-scheduler airflow-webserver
# Don't start services yet
```

### **S03 (RabbitMQ) - Add this step:**
```bash
# After RabbitMQ setup, update all Airflow nodes:
sed -i 's/executor = LocalExecutor/executor = CeleryExecutor/' ~/airflow/airflow.cfg

# Add celery section to airflow.cfg:
cat >> ~/airflow/airflow.cfg << EOF
[celery]
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host;amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.210:5000/airflow_db
EOF
```

### **S04 (NFS) - Add this step:**
```bash
# After NFS setup, replace local DAG directory:
rm -rf ~/airflow/dags
ln -s /mnt/airflow-dags ~/airflow/dags
```

### **S06 (Integration) - Start services:**
```bash
# Now start all Airflow services
sudo systemctl start airflow-scheduler airflow-webserver airflow-worker
```

**Your order is correct. Use these modifications during implementation.**
