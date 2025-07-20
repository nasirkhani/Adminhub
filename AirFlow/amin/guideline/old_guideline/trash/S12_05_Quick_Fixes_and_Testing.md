# S12 Quick Fixes and Testing

## Fix 1: Enable Flower API Access

```bash
# On VM1
sudo vi /etc/systemd/system/airflow-flower.service
```

Add this line under [Service]:
```ini
Environment="FLOWER_UNAUTHENTICATED_API=true"
```

Restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-flower
```

## Fix 2: Test Queue Creation

Create and run this test script on VM1:

```bash
# Create S12_test_queue.py
cat > ~/S12_test_queue.py << 'EOF'
import pika

# Connect to RabbitMQ
credentials = pika.PlainCredentials('airflow_user', 'airflow_pass')
parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    virtual_host='airflow_host',
    credentials=credentials
)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue='card_processing_queue', durable=True)

# Send a test message
channel.basic_publish(
    exchange='',
    routing_key='card_processing_queue',
    body='Test message for S12'
)

print("Sent test message to card_processing_queue")
connection.close()

# Now check if queue exists
import subprocess
result = subprocess.run(['sudo', 'rabbitmqctl', 'list_queues'], capture_output=True, text=True)
print("\nCurrent queues:")
print(result.stdout)
EOF

python3 ~/S12_test_queue.py
```

## Fix 3: Deploy and Test

1. **Deploy the concurrent DAG**:
```bash
# On VM2
cd /srv/airflow/dags
# Copy the S12_card_processing_concurrent.py content from artifact
```

2. **Restart Worker with Debug**:
```bash
# On VM4
sudo journalctl -u airflow-worker -f
```

3. **Trigger DAG and Watch**:
- Go to http://192.168.83.129:8080
- Trigger S12_card_processing_concurrent
- Watch logs on VM4
- Check Flower at http://192.168.83.129:5555

## Understanding Concurrency in Action

When you trigger the DAG:

1. **Sensor Phase**: 1 task checking for files
2. **Transfer Phase**: 5 tasks start (if 5 files found)
   - With concurrency=5, all run simultaneously
   - Watch multiple "CONCURRENT" messages in logs
3. **Validation Phase**: 5 tasks run in parallel
4. **Processing Phase**: 5 tasks run in parallel
5. **Report Phase**: 1 task waits for all to complete

Total tasks: 17 (1+5+5+5+1)
Max concurrent: 5 (worker limit)

## What You Should See

In Flower (http://192.168.83.129:5555/tasks):
- Multiple tasks in "STARTED" state
- Some tasks in "PENDING" if > 5 running
- Tasks transitioning through states

In RabbitMQ:
```bash
# Should see messages in queue when tasks are pending
sudo rabbitmqctl list_queues name messages consumers
# Example output:
# card_processing_queue    3    1
# default                  0    1
```

The "3" means 3 tasks waiting in queue!
