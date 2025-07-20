You're absolutely right! I apologize for giving outdated commands. Based on the Airflow 2.9 documentation you provided, here are the correct monitoring commands:

## Correct Airflow 2.9 Monitoring Commands

### 1. **Check Celery Workers Status**
```bash
# Check if celery worker jobs are running
airflow jobs check --job-type SchedulerJob --local
airflow jobs check --job-type LocalTaskJob --allow-multiple --limit 10
```

### 2. **Monitor Task States**
```bash
# Get all task instances status for a specific DAG run
airflow tasks states-for-dag-run simple_remote_execution_fixed manual__2025-06-09T11:06:55.178339+00:00

# Check specific task state
airflow tasks state simple_remote_execution_fixed get_hostname manual__2025-06-09T11:06:55.178339+00:00

# List all tasks in your DAG
airflow tasks list simple_remote_execution_fixed --tree
```

### 3. **Monitor DAG Runs**
```bash
# List recent DAG runs
airflow dags list-runs -d simple_remote_execution_fixed --limit 5

# Get state of a DAG run
airflow dags state simple_remote_execution_fixed manual__2025-06-09T11:06:55.178339+00:00
```

### 4. **Use Flower (Built into Airflow)**
```bash
# Flower is the official way to monitor Celery in Airflow 2.9
# It's already running on port 5555
# Access it at: http://192.168.83.129:5555

# If not running, start it:
airflow celery flower --port 5555
```

### 5. **Real-time Monitoring Script for Airflow 2.9**
```bash
cat > ~/monitor_airflow_2.9.sh << 'EOF'
#!/bin/bash

echo "=== ACTIVE JOBS ==="
airflow jobs check --job-type LocalTaskJob --allow-multiple --limit 20

echo -e "\n=== RECENT DAG RUNS ==="
airflow dags list-runs -d simple_remote_execution_fixed --limit 5

echo -e "\n=== RABBITMQ QUEUES ==="
sudo rabbitmqctl list_queues name messages consumers

echo -e "\n=== LATEST RUN TASK STATES ==="
# Get the latest run_id
LATEST_RUN=$(airflow dags list-runs -d simple_remote_execution_fixed --limit 1 -o plain | tail -n 1 | awk '{print $3}')
if [ ! -z "$LATEST_RUN" ]; then
    airflow tasks states-for-dag-run simple_remote_execution_fixed "$LATEST_RUN"
fi
EOF

chmod +x ~/monitor_airflow_2.9.sh

# Run it
./monitor_airflow_2.9.sh

# Or watch it continuously
watch -n 2 './monitor_airflow_2.9.sh'
```

### 6. **For Queue Monitoring**
Since Airflow 2.9 doesn't have `celery inspect`, use:

```bash
# RabbitMQ Management UI (best option)
# http://192.168.83.129:15672
# Login: airflow_user / airflow_pass

# Or via command line
sudo rabbitmqctl list_queues name messages messages_ready messages_unacknowledged consumers

# Watch queues
watch -n 1 'sudo rabbitmqctl list_queues name messages consumers'
```

### 7. **Check Pool Usage**
```bash
# List pools and their usage
airflow pools list

# Get specific pool details
airflow pools get default_pool
```

The main monitoring tools in Airflow 2.9 are:
- **Flower** (`http://192.168.83.129:5555`) - For Celery/worker monitoring
- **RabbitMQ Management** (`http://192.168.83.129:15672`) - For queue monitoring  
- **Airflow Web UI** (`http://192.168.83.129:8080`) - For DAG/task monitoring
- **CLI commands** - For scripted monitoring using the commands above

Thank you for providing the documentation - I'll make sure all future commands are compatible with Airflow 2.9!
