**Perfect diagnosis!** The HA **IS working on RabbitMQ side** (queues failed over to mq2), but **Celery worker doesn't know about other nodes**!

## 🚨 **Root Cause:**
Your `broker_url` only points to **mq1**:
```ini
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host
```

When **mq1 fails**, Celery has **no idea** that mq2 and mq3 exist!

---

## 🔧 **Solution: Configure Celery for Multiple Brokers**

### **Step 1: Update broker_url for Failover**

```ini
# In airflow.cfg on ALL VMs (VM1, VM2, VM4):
[celery]
# Use semicolon separator (this worked for you before):
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host;amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host

result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db
```

### **Step 2: Alternative - Use Celery's Built-in Failover**

If semicolons still cause issues:

```ini
[celery]
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host

# Add backup brokers:
broker_transport_options = {
    "fanout_prefix": True,
    "fanout_patterns": True,
    "master_name": "mymaster"
}

# Or explicitly define failover hosts:
broker_failover_strategy = "round-robin"
broker_host = mq1,mq2,mq3
broker_port = 5672
broker_user = airflow_user
broker_password = airflow_pass
broker_vhost = airflow_host
```

### **Step 3: Test Configuration**

```bash
# Restart worker with new config:
sudo systemctl restart airflow-worker

# Check worker can see all brokers:
sudo journalctl -u airflow-worker -f --lines=10

# Should show connection attempts to multiple hosts
```

---

## 🎯 **Step 4: Proper Failover Test**

```bash
# 1. Start with all nodes up:
sudo systemctl start rabbitmq-server  # On mq1, mq2, mq3

# 2. Trigger a DAG:
airflow dags trigger S12_card_processing_workflow

# 3. While task is running, stop mq1:
sudo systemctl stop rabbitmq-server  # On mq1

# 4. Worker should automatically connect to mq2:
sudo journalctl -u airflow-worker -f --lines=5

# Expected logs:
# [ERROR] Cannot connect to mq1: Connection refused
# [INFO] Will retry using next failover
# [INFO] Connected to amqp://airflow_user:**@mq2:5672/airflow_host
```

---

## 🔧 **Step 5: Alternative Broker Configuration (Most Reliable)**

If the semicolon approach has issues, use **environment variables**:

```bash
# On VM4 (worker), set multiple broker URLs:
sudo systemctl edit airflow-worker

# Add:
[Service]
Environment="CELERY_BROKER_URL=amqp://airflow_user:airflow_pass@mq1:5672/airflow_host"
Environment="CELERY_BROKER_BACKUP=amqp://airflow_user:airflow_pass@mq2:5672/airflow_host;amqp://airflow_user:airflow_pass@mq3:5672/airflow_host"
```

Or use **Celery's native configuration file**:

```bash
# Create /home/rocky/celeryconfig.py:
cat > /home/rocky/celeryconfig.py << 'EOF'
broker_url = [
    'amqp://airflow_user:airflow_pass@mq1:5672/airflow_host',
    'amqp://airflow_user:airflow_pass@mq2:5672/airflow_host', 
    'amqp://airflow_user:airflow_pass@mq3:5672/airflow_host'
]

broker_transport_options = {
    'confirm_publish': True,
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.2,
}
EOF

# Update airflow.cfg to use this config:
# In [celery] section:
# celery_config_options = celeryconfig
```

---

## 🎯 **What Should Happen After Fix:**

### **✅ Successful Failover Logs:**
```
[WARNING] Connection to broker lost. Trying to re-establish...  
[ERROR] Cannot connect to mq1: Connection refused
[INFO] Will retry using next failover
[INFO] Connected to amqp://airflow_user:**@mq2:5672/airflow_host
[INFO] celery@worker1 ready.
```

### **✅ Task Continues Processing:**
The running task should **NOT fail** - it should continue processing on the new broker.

---

## 🎯 **Recommended Solution:**

**Start with Step 1** (semicolon broker_url) since you know that format works. If it causes parsing issues, use **Step 5** (Celery config file).

The key is getting Celery to know about **all three RabbitMQ nodes** instead of just mq1. Try the semicolon approach first and let me know what the worker logs show!

===============================================================  





**Great observation!** The mirroring IS actually configured correctly (you can see `slave_pids` showing mq2 and mq3), but there are **cluster health issues** causing the timeouts.

