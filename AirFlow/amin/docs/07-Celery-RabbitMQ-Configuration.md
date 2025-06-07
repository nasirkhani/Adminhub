# Complete Guide to Celery Distributed Execution with Airflow

## Part 1: Core Concepts and Architecture

### Understanding the Components

**1. Apache Airflow Components:**
- **Scheduler**: Reads DAGs, creates task instances, decides what to run when
- **Webserver**: Provides UI for monitoring and managing workflows
- **Executor**: Determines HOW tasks are executed (LocalExecutor, CeleryExecutor, etc.)
- **Database (PostgreSQL)**: Stores metadata, task states, DAG information

**2. Celery Distributed System:**
- **Celery**: A distributed task queue system that executes tasks across multiple machines
- **Broker (RabbitMQ)**: Message queue that holds tasks waiting to be executed
- **Workers**: Processes running on remote machines that pull tasks from queues and execute them
- **Result Backend**: Stores task results (we use PostgreSQL for this)

**3. RabbitMQ Components:**
- **Queues**: Named channels where tasks wait to be processed
- **Exchanges**: Route messages to appropriate queues
- **Virtual Hosts**: Logical separation of resources
- **Users**: Authentication for accessing RabbitMQ

### How They Work Together - Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     VM1 (Airflow Master)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Scheduler  │  │ Webserver   │  │ PostgreSQL  │            │
│  │             │  │             │  │             │            │
│  │ - Reads DAGs│  │ - Shows UI  │  │ - Metadata  │            │
│  │ - Creates   │  │ - Monitors  │  │ - Task      │            │
│  │   tasks     │  │   tasks     │  │   states    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────────────────────────────────┐  │
│  │ RabbitMQ    │  │        Celery Executor                  │  │
│  │             │  │                                         │  │
│  │ - Queues    │  │ - Converts Airflow tasks to Celery     │  │
│  │ - Messages  │  │ - Sends tasks to RabbitMQ queues       │  │
│  │ - Routing   │  │ - Monitors task completion              │  │
│  └─────────────┘  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Network
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌─────────────┐            ┌─────────────┐            ┌─────────────┐
│    VM2      │            │    VM3      │            │    VM4      │
│             │            │             │            │             │
│ ┌─────────┐ │            │ ┌─────────┐ │            │ ┌─────────┐ │
│ │ Celery  │ │            │ │ Celery  │ │            │ │ Celery  │ │
│ │ Worker  │ │            │ │ Worker  │ │            │ │ Worker  │ │
│ │         │ │            │ │         │ │            │ │         │ │
│ │Queue: A │ │            │ │Queue: B │ │            │ │Queue: C │ │
│ └─────────┘ │            │ └─────────┘ │            │ └─────────┘ │
└─────────────┘            └─────────────┘            └─────────────┘
```

### Step-by-Step Workflow Example

**1. DAG Creation Phase:**
```python
# In your DAG file
task1 = BashOperator(
    task_id='task_for_vm2',
    bash_command='hostname',
    queue='vm2_queue'  # This determines which worker will execute it
)
```

**2. Scheduling Phase (VM1 Scheduler):**
- Scheduler reads DAG file
- Creates task instance in PostgreSQL: `task_for_vm2`, status: `queued`
- Passes task to CeleryExecutor

**3. Task Distribution Phase (VM1 CeleryExecutor):**
- CeleryExecutor converts Airflow task to Celery task
- Sends message to RabbitMQ queue named `vm2_queue`
- Message contains: task code, parameters, execution context

**4. Task Execution Phase (VM2 Worker):**
- Celery worker on VM2 listens to `vm2_queue`
- Pulls task message from RabbitMQ
- Executes the bash command `hostname`
- Sends result back to PostgreSQL

**5. Result Collection Phase:**
- PostgreSQL stores: task status = `success`, result = `vm2-hostname`
- Airflow Webserver shows updated status in UI
- Scheduler can now run dependent tasks

## Part 2: Airflow Master Configuration (VM1)

Since you already have the basic installation, let's configure it for Celery distributed execution.

### Step 1: Update Airflow Configuration

Edit your `~/airflow/airflow.cfg`:

```ini
[core]
# Change executor to Celery
executor = CeleryExecutor

