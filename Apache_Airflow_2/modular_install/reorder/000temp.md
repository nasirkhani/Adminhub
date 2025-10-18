## ⚙️ Overview — Where “Concurrency” Appears in Airflow

Airflow has **three main levels** of concurrency control:

| Level                             | Config / Parameter                                                         | Scope                      | Controls                                                                             |
| --------------------------------- | -------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------ |
| 🧠 **Global**                     | `parallelism` (in `airflow.cfg`)                                           | Whole Airflow system       | Max *total* number of task instances (TIs) that can run across all DAGs, all workers |
| 📊 **DAG-level**                  | `max_active_tasks` / `max_active_runs` / `concurrency` (in DAG definition) | Each DAG                   | Limits how many TIs from that DAG can run simultaneously                             |
| ⚙️ **Worker-level**               | `worker_concurrency` (in `[celery]` section of `airflow.cfg`)              | Each Celery worker process | Max number of tasks that each Celery worker can execute concurrently                 |
| 💻 **Executor slots (scheduler)** | `max_tis_per_query`, `scheduler_heartbeat_sec`                             | Scheduler → DB load tuning | Limits how many TIs are fetched from DB per cycle                                    |
| 🧩 **Task-level**                 | `pool` or `task_concurrency` (in operator)                                 | Individual tasks           | Limits how many *instances* of this task ID can run in parallel                      |

---

## 🧱 Let’s explain each clearly with examples

### 1. **Global: `parallelism` (in `airflow.cfg`)**

```ini
[core]
parallelism = 32
```

* This limits the total number of **task instances** that Airflow can run *system-wide*, across all DAGs and workers.
* If set too low, you can have many tasks “queued” forever even though workers are idle.
* Think of this as the **global concurrency cap**.

✅ For your cluster (2 workers × 4 concurrency each = 8 real parallel slots),
a safe value is 32–64.

---

### 2. **Worker-level: `worker_concurrency` (in `[celery]`)**

```ini
[celery]
worker_concurrency = 4
```

* This controls how many *Python processes per Celery worker* can run tasks in parallel.
* Each worker VM runs up to that many tasks concurrently.

🧠 Example:

* You have two workers (`celery-1`, `celery-2`)
* Each has `worker_concurrency = 4`
  → You can theoretically run **8 parallel tasks**.

If you run 9+ tasks, the extra ones stay in **queued** state until a slot opens.

⚠️ If `parallelism` (global) is lower than `worker_concurrency × workers`, you’ll still get a bottleneck — tasks queue up even if worker slots are free.

---

### 3. **DAG-level: `concurrency` and `max_active_runs`**

Inside a DAG file:

```python
dag = DAG(
    'my_dag',
    concurrency=4,
    max_active_runs=2,
)
```

* `concurrency`: max number of *tasks from this DAG* that can run at once, across all DAG runs.
* `max_active_runs`: max number of DAG runs that can execute concurrently (e.g., today + yesterday).

🧠 Example:
If your DAG runs every 5 minutes but takes 10 minutes to finish:

* `max_active_runs=1` → new run waits until previous finishes
* `max_active_runs=2` → you can have 2 overlapping runs
* `concurrency=3` → within all runs, only 3 tasks total can execute at once

---

### 4. **Task-level: `task_concurrency`**

You can set per-task limits to avoid overlapping instances:

```python
BashOperator(
    task_id='check_postgresql_3_patroni',
    task_concurrency=1,
    ...
)
```

→ prevents more than 1 instance of that specific task from running simultaneously, even across DAG runs.

---

### 5. **Pools**

Pools are logical groups of slots you can assign to tasks:

```bash
airflow pools set postgres_check_pool 2 "Pool for PostgreSQL checks"
```

and in DAG:

```python
BashOperator(pool='postgres_check_pool')
```

→ ensures only 2 of these tasks run at once, even if there are many worker slots free.

---

## 💣 How Misconfigured Concurrency Can Cause “Queued → Failed” Problems

Here’s the subtle but important part related to your error:

### ❌ Scenario

You have:

```ini
[core]
parallelism = 16

[celery]
worker_concurrency = 4
```

and two workers (→ 8 task slots total).

Now your scheduler tries to queue 20 tasks because DAG concurrency allows it.
However:

* 16 tasks get submitted fine.
* 4 tasks remain in **queued** because the global cap (16) is hit.
* Scheduler marks them as “queued” in DB.
* Celery (or another scheduler) eventually tries to pick one up again, but it’s now stale or expired.
* Airflow detects a mismatch:
  “Task says queued, executor says finished (failed). Was it killed externally?”

💥 That’s **exactly your log line.**

---

## ✅ How to Fix / Tune for Your Cluster

For your architecture (2 schedulers, 2 workers, 4 slots each):

| Setting                       | Suggested Value                            | Why                                                                |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------------------------ |
| `[core] parallelism`          | `64`                                       | Gives headroom for HA schedulers, avoids system-wide throttle      |
| `[celery] worker_concurrency` | `4`–`6`                                    | 4 is fine per 2 GB RAM; can increase slightly if lightweight tasks |
| `concurrency` in DAGs         | `4`–`8`                                    | Safe default per DAG to prevent oversubscription                   |
| `max_active_runs`             | `1` or `2`                                 | For monitoring DAGs like `ha_service_health_monitor`, use 1        |
| `task_concurrency`            | Only if specific task should never overlap | e.g., a health check that must run once at a time                  |

---

### Example: good configuration for your monitoring DAG

```python
dag = DAG(
    'ha_service_health_monitor',
    schedule_interval='*/5 * * * *',
    max_active_runs=1,
    concurrency=4,
    catchup=False,
)
BashOperator(
    task_id='check_postgresql_3_patroni',
    bash_command='check_pg_node.sh 3',
    task_concurrency=1,
    pool='postgres_check_pool',
    retries=2,
    retry_delay=timedelta(minutes=1),
)
```