## 🔍 **Understanding What You're Seeing:**

### **✅ Mirroring IS Working:**
```
card_processing_queue   [<rabbit@mq3.1751893145.2236.0>, <rabbit@mq2.1751893141.2365.0>]
```
This shows `card_processing_queue` **master is on mq1** with **slaves on mq2 and mq3**.

### **❌ Cluster Performance Issues:**
The timeouts indicate cluster communication problems, not mirroring problems.

---

## 🔧 **Step 1: Check Cluster Health**

```bash
# On ALL RabbitMQ nodes, check cluster status:
sudo rabbitmqctl cluster_status

# Check if all nodes are actually running:
sudo rabbitmqctl eval 'rabbit_mnesia:cluster_nodes(all).'

# Check network partitions (critical):
sudo rabbitmqctl eval 'rabbit_mnesia:cluster_nodes(running).'
```

## 🔧 **Step 2: Fix Cluster Communication Issues**

### **Check Network Connectivity:**
```bash
# From each RabbitMQ node, test connectivity:
# On mq1:
telnet mq2 25672
telnet mq3 25672

# On mq2:
telnet mq1 25672  
telnet mq3 25672

# On mq3:
telnet mq1 25672
telnet mq2 25672
```

### **Check Firewall (Critical for Erlang Distribution):**
```bash
# On ALL RabbitMQ VMs, add missing Erlang distribution ports:
sudo firewall-cmd --permanent --add-port=35672-35682/tcp  # Erlang distribution
sudo firewall-cmd --reload

# Restart RabbitMQ services in order:
sudo systemctl restart rabbitmq-server  # On mq1
sleep 10
sudo systemctl restart rabbitmq-server  # On mq2  
sleep 10
sudo systemctl restart rabbitmq-server  # On mq3
```

---

## 📊 **Step 3: How to Check Master/Slave Status**

### **Method A: Check Queue Leadership**
```bash
# This shows which node is the MASTER (no timeout issues):
sudo rabbitmqctl list_queues name pid policy --vhost airflow_host --timeout 30

# Example output:
# card_processing_queue    <rabbit@mq1.123.456.0>    ha-all    ← mq1 is master
# default                  <rabbit@mq2.789.012.0>    ha-all    ← mq2 is master
```

### **Method B: Use Management API (More Reliable)**
```bash
# Check via HTTP API (works even with cluster issues):
curl -u airflow_user:airflow_pass http://mq1:15672/api/queues/airflow_host

# This shows detailed queue info including master node
```

---

## ⚡ **Step 4: Test Instant Failover**

### **A. Understanding RabbitMQ 3.x Failover:**

**Yes, failover is nearly instant** when properly configured:
- **Master fails** → **Slave promoted to master** (1-2 seconds)
- **In-flight messages** → **Preserved** (not lost)
- **Consumer connections** → **Automatically reconnect** to new master

### **B. Proper Failover Test:**
```bash
# 1. Start a long-running task:
airflow dags trigger S12_card_processing_workflow

# 2. While task is running, check which node hosts the queue:
sudo timeout 10 rabbitmqctl list_queues name pid --vhost airflow_host

# 3. Stop the master node (from step 2):
sudo systemctl stop rabbitmq-server  # On master node

# 4. Check worker logs for failover (should be instant):
sudo journalctl -u airflow-worker -f --lines=10

# 5. Check new master:
sudo timeout 10 rabbitmqctl list_queues name pid --vhost airflow_host  # On surviving nodes
```

---

## 🔧 **Step 5: Fix the Timeout Issues**

### **Option A: Restart Cluster Clean**
```bash
# Stop all RabbitMQ nodes:
sudo systemctl stop rabbitmq-server  # On mq1, mq2, mq3

# Start in order with delays:
sudo systemctl start rabbitmq-server  # On mq1
sleep 15

sudo systemctl start rabbitmq-server  # On mq2
sleep 10

sudo systemctl start rabbitmq-server  # On mq3
sleep 10

# Verify cluster:
sudo rabbitmqctl cluster_status
```

