I'll search for information about disabling global QoS in Celery with RabbitMQ for your specific setup.Based on my research, here's a comprehensive guide on **disabling global QoS in Celery with RabbitMQ** for your Airflow 2.9 + Celery 5.5 + RabbitMQ 4 setup:

## 🎯 **Automatic Solution (Recommended - Celery 5.5+)**

Celery 5.5 introduced automatic detection and handling of quorum queues with the `worker_detect_quorum_queues` setting, which is **enabled by default**. When enabled, the worker automatically detects if any queues are quorum queues and disables global QoS accordingly.

### **Method 1: Enable Quorum Queues (Automatic Detection)**

Add this to your Airflow configuration or celeryconfig.py:

```python
# In your celeryconfig.py or airflow.cfg [celery] section
from kombu import Queue

# Enable quorum queues
task_default_queue_type = "quorum"
task_default_exchange_type = "topic"
broker_transport_options = {"confirm_publish": True}

# Automatic detection is enabled by default
worker_detect_quorum_queues = True  # This is the default

# Optional: Define specific quorum queues
task_queues = [
    Queue('default', queue_arguments={'x-queue-type': 'quorum'}),
    Queue('high_priority', queue_arguments={'x-queue-type': 'quorum'}),
]
```

**In airflow.cfg:**
```ini
[celery]
broker_transport_options = {"confirm_publish": True}
worker_detect_quorum_queues = True
```

---

## 🔧 **Manual Solutions (If needed)**

### **Method 2: Custom Celery Configuration Class**

If you need to manually disable global QoS, you can create a custom configuration class that hooks into Celery's worker bootstrap process:

```python
# Create a file: celery_custom_config.py
from celery import bootsteps
from celery.worker.consumer.consumer import QoS

class NoChannelGlobalQoS(bootsteps.StartStopStep):
    """Disable global QoS for RabbitMQ compatibility"""
    requires = {'celery.worker.consumer.tasks:Tasks'}
    
    def start(self, c):
        qos_global = False  # Disable global QoS
        c.connection.default_channel.basic_qos(
            0, c.initial_prefetch_count, qos_global
        )
        
        def set_prefetch_count(prefetch_count):
            return c.task_consumer.qos(
                prefetch_count=prefetch_count,
                apply_global=qos_global,  # Set to False
            )
        
        c.qos = QoS(set_prefetch_count, c.initial_prefetch_count)

# In your celeryconfig.py
from celery import Celery
app = Celery('airflow.executors.celery_executor')

# Add the custom step
app.steps['consumer'].add(NoChannelGlobalQoS)
```

---

### **Method 3: Airflow Configuration Approach**

Modify your **airflow.cfg** file:

```ini
[celery]
# Basic broker settings
broker_url = amqp://airflow_user:airflow_pass@localhost:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

# Disable global QoS settings
broker_transport_options = {"confirm_publish": True}
worker_detect_quorum_queues = True

# Optional: Force quorum queues
task_default_queue_type = quorum
```

---

## ⚠️ **Important Considerations**

### **Limitations When Global QoS is Disabled:**

When global QoS is disabled, several Celery features won't work as expected:

1. **Autoscaling** - Won't work because it relies on changing prefetch counts
2. **worker_enable_prefetch_count_reduction** - Will be a no-op
3. **ETA/Countdown tasks** - Will block the worker until execution time

### **RabbitMQ 4 Compatibility:**

RabbitMQ 4.0 has deprecated some features including global_qos. You may see warnings like: `Deprecated features: global_qos`. To handle this properly, ensure your configuration explicitly disables global QoS.

---

## 🚀 **Complete Working Example**

Here's a complete configuration for your setup:

**1. Update airflow.cfg:**
```ini
[core]
executor = CeleryExecutor

[celery]
broker_url = amqp://airflow_user:airflow_pass@localhost:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

# Disable global QoS
broker_transport_options = {"confirm_publish": True}
worker_detect_quorum_queues = True
task_default_queue_type = quorum
```

**2. Create celeryconfig.py in your AIRFLOW_HOME:**
```python
from kombu import Queue

# Broker settings
broker_url = 'amqp://airflow_user:airflow_pass@localhost:5672/airflow_host'
result_backend = 'db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db'

# Disable global QoS
broker_transport_options = {"confirm_publish": True}
worker_detect_quorum_queues = True
task_default_queue_type = "quorum"

# Define queues with quorum type
task_queues = [
    Queue('default', queue_arguments={'x-queue-type': 'quorum'}),
    Queue('high_priority', queue_arguments={'x-queue-type': 'quorum'}),
    Queue('card_processing_queue', queue_arguments={'x-queue-type': 'quorum'}),
]

# Other important settings
task_acks_late = True
worker_prefetch_multiplier = 1
```

---

## 🔍 **Verification**

**1. Check if settings are applied:**
```bash
# Start Airflow celery worker with verbose logging
airflow celery worker --loglevel=info

# Look for messages like:
# "Quorum queues detected, disabling global QoS"
```

**2. Monitor RabbitMQ:**
```bash
# Check queue types
sudo rabbitmqctl list_queues name type

# Should show queues with type "quorum"
```

**3. Test with Flower:**
```bash
airflow celery flower
# Visit http://localhost:5555 to monitor workers
```

---

## 📝 **Summary**

For your **Airflow 2.9 + Celery 5.5 + RabbitMQ 4** setup:

1. **Use Method 1** (automatic detection) - it's the cleanest approach
2. **Enable quorum queues** with `task_default_queue_type = "quorum"`  
3. **Set** `broker_transport_options = {"confirm_publish": True}`
4. **Keep** `worker_detect_quorum_queues = True` (default)

This configuration will automatically disable global QoS when quorum queues are detected, solving compatibility issues with RabbitMQ 4 while maintaining Airflow functionality.