---

## 🔎 TL;DR — Quick Reference

| Setting              | Scope  | Typical Range  | Applies To         | Notes                  |
| -------------------- | ------ | -------------- | ------------------ | ---------------------- |
| `parallelism`        | Global | 32–128         | Whole Airflow      | Total running tasks    |
| `worker_concurrency` | Worker | 2–8 per worker | Each Celery worker | OS resources dependent |
| `concurrency`        | DAG    | 4–8            | Tasks within DAG   | Prevent DAG flood      |
| `max_active_runs`    | DAG    | 1–2            | DAG runs           | Avoid overlap          |
| `task_concurrency`   | Task   | 1              | Individual task    | For singleton tasks    |

---

### ✅ Practical tip

If you often see `task stuck in queued` or `task says queued but finished`, **raise `parallelism` first**, then check Celery logs for worker slot saturation:

```bash
airflow celery inspect active
airflow celery inspect reserved
airflow celery inspect stats
```

---

deep   



## Airflow Concurrency Hierarchy

Here's the hierarchy from **global** to **specific**:

### 1. **`[core] parallelism`** (Global - in airflow.cfg)
```ini
[core]
parallelism = 32
```
- **What it controls**: Maximum number of **total task instances** that can run across ALL DAGs in your entire Airflow deployment
- **Scope**: Global across all DAGs, all workers
- **Your setting**: 32 total tasks max across entire system

### 2. **`[core] max_active_runs_per_dag`** (Per DAG)
```ini
[core]
max_active_runs_per_dag = 16
```
- **What it controls**: Maximum number of **concurrent DAG runs** for a single DAG
- **Scope**: Per DAG
- **Your setting**: Each DAG can have max 16 simultaneous runs

### 3. **`dag_concurrency`** (Per DAG Run - usually in DAG definition)
```python
@dag(
    dag_id='my_dag',
    max_active_tasks=8,  # This is dag_concurrency
    concurrency=16,      # Alternative parameter
)
```
- **What it controls**: Maximum number of **tasks** that can run simultaneously **within a single DAG run**
- **Scope**: Per DAG run

### 4. **`worker_concurrency`** (Per Worker - in airflow.cfg)
```ini
[celery]
worker_concurrency = 4
```
- **What it controls**: Maximum number of **tasks** that a **single worker process** can execute simultaneously
- **Scope**: Per worker process

### 5. **`--concurrency`** (Per Worker - in service file)
```bash
airflow celery worker --concurrency 6
```
- **What it controls**: Same as `worker_concurrency` but **overrides** the config file setting
- **Scope**: Per worker process

## How They Interact - Practical Example

With your current settings:
- **Global**: `parallelism = 32` (max 32 tasks total)
- **Per DAG run**: `max_active_runs_per_dag = 16` (max 16 DAG runs per DAG)
- **Per worker**: `worker_concurrency = 4` (each worker runs 4 tasks)
- **2 workers**: Total capacity = 4 × 2 = **8 concurrent tasks**

## Visual Flow:

```
[Global Limit: 32 tasks]
    ↓
[Per DAG: max 16 runs of DAG-A]
    ↓
[Per DAG run: max X tasks in this run]
    ↓
[Per Worker: max 4 tasks on worker-1]
```

## Your Specific Questions Answered:

### **"parallelism in the DAG"**
This refers to **`max_active_tasks`** or **`concurrency`** in DAG definition:
```python
@dag(
    max_active_tasks=8,  # Max tasks running concurrently in one DAG run
    concurrency=16,      # Alternative way (same concept)
)
```

### **"parallelism in the service file"**
This is **`--concurrency`** which controls **per-worker task capacity**

### **"parallelism In airflow.cfg"**
- **`[core] parallelism`**: Global task limit
- **`[celery] worker_concurrency`**: Per-worker task limit

### **"parallelism in dag or task instance?"**
- **DAG level**: Controls how many tasks run concurrently within the DAG
- **Task instance**: There's no per-task parallelism setting. Each task instance runs as a separate process.

## Your Current Bottleneck Analysis

Your health monitor DAG has:
- ~15+ tasks per run
- Runs every minute
- With your current limits:
  - **Global**: 32 tasks max ✅ (plenty)
  - **Workers**: 8 tasks total capacity (4 × 2 workers) ⚠️
  - **Result**: Tasks queue up because workers can only handle 8 at once

## Recommended Fix:

### **Option 1: Increase Worker Concurrency** (Quickest)
```ini
# In airflow.cfg
[celery]
worker_concurrency = 8

# Or in service file (overrides config)
ExecStart=... --concurrency 8
```
**Result**: 8 × 2 workers = 16 concurrent tasks

### **Option 2: Add DAG-Level Limits**
```python
@dag(
    dag_id='ha_service_health_monitor',
    max_active_tasks=6,  # Don't overwhelm the system
    concurrency=10,
)
```

### **Option 3: Balance All Settings**
```ini
# airflow.cfg
[core]
parallelism = 64                    # Increase global limit
max_active_runs_per_dag = 8         # Reduce per-DAG runs

[celery]
worker_concurrency = 6              # Per-worker capacity
```

## Key Takeaway:

The **immediate bottleneck** is your **worker concurrency (8 total)** vs your **DAG tasks (~15+)**. Increasing worker concurrency to 6-8 per worker will likely resolve your queued task issue.

Start with:
```bash
# Update service file on both workers
ExecStart=... --concurrency 6

# Restart workers
sudo systemctl restart airflow-worker
```

This should give you 12 total concurrent task capacity (6 × 2 workers), which should handle your health monitor DAG comfortably.