### **Option B: Use Shorter Timeouts**
```bash
# Use shorter timeouts to avoid hanging:
sudo rabbitmqctl list_queues name policy --vhost airflow_host --timeout 10

# Check unresponsive queues:
sudo rabbitmqctl list_unresponsive_queues --vhost airflow_host
```

---

## 🎯 **Expected Healthy Output:**

### **✅ Healthy Cluster:**
```bash
# Should complete quickly (< 5 seconds):
sudo rabbitmqctl list_queues name pid policy --vhost airflow_host

# Output:
card_processing_queue    <rabbit@mq1.xxx.xxx.0>    ha-all
default                  <rabbit@mq1.xxx.xxx.0>    ha-all
remote_tasks            <rabbit@mq2.xxx.xxx.0>    ha-all
```

### **✅ Instant Failover Test:**
```bash
# Worker logs should show:
[WARNING] Connection to broker lost. Trying to re-establish...
[INFO] Connected to amqp://airflow_user:**@mq2:5672/airflow_host  ← Switched to mq2
```

The mirroring **is working** - the issue is cluster communication performance. Try the **firewall fix** and **clean restart** first. This should eliminate the timeouts and give you proper instant failover.


======================================================================================






You're hitting a crucial RabbitMQ design constraint: **you cannot use policies to change the queue type** (e.g., to quorum or stream). The queue type must be set **at declaration time**, either by the client or via vhost/default config ([rabbitmq.com][1]).

---

### 🚫 Why Your `set_policy` Commands Failed

* You attempted:

  ```bash
  rabbitmqctl set_policy quorum-policy ".*" '{"queue-type":"quorum", ...}' ...
  ```
* RabbitMQ responded:

  ```
  [{<<"queue-type">>,<<"quorum">>}] are not recognised policy settings
  ```
* This is because `queue-type` isn't supported as a runtime policy parameter—it's immutable after queue creation ([github.com][2]).

---

### ✅ How to Use Quorum Queues Properly

#### **Option 1: Declare Quorum Queues in Client Code**

When your application (e.g., Airflow, Celery) declares a queue, it must include the argument:

```python
arguments={'x-queue-type': 'quorum'}
```

Or the equivalent in your client library. This ensures the queue is created as a quorum queue .

#### **Option 2: Use Vhost or Node-Wide Defaults** *(RabbitMQ ≥ 3.13)*

✔️ **Per‑vhost default:** Assign quorum queue type when creating or updating the vhost:

```bash
rabbitmqctl add_vhost your_vhost --default-queue-type quorum
```

Or, for existing vhost:

```bash
rabbitmqctl update_vhost_metadata your_vhost --default-queue-type quorum
```

This ensures new queues default to quorum type ([stackoverflow.com][3]).

✔️ **Node‑wide default queue type**: (RabbitMQ ≥ 3.13)
Add to `rabbitmq.conf`:

```ini
default_queue_type = quorum
```

This applies cluster-wide for vhosts without explicit defaults ([stackoverflow.com][3]).

---

### 💡 So What Now?

1. **Modify your client/app queue declarations** to include the quorum type:

   ```python
   arguments = {'x-queue-type': 'quorum'}
   ```
2. Optionally **set default queue type**:

   * For existing vhost: `rabbitmqctl update_vhost_metadata airflow_host --default-queue-type quorum`
   * Or in config: `default_queue_type = quorum`

After that, new queues will be quorum type automatically—no need for `set_policy`.

---

### 📒 Migration Strategy (Optional)

If you're migrating from classic queues, refer to RabbitMQ's migration guide ([stackoverflow.com][3], [reddit.com][4], [rabbitmq.com][5]). Typical approach:

* Create new vhost or node-wide default
* Update clients to declare quorum queues
* Migrate data (possibly via federation or rolling restart)

---

### ✅ Summary

| Use Case                | How to Specify Quorum Queue Type                  |
| ----------------------- | ------------------------------------------------- |
| Client-declared queue   | `arguments={'x-queue-type': 'quorum'}`            |
| Default for new vhost   | `rabbitmqctl add/update_vhost_metadata`           |
| Node-wide default       | `rabbitmq.conf`: `default_queue_type = quorum`    |
| Policy-based queue-type | ❌ Not supported – will fail as you've experienced |

---

### ✅ Next Steps for You:

* Remove your `set_policy` attempts involving `"queue-type"`.
* Adjust client code or vhost metadata as shown.
* Declared queues will then be properly created as quorum.