# Database connection (you already have this)
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

# Default timezone
default_timezone = Asia/Tehran

[celery]
# RabbitMQ broker URL (you already have this)
broker_url = amqp://airflow_user:airflow_pass@localhost:5672/airflow_host

# PostgreSQL as result backend
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

# Worker configuration
worker_concurrency = 4
celery_app_name = airflow.providers.celery.executors.celery_executor

# Default queue name
default_queue = default

[celery_kubernetes_executor]
# Leave this section as default

[webserver]
# Web server configuration
web_server_port = 8080
base_url = http://localhost:8080

[scheduler]
# How often to scan for DAG changes
dag_dir_list_interval = 300
```

### Step 2: Configure Queue Routing

Create a file `~/airflow/config/celery_config.py`:

```python
# celery_config.py - Advanced Celery configuration

from kombu import Queue

# Define available queues and their routing
task_routes = {
    # Route specific tasks to specific queues
    'airflow.executors.celery_executor.execute_command': {
        'queue': 'default'
    }
}

# Define queues with their properties
task_queues = [
    Queue('default', routing_key='default'),
    Queue('vm2_queue', routing_key='vm2'),
    Queue('vm3_queue', routing_key='vm3'),
    Queue('high_priority', routing_key='high'),
    Queue('low_priority', routing_key='low'),
]

# Worker settings
worker_prefetch_multiplier = 1  # Only take one task at a time
task_acks_late = True           # Acknowledge task after completion
task_reject_on_worker_lost = True
```

### Step 3: Network Configuration for Remote Access

Configure PostgreSQL and RabbitMQ to accept remote connections:

**PostgreSQL Configuration (already done in your installation):**
```bash
# Check if these are already configured
grep "listen_addresses" /var/lib/pgsql/data/postgresql.conf
grep "0.0.0.0/0" /var/lib/pgsql/data/pg_hba.conf
```

**RabbitMQ Network Access:**
```bash
# Enable external access
sudo rabbitmqctl set_parameter federation-upstream remote_upstream '{
    "uri": "amqp://airflow_user:airflow_pass@192.168.83.129:5672/airflow_host"
}'

# Check current users and permissions
sudo rabbitmqctl list_users
sudo rabbitmqctl list_permissions -p airflow_host
```

### Step 4: Start Services on Master (VM1)

```bash
# Start in separate terminals or use systemd services

# Terminal 1: Start Scheduler
cd ~/airflow
airflow scheduler

# Terminal 2: Start Webserver  
cd ~/airflow
airflow webserver --port 8080

# Terminal 3: Start Flower (Celery monitoring)
cd ~/airflow
airflow celery flower --port 5555

# Optional Terminal 4: Start local worker
cd ~/airflow
airflow celery worker --queues default
```

## Part 3: Remote Worker Setup (VM2, VM3, etc.)

For each remote machine that will execute tasks:

### Step 1: Install Required Packages

```bash
# Update system
sudo dnf update -y

# Install Python and development tools
sudo dnf install -y python3 python3-pip python3-devel gcc

# Install PostgreSQL client libraries
sudo dnf install -y postgresql-devel

# Install system dependencies for Celery
sudo dnf install -y libffi-devel openssl-devel
```

### Step 2: Install Airflow and Dependencies

```bash
# Install same Airflow version as master
pip3 install --user apache-airflow==2.9.0

# Install Celery support
pip3 install --user apache-airflow[celery]==2.9.0

# Install database drivers
pip3 install --user psycopg2-binary

# Install RabbitMQ client
pip3 install --user celery[librabbitmq]==5.5.0

