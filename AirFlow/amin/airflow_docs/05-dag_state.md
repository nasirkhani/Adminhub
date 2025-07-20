# Canceling Tasks and DAG Runs

## Cancel a Retrying Task

### **Method 1: Web UI (Easiest)**
1. Go to **DAGs** → Click your DAG
2. Click on the **Graph** or **Grid** view
3. Find the task in "retry" state (orange color)
4. **Click the task** → **Mark Failed**
5. Or **Click the task** → **Clear** (to reset it)

### **Method 2: CLI**
```bash
# Mark task as failed (stops retries)
airflow tasks state <dag_id> <task_id> <execution_date> --subdir <dag_file>

# Or clear the task
airflow tasks clear <dag_id> --task_regex <task_id>
```

## Cancel an Entire DAG Run

### **Method 1: Web UI (Easiest)**
1. Go to **DAGs** → Click your DAG
2. In **Grid View**, find the running DAG instance
3. Click the **DAG Run** (the row)
4. Click **Mark as Failed**
5. Or click the **"X"** button to stop all running tasks

### **Method 2: Alternative UI Method**
1. **DAGs** → **Browse** → **DAG Runs**
2. Find your running DAG run
3. Click **Actions** → **Mark Failed**

### **Method 3: CLI**
```bash
# Mark entire DAG run as failed
airflow dags state <dag_id> <execution_date>

# Or use the newer command
airflow dags backfill <dag_id> --mark_success --start_date <date> --end_date <date>
```

## Quick Visual Guide

**Task States in UI:**
- 🟢 **Green** = Success
- 🔴 **Red** = Failed  
- 🟠 **Orange** = Retry/Running
- ⚪ **Gray** = Not started
- 🔵 **Blue** = Skipped

**Quick Actions:**
- **Mark Failed** = Stop and mark as failed
- **Clear** = Reset task to run again
- **Mark Success** = Pretend it succeeded

## Pro Tip

**For immediate cancellation:** Use the **Web UI Graph View** - it's the fastest way to see and control individual tasks or entire DAG runs.