Need help updating your vhost or client config? Just shout!

[1]: https://www.rabbitmq.com/docs/quorum-queues?utm_source=chatgpt.com "Quorum Queues | RabbitMQ"
[2]: https://github.com/rabbitmq/rabbitmq-server/discussions/11988?utm_source=chatgpt.com "rabbitmqctl cannot Force exchange queues to quorum queue #11988"
[3]: https://stackoverflow.com/questions/77155058/how-to-set-up-rabbitmq-default-queue-type-to-quorum-queue-on-bootstrap?utm_source=chatgpt.com "kubernetes - How to set up RabbitMQ default queue type to quorum ..."
[4]: https://www.reddit.com/r/rabbitmq/comments/ouigv4/question_mqtt_plugin_create_quorum_queues_instead/?utm_source=chatgpt.com "[Question] mqtt plugin create quorum queues instead of classic ..."
[5]: https://www.rabbitmq.com/blog/2023/03/02/quorum-queues-migration?utm_source=chatgpt.com "Migrating from Mirrored Classic Queues to Quorum Queues"


========================================================


Since you're using **Airflow with CeleryExecutor and RabbitMQ**, here’s how to properly configure your system to use **quorum queues**:

---

## ✅ 1. Adjust `airflow.cfg` (or ENV vars)

You need to set broker settings under the **$celery$** section (not under $core$). Add these:

```ini
[celery]
broker_url = amqp://<user>:<pass>@mq1:5672/airflow_host
celery_config_options = {"task_default_queue_type": "quorum", "task_default_exchange_type": "direct"}
```

Optionally, you can add:

```ini
extra_celery_config = {"task_queues": [{"name": "celery", "queue_arguments": {"x-queue-type": "quorum"}}]}
```

This ensures Celery declares your default queue with `x-queue-type='quorum'` so RabbitMQ creates it as a quorum queue ([docs.celeryq.dev][1], [sparkcodehub.com][2]).

---

## ✅ 2. RabbitMQ-side vhost default

Set your vhost to use quorum queues as default:

```bash
rabbitmqctl update_vhost_metadata airflow_host --default-queue-type quorum
```

This way, any queue declared in that vhost will default to quorum unless overridden ([stackoverflow.com][3]).

---

## ✅ 3. No more `set_policy` for queue-type

As you found, RabbitMQ doesn’t allow changing queue types via policy — it must be at declaration time ([stackoverflow.com][3]). So remove any existing policies attempting to set `queue-type`.

---

## ✅ 4. Update your Airflow worker code (optional)

If you need to declare custom queues, use:

```python
from kombu import Queue
task_queues = [
    Queue('your_queue', queue_arguments={'x-queue-type': 'quorum'})
]
broker_transport_options = {"confirm_publish": True}
```

Then pass it via `extra_celery_config` or set via env var

---

## ✅ TL;DR

1. **Modify `airflow.cfg`** under `[celery]`, not elsewhere.
2. **Set vhost default queue-type** to quorum.
3. **Restart** all Airflow scheduler + workers so they pick up changes.
4. **Verify** in RabbitMQ management that queues show type **quorum**.

After these steps, Celery will produce and consume from quorum queues automatically. Let me know if you want help generating a full `airflow.cfg` snippet!

[1]: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/rabbitmq.html?utm_source=chatgpt.com "Using RabbitMQ — Celery 5.5.3 documentation"
[2]: https://www.sparkcodehub.com/airflow/integrations/celery-executor?utm_source=chatgpt.com "Mastering Airflow with Celery Executor: A Comprehensive Guide"
[3]: https://stackoverflow.com/questions/77155058/how-to-set-up-rabbitmq-default-queue-type-to-quorum-queue-on-bootstrap?utm_source=chatgpt.com "kubernetes - How to set up RabbitMQ default queue type to quorum ..."


================================================
Here’s how to safely migrate your **existing classic queues** (`card_processing_queue`, `remote_tasks`, `default`) defined via Airflow to **quorum queues**:

---

## 1. 🎯 Understand Queue Type is Fixed at Declaration

RabbitMQ does **not allow** converting an existing classic queue to quorum. Instead, you need to **create new queues** of the desired type and migrate data/messages over ([groups.google.com][1]).