# Verify installation
python3 -c "import airflow; print(airflow.__version__)"
```

### Step 3: Configure Worker Environment

```bash
# Create Airflow directory
mkdir -p ~/airflow

# Set environment variable permanently
echo 'export AIRFLOW_HOME=~/airflow' >> ~/.bashrc
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Create Worker Configuration

Create `~/airflow/airflow.cfg` on the worker machine:

```ini
[core]
# Use CeleryExecutor
executor = CeleryExecutor

# Connect to master's database (IMPORTANT: Use master's IP)
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

# Disable DAG loading on workers (optional optimization)
load_examples = False
dags_folder = /dev/null

[celery]
# Connect to master's RabbitMQ (IMPORTANT: Use master's IP)
broker_url = amqp://airflow_user:airflow_pass@192.168.83.129:5672/airflow_host

# Connect to master's PostgreSQL for results
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

# Worker-specific settings
worker_concurrency = 2  # Adjust based on machine capacity
celery_app_name = airflow.providers.celery.executors.celery_executor

[logging]
# Store logs locally but they won't be visible in web UI
base_log_folder = ~/airflow/logs
```

### Step 5: Start Worker with Specific Queue

```bash
# Start worker for specific queue (VM2 example)
export AIRFLOW_HOME=~/airflow
airflow celery worker --queues vm2_queue --hostname vm2_worker

# Start worker for multiple queues
airflow celery worker --queues vm2_queue,default --hostname vm2_worker

# Start worker with custom concurrency
airflow celery worker --queues vm2_queue --concurrency 4 --hostname vm2_worker
```

### Step 6: Create Systemd Service (Optional)

Create `/etc/systemd/system/airflow-worker.service`:

```ini
[Unit]
Description=Airflow Celery Worker
After=network.target

[Service]
Type=simple
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/rocky/.local/bin/airflow celery worker --queues vm2_queue --hostname vm2_worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable airflow-worker
sudo systemctl start airflow-worker
sudo systemctl status airflow-worker
```

## Part 4: Queue Management and Task Routing

### Understanding Queue Concepts

**Queue Types:**
- **Default Queue**: All tasks go here unless specified otherwise
- **Named Queues**: Target specific workers or machine types
- **Priority Queues**: High/low priority task separation
- **Functional Queues**: Group by task type (data_processing, file_transfer, etc.)

### Queue Configuration Strategies

**1. Machine-Specific Queues:**
```python
# In your DAG
task_vm2 = BashOperator(
    task_id='task_for_vm2',
    bash_command='hostname',
    queue='vm2_queue'  # Only VM2 worker will execute this
)

task_vm3 = BashOperator(
    task_id='task_for_vm3', 
    bash_command='df -h',
    queue='vm3_queue'  # Only VM3 worker will execute this
)
```

**2. Function-Specific Queues:**
```python
# Heavy computation tasks
heavy_task = PythonOperator(
    task_id='heavy_computation',
    python_callable=complex_calculation,
    queue='compute_queue'  # Workers with powerful CPUs
)

# File processing tasks
file_task = BashOperator(
    task_id='process_files',
    bash_command='convert image.jpg image.png',
    queue='file_processing_queue'  # Workers with large storage
)
```

**3. Priority-Based Queues:**
```python
urgent_task = BashOperator(
    task_id='urgent_processing',
    bash_command='process_urgent_data.sh',
    queue='high_priority',
    priority_weight=100
)
```

### Testing Queue Routing

**Test DAG for Multiple Queues:**
```python
# test_queues_dag.py
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

@dag(
    dag_id='test_queue_routing',
    schedule_interval=None,
    start_date=datetime(2024, 5, 1),
    catchup=False,
    default_args={'owner': 'rocky', 'retries': 0}
)
def test_queues():
    
    # Task for VM2
    vm2_task = BashOperator(
        task_id='test_vm2',
        bash_command='echo "Running on $(hostname) at $(date)"',
        queue='vm2_queue'
    )
    
    # Task for VM3
    vm3_task = BashOperator(
        task_id='test_vm3',
        bash_command='echo "Running on $(hostname) at $(date)"',
        queue='vm3_queue'
    )
    
    # Default queue task
    default_task = BashOperator(
        task_id='test_default',
        bash_command='echo "Running on $(hostname) at $(date)"'
        # No queue specified = default queue
    )
    
    # All tasks can run in parallel
    [vm2_task, vm3_task, default_task]

dag_instance = test_queues()
```

