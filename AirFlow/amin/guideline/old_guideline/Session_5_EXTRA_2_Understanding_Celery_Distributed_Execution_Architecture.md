# Understanding Celery Distributed Execution Architecture

Let me explain the core concepts and workflow of Celery distributed execution, then answer your setup questions.

## Core Concept: How Celery Distributed Execution Works

### The Components and Their Relationships

```
VM_1 (192.168.83.129) - MAIN MACHINE
├── Airflow Webserver    (User Interface)
├── Airflow Scheduler    (Task Scheduler - THE BRAIN)
├── PostgreSQL          (Metadata Database - Task States)
├── RabbitMQ            (Message Broker - Task Queue)
└── Celery Executor     (Task Distribution Engine)

VM_2 (192.168.83.130) - WORKER MACHINE 1
└── ??? (What needs to be here?)

VM_3 (192.168.83.131) - WORKER MACHINE 2  
└── ??? (What needs to be here?)
```

### The Workflow Step-by-Step

**Step 1: Task Creation**
```
Scheduler (VM_1) reads DAG → Creates task instance → Stores in PostgreSQL
```

**Step 2: Task Queuing**
```
Celery Executor (VM_1) → Sends task to RabbitMQ queue → "Task ready for execution"
```

**Step 3: Task Pickup** 
```
Celery Worker (VM_2 or VM_3) → Pulls task from RabbitMQ → "I'll execute this task"
```

**Step 4: Task Execution**
```
Celery Worker executes Python/Bash code → Sends results back to PostgreSQL
```

**Step 5: Status Update**
```
Webserver (VM_1) → Reads status from PostgreSQL → Shows results in UI
```

## What Needs to Be Installed on Target Machines?

**Answer: YES, you need to install Airflow components on VM_2 and VM_3**

Here's what needs to be installed on each target machine:

### Installation Required on VM_2 and VM_3:

```bash
# On VM_2 and VM_3, install these components:

# 1. Python (same version as VM_1)
sudo yum install python3 python3-pip

# 2. Apache Airflow (same version as VM_1)
pip install apache-airflow==2.9.0

# 3. Celery support
pip install apache-airflow[celery]

# 4. Database connection packages (to connect to VM_1's PostgreSQL)
pip install psycopg2-binary

# 5. RabbitMQ client packages (to connect to VM_1's RabbitMQ)  
pip install celery[librabbitmq]
```

### Configuration Required on VM_2 and VM_3:

Create `/home/rocky/airflow/airflow.cfg` on each target machine:

```ini
# airflow.cfg on VM_2 and VM_3
[core]
executor = CeleryExecutor
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

[celery]
broker_url = amqp://airflow_user:airflow_pass@192.168.83.129:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

# Optional: Specify which queues this worker should handle
worker_concurrency = 4
```

### Starting Workers on Target Machines:

```bash
# On VM_2 - start a Celery worker
export AIRFLOW_HOME=/home/rocky/airflow
airflow celery worker -q vm2_queue

# On VM_3 - start a Celery worker  
export AIRFLOW_HOME=/home/rocky/airflow
airflow celery worker -q vm3_queue
```

## Complete Architecture After Setup

```
VM_1 (192.168.83.129) - CONTROL CENTER
├── Airflow Webserver ─────┐
├── Airflow Scheduler ─────┤
├── PostgreSQL ────────────┤── All manage and coordinate tasks
├── RabbitMQ ──────────────┤
└── Celery Executor ───────┘

         ║ (Network Connection)
         ║ 
    ┌────────────────────────────┐
    ▼                            ▼

VM_2 (192.168.83.130)      VM_3 (192.168.83.131)
└── Celery Worker           └── Celery Worker
    (Executes tasks)            (Executes tasks)
```

## Example: How a Task Flows Through the System

Let's trace a simple task through the system:

### DAG Definition (on VM_1):
```python
# sample_distributed_dag.py
from airflow.operators.bash import BashOperator

task1 = BashOperator(
    task_id='check_hostname_vm2',
    bash_command='hostname',
    queue='vm2_queue'  # Send this task to VM_2
)

task2 = BashOperator(
    task_id='check_hostname_vm3', 
    bash_command='hostname',
    queue='vm3_queue'  # Send this task to VM_3
)
```

### What Happens When You Run This DAG:

**1. Scheduler Action (VM_1):**
```
Scheduler reads DAG → Creates 2 task instances → Stores in PostgreSQL:
- Task: check_hostname_vm2, Status: queued, Queue: vm2_queue
- Task: check_hostname_vm3, Status: queued, Queue: vm3_queue
```

**2. Celery Executor Action (VM_1):**
```
Celery Executor → Sends to RabbitMQ:
- Message to vm2_queue: "Execute 'hostname' command"
- Message to vm3_queue: "Execute 'hostname' command"
```

**3. Worker Actions:**
```
VM_2 Celery Worker → Pulls from vm2_queue → Executes 'hostname' → Returns "vm2-hostname"
VM_3 Celery Worker → Pulls from vm3_queue → Executes 'hostname' → Returns "vm3-hostname"
```

**4. Results Storage:**
```
Both workers → Send results to PostgreSQL on VM_1:
- Task check_hostname_vm2: Status=success, Result="vm2-hostname"
- Task check_hostname_vm3: Status=success, Result="vm3-hostname"
```

**5. UI Display:**
```
Webserver (VM_1) → Reads from PostgreSQL → Shows both tasks as successful
```

## Key Points to Understand:

1. **Workers Need Airflow**: Target machines must have Airflow installed to run as Celery workers
2. **Shared Configuration**: All machines connect to the same database and message broker
3. **Task Distribution**: Tasks are distributed via RabbitMQ queues
4. **Centralized Management**: Everything is controlled from VM_1, but execution happens on workers

## Alternative: If You Don't Want to Install Airflow on Target Machines

If you prefer to keep VM_2 and VM_3 "naked," use the **SSH approach** we discussed earlier instead of Celery workers. With SSH:

- VM_2 and VM_3 remain completely clean
- Only need SSH access configured
- Tasks execute via SSH commands from VM_1
- No Airflow installation required on target machines

## Summary

**For Celery Distributed Execution:**
- ✅ **VM_1**: Already set up correctly
- ❌ **VM_2 & VM_3**: Need Airflow + Celery worker installation
- 📊 **Result**: True distributed processing with automatic load balancing

**For SSH Approach:**
- ✅ **VM_1**: Use existing setup
- ✅ **VM_2 & VM_3**: Keep completely naked, just need SSH access
- 📊 **Result**: Remote execution without distributed infrastructure

Which approach would you prefer to implement? The Celery approach gives you more sophisticated distributed processing, while SSH keeps your target machines clean and simple.