---

## 2. 🔁 Migration Approaches

### ▶️ Option A: **Blue-Green Migration per vhost**

* Create a **new vhost** (e.g., `airflow_v2`) with default queue type set to quorum:

  ```bash
  rabbitmqctl add_vhost airflow_v2 --default-queue-type quorum
  rabbitmqctl set_permissions -p airflow_v2 airflow_user ".*" ".*" ".*"
  ```
* Use **federation** or **shovel plugin** to migrate messages:

  * Federation: seamlessly replicate from old vhost to the new one ([rabbitmq.com][2]).
* Update Airflow to point to the new vhost. Once drained, decommission the old one.

### ▶️ Option B: **In-place Empty-and-Replace**

* Stop Airflow producers/consumers.
* Use a **shovel** to move messages from each classic queue to a new quorum queue with the **same name** in the same vhost.
* Delete the old classic queue.
* Declare quorum queue with `x-queue-type='quorum'` (either client-side or via default queue-type config).
* Restart Airflow to consume from the new queue ([cloudamqp.com][3], [rabbitmq.com][4]).

Example shovel config:

```json
{
  "src-uri": "amqp://user:pass@localhost/airflow_host",
  "src-queue": "card_processing_queue",
  "dest-uri": "amqp://user:pass@localhost/airflow_host",
  "dest-queue": "card_processing_queue",
  "queue-master-locator": "client-local"
}
```

---

## 3. 🚀 Ensure Future Queues Are Quorum

Once old queues are replaced, ensure new ones get the correct type at declaration:

* Declare queues with `x-queue-type='quorum'` argument (from client/Celery).

* Or configure `/etc/rabbitmq/rabbitmq.conf` with:

  ```ini
  default_queue_type = quorum
  ```

  ([youtube.com][5], [rabbitmq.com][4])

* Or set vhost metadata:

  ```bash
  rabbitmqctl update_vhost_metadata airflow_host --default-queue-type quorum
  ```

---

## 4. ✅ Practical Steps for Your Airflow Setup

1. **Choose migration strategy**: Blue-Green vs In-place.
2. **Declare new quorum queues** via default config or queue arguments.
3. **Shovel or federate messages** from old queues.
4. **Stop consumers**, swap queues, restart Airflow workers.
5. **Clean up** old classic queues and policies.

---

## 5. 🧩 In Your Celery Start Command

```bash
airflow celery worker --queues card_processing_queue,remote_tasks,default \
  --queue-arguments '{"x-queue-type":"quorum"}' --concurrency 5
```

*Ensure that Airflow's passing of arguments per queue is supported; otherwise set default queue type globally.*

---

## ✅ Summary Table

| Task                    | How-to                                               |
| ----------------------- | ---------------------------------------------------- |
| Migrate queue data      | Shovel or Federation                                 |
| Create quorum queue     | Client + x-queue-type or default\_queue\_type config |
| Prevent future classics | default\_queue\_type or vhost metadata               |
| Verify queue type       | Check RabbitMQ management UI or `list_queues type`   |

---

Let me know which path you'd prefer (Blue-Green or In-place), and I can provide the exact shovel config or command scripts for your setup!

[1]: https://groups.google.com/g/rabbitmq-users/c/shi9ISJYsRU?utm_source=chatgpt.com "Changing Queue type Classic to Quorum - Google Groups"
[2]: https://www.rabbitmq.com/blog/2023/03/02/quorum-queues-migration?utm_source=chatgpt.com "Migrating from Mirrored Classic Queues to Quorum Queues"
[3]: https://www.cloudamqp.com/blog/moving-from-classic-mirrored-queues-to-quorum-queues.html?utm_source=chatgpt.com "Moving From Classic Mirrored Queues to Quorum Queues"
[4]: https://www.rabbitmq.com/docs/quorum-queues?utm_source=chatgpt.com "Quorum Queues | RabbitMQ"
[5]: https://www.youtube.com/watch?v=ODttmCR4Dgc&utm_source=chatgpt.com "Migrating to Quorum Queues with Minimal Code Changes - YouTube"



================================================================
CLAUDE SOLUTION : 

**Your solution is mostly correct, but needs some adjustments!** Let me refine it based on the official Celery documentation you provided.