## Part 5: Monitoring and Troubleshooting

### Monitoring Tools

**1. Flower - Celery Monitoring (on VM1):**
```bash
# Start Flower
airflow celery flower --port 5555

# Access at: http://192.168.83.129:5555
```

**Flower shows:**
- Active workers and their queues
- Task execution statistics
- Worker resource usage
- Queue lengths and task distribution

**2. RabbitMQ Management (on VM1):**
```bash
# Access at: http://192.168.83.129:15672
# Login: airflow_user / airflow_pass
```

**RabbitMQ Management shows:**
- Queue depths (how many tasks waiting)
- Message rates
- Connection status
- Exchange routing

**3. Airflow Web UI (on VM1):**
```bash
# Access at: http://192.168.83.129:8080
```

### Troubleshooting Common Issues

**1. Worker Can't Connect to RabbitMQ:**
```bash
# Check network connectivity
telnet 192.168.83.129 5672

# Check RabbitMQ status
sudo systemctl status rabbitmq-server

# Check firewall
sudo firewall-cmd --list-all
```

**2. Worker Can't Connect to PostgreSQL:**
```bash
# Test database connection
psql -h 192.168.83.129 -U airflow_user -d airflow_db

# Check PostgreSQL logs
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log
```

**3. Tasks Not Being Picked Up:**
```bash
# Check worker status
airflow celery worker --queues vm2_queue --hostname test_worker

# Check if worker is registered
python3 -c "
from celery import Celery
app = Celery('airflow.providers.celery.executors.celery_executor')
app.config_from_object('airflow.providers.celery.executors.default_celery')
inspect = app.control.inspect()
print('Active workers:', inspect.active())
print('Registered tasks:', inspect.registered())
"
```

### Performance Optimization

**1. Worker Concurrency:**
```bash
# High-CPU machine
airflow celery worker --queues compute_queue --concurrency 8

# Low-resource machine  
airflow celery worker --queues file_queue --concurrency 2
```

**2. Queue Prefetch:**
```ini
# In airflow.cfg
[celery]
worker_prefetch_multiplier = 1  # Take one task at a time
```

**3. Resource Isolation:**
```bash
# Limit memory usage
airflow celery worker --queues vm2_queue --max-memory-per-child 1000000

# Limit task count per worker
airflow celery worker --queues vm2_queue --max-tasks-per-child 100
```

## Part 6: Advanced Configuration Examples

### Multi-Environment Setup

**Production Configuration:**
```python
# production_queues.py
PRODUCTION_QUEUES = {
    'web_servers': ['web1_queue', 'web2_queue', 'web3_queue'],
    'db_servers': ['db1_queue', 'db2_queue'], 
    'compute_cluster': ['compute1_queue', 'compute2_queue', 'compute3_queue'],
    'storage_nodes': ['storage1_queue', 'storage2_queue']
}

# Start workers with multiple queues
# airflow celery worker --queues web1_queue,default --hostname web1_worker
```

### Security Configuration

**SSL/TLS for RabbitMQ:**
```ini
# In airflow.cfg
[celery]
broker_url = amqps://airflow_user:airflow_pass@192.168.83.129:5671/airflow_host
broker_use_ssl = {
    'keyfile': '/path/to/client/key.pem',
    'certfile': '/path/to/client/cert.pem',
    'ca_certs': '/path/to/ca/cert.pem'
}
```

This complete setup gives you a robust, scalable Airflow deployment with Celery distributed execution across multiple machines!
