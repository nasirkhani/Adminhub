# S12 Monitoring Configuration and Fixes

## Issue 1: RabbitMQ Queue Monitoring

### Understanding Queue Creation
Queues in RabbitMQ are created only when:
1. A task is sent to that queue
2. A worker declares it's listening to that queue

### Fix: Check All Queues First

```bash
# On VM1 - Check all queues without grep
sudo rabbitmqctl list_queues name messages consumers

# Also check queue details
sudo rabbitmqctl list_queues name messages consumers messages_ready messages_unacknowledged

# Check if workers are connected
sudo rabbitmqctl list_consumers
```

### Real-time Queue Monitoring Script

Create monitoring script on VM1:
```bash
# Create S12_queue_monitor.sh
vi ~/S12_queue_monitor.sh
```

Content:
```bash
#!/bin/bash
# S12_queue_monitor.sh - Real-time queue monitoring

while true; do
    clear
    echo "=== RabbitMQ Queue Status - $(date) ==="
    echo ""
    echo "Queue Name            | Messages | Ready | Unacked | Consumers"
    echo "-------------------- | -------- | ----- | ------- | ---------"
    
    sudo rabbitmqctl list_queues name messages messages_ready messages_unacknowledged consumers | \
    tail -n +2 | \
    awk '{printf "%-20s | %8s | %5s | %7s | %9s\n", $1, $2, $3, $4, $5}'
    
    echo ""
    echo "=== Active Consumers ==="
    sudo rabbitmqctl list_consumers queue_name channel_pid consumer_tag | tail -n +2
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 2
done
```

Make executable:
```bash
chmod +x ~/S12_queue_monitor.sh
./S12_queue_monitor.sh
```

### Alternative: RabbitMQ Management UI
```bash
# Access RabbitMQ Management UI
# http://192.168.83.129:15672
# Login: airflow_user / airflow_pass
# Navigate to Queues tab for visual monitoring
```

## Issue 2: Flower API Authentication

### Fix 1: Update Flower Service with Environment Variable

On VM1, edit the Flower service:
```bash
sudo vi /etc/systemd/system/airflow-flower.service
```

Add environment variable:
```ini
[Unit]
Description=Apache Airflow Flower (Celery Monitor)
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rocky/airflow
Environment=FLOWER_UNAUTHENTICATED_API=true
WorkingDirectory=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
SyslogIdentifier=airflow-flower

[Install]
WantedBy=multi-user.target
```

Restart Flower:
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-flower
sudo systemctl status airflow-flower
```

### Fix 2: Flower Broker Configuration

Ensure Flower can connect to RabbitMQ by checking logs:
```bash
sudo journalctl -u airflow-flower -n 50

# Look for connection messages like:
# "Connected to amqp://airflow_user:**@192.168.83.129:5672/airflow_host"
```

### Alternative Flower Monitoring Commands

```bash
# Use curl to access Flower API
curl http://localhost:5555/api/workers
curl http://localhost:5555/api/queues/length
curl http://localhost:5555/api/tasks
```

## Issue 3: Worker Queue Declaration

The worker needs to properly declare queues. Update worker service on VM4:

```bash
# On VM4
sudo vi /etc/systemd/system/airflow-worker.service
```

Ensure proper queue declaration:
```ini
ExecStart=/bin/bash -c 'exec /home/rocky/.local/bin/airflow celery worker --queues card_processing_queue,remote_tasks,default --concurrency 5 --hostname worker1@%h'
```

Restart worker:
```bash
sudo systemctl restart airflow-worker
```

## Comprehensive Monitoring Dashboard

Create S12_monitoring_dashboard.py on VM1:
```python
#!/usr/bin/env python3
"""
S12_monitoring_dashboard.py - Comprehensive Airflow monitoring
"""
import subprocess
import json
import time
import os

def clear_screen():
    os.system('clear')

def get_rabbitmq_queues():
    """Get RabbitMQ queue statistics"""
    try:
        cmd = "sudo rabbitmqctl list_queues name messages consumers --formatter json"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return json.loads(result.stdout)
    except:
        return []

def get_flower_workers():
    """Get worker status from Flower API"""
    try:
        cmd = "curl -s http://localhost:5555/api/workers"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except:
        return {}

def get_active_tasks():
    """Get active tasks from Flower"""
    try:
        cmd = "curl -s http://localhost:5555/api/tasks?state=STARTED"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except:
        return {}

def main():
    while True:
        clear_screen()
        print("=== S12 AIRFLOW MONITORING DASHBOARD ===")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # RabbitMQ Queues
        print("\n📊 RABBITMQ QUEUES:")
        print("-" * 50)
        queues = get_rabbitmq_queues()
        if queues:
            print(f"{'Queue':<30} {'Messages':<10} {'Consumers':<10}")
            for q in queues:
                print(f"{q['name']:<30} {q['messages']:<10} {q['consumers']:<10}")
        else:
            print("No queue data available")
        
        # Workers
        print("\n👷 CELERY WORKERS:")
        print("-" * 50)
        workers = get_flower_workers()
        for worker_name, worker_info in workers.items():
            status = worker_info.get('status', False)
            active = worker_info.get('active', 0)
            processed = worker_info.get('processed', 0)
            print(f"{worker_name}: {'🟢 Online' if status else '🔴 Offline'} | Active: {active} | Processed: {processed}")
        
        # Active Tasks
        print("\n⚡ ACTIVE TASKS:")
        print("-" * 50)
        tasks = get_active_tasks()
        if tasks:
            for task_id, task_info in list(tasks.items())[:5]:  # Show only 5 recent
                name = task_info.get('name', 'Unknown')
                state = task_info.get('state', 'Unknown')
                print(f"{name}: {state}")
        else:
            print("No active tasks")
        
        print("\n[Press Ctrl+C to exit]")
        time.sleep(3)

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x ~/S12_monitoring_dashboard.py
```

## Testing Queue Creation

To ensure queues are created, trigger a simple test:

```bash
# Create S12_test_queue.py
cat > ~/S12_test_queue.py << 'EOF'
from celery import Celery

# Connect to Airflow's Celery
app = Celery('airflow.providers.celery.executors.celery_executor')
app.config_from_object('celery.app.defaults')

# Send a test message to card_processing_queue
result = app.send_task(
    'test.task',
    args=['test'],
    queue='card_processing_queue',
    routing_key='card_processing_queue'
)

print(f"Sent test task to card_processing_queue: {result.id}")
EOF

python3 ~/S12_test_queue.py
```