## ✅ **Corrected Solution for Airflow + RabbitMQ 4.x Quorum Queues**

### **Step 1: Update airflow.cfg - Correct Format**

```ini
# In airflow.cfg on ALL VMs (VM1, VM2, VM4):

[celery]
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host

# Key settings for Quorum Queues (based on Celery 5.5 docs):
celery_config_options = {
    "task_default_queue_type": "quorum",
    "task_default_exchange_type": "direct",
    "broker_transport_options": {"confirm_publish": True},
    "worker_enable_prefetch_count_reduction": False
}
```

### **Step 2: Issues with Your Original Approach**

❌ **`extra_celery_config`** - This isn't a standard Airflow setting  
❌ **Missing `broker_transport_options`** - Required for quorum queues  
❌ **Missing worker settings** - Needed for quorum queue limitations  

### **Step 3: Alternative Method (Environment Variables)**

If the `celery_config_options` doesn't work, use environment variables:

```bash
# Add to /etc/environment or systemd service files:
export AIRFLOW__CELERY__BROKER_URL="amqp://airflow_user:airflow_pass@mq1:5672/airflow_host"
export AIRFLOW__CELERY__TASK_DEFAULT_QUEUE_TYPE="quorum"  
export AIRFLOW__CELERY__BROKER_TRANSPORT_OPTIONS='{"confirm_publish": true}'
```

### **Step 4: Complete airflow.cfg Configuration**

```ini
[celery]
# Basic broker connection
broker_url = amqp://airflow_user:airflow_pass@mq1:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

# Quorum Queue Configuration (Celery 5.5+ with RabbitMQ 4.x)
celery_config_options = {
    "task_default_queue_type": "quorum",
    "task_default_exchange_type": "direct", 
    "task_default_queue": "default",
    "broker_transport_options": {"confirm_publish": True},
    "worker_enable_prefetch_count_reduction": False,
    "worker_detect_quorum_queues": True
}

# Worker settings for quorum queue compatibility
worker_concurrency = 5
worker_max_tasks_per_child = 1000
```

### **Step 5: Implementation Steps**

```bash
# 1. Stop all services
sudo systemctl stop airflow-scheduler airflow-webserver airflow-worker airflow-dag-processor

# 2. Delete existing classic queues
sudo rabbitmqctl delete_queue card_processing_queue --vhost airflow_host
sudo rabbitmqctl delete_queue default --vhost airflow_host
sudo rabbitmqctl delete_queue remote_tasks --vhost airflow_host

# 3. Update airflow.cfg on ALL VMs (VM1, VM2, VM4)
sudo vi /home/rocky/airflow/airflow.cfg
# [Add the celery_config_options as shown above]

# 4. Restart services
sudo systemctl start airflow-dag-processor    # VM2
sudo systemctl start airflow-scheduler        # VM1  
sudo systemctl start airflow-worker           # VM4
sudo systemctl start airflow-webserver        # VM1
```

### **Step 6: Verify Quorum Queues Are Created**

```bash
# Trigger a DAG to create queues:
airflow dags trigger S12_card_processing_workflow

# Check queue types:
sudo rabbitmqctl list_queues name type --vhost airflow_host

# Should show:
# default                    quorum
# card_processing_queue      quorum
# remote_tasks              quorum
```

## 🚨 **Important Notes from Celery Docs:**

1. **Autoscaling Disabled**: Quorum queues disable autoscaling features
2. **ETA/Countdown Changes**: Uses native delayed delivery instead of blocking
3. **Global QoS Disabled**: Prefetch count becomes static
4. **Confirm Publish**: Required for reliable message delivery

## 🎯 **Why Your Solution Needed Adjustment:**

✅ **Correct**: `task_default_queue_type = "quorum"`  
✅ **Correct**: Basic broker_url format  
❌ **Missing**: `broker_transport_options = {"confirm_publish": True}`  
❌ **Missing**: `worker_enable_prefetch_count_reduction = False`  
❌ **Wrong**: `extra_celery_config` (not a real Airflow setting)  

The key is that **Airflow's `celery_config_options`** passes settings directly to Celery, so you need to use the exact parameter names from the Celery documentation.

Try this corrected configuration and let me know if the queues are created as `quorum` type!
