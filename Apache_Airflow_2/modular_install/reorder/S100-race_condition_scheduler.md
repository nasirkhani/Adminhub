**exact issue** with the `check_scheduler_2_airflow_scheduler` task failure. Here's what's happening:

## **Root Cause Analysis**

### **The Problem: Multi-Scheduler Race Condition**

Looking at the scheduler logs:

**From haproxy-1 scheduler:**
```
[2025-10-25, 11:22:49 +0330] {scheduler_job_runner.py:1562} WARNING - Marking task instance <TaskInstance: ha_service_health_monitor.check_scheduler_2_airflow_scheduler scheduled__2025-10-25T07:40:00+00:00 [queued]> stuck in queued as failed.
[2025-10-25, 11:22:50 +0330] {scheduler_job_runner.py:769} ERROR - Executor reports task instance <TaskInstance: ha_service_health_monitor.check_scheduler_2_airflow_scheduler scheduled__2025-10-25T07:40:00+00:00 [queued]> finished (failed) although the task says it's queued.
```

**But from scheduler-2 scheduler:**
```
[2025-10-25T14:52:04.425+0330] {scheduler_job_runner.py:721} INFO - TaskInstance Finished: dag_id=ha_service_health_monitor, task_id=check_scheduler_2_airflow_scheduler, run_id=scheduled__2025-10-25T07:51:00+00:00, ... state=success
```

### **What's Actually Happening:**

1. **Two different DAG runs are being processed simultaneously:**
   - `scheduled__2025-10-25T07:40:00+00:00` (11:10:00 local time) - **FAILING**
   - `scheduled__2025-10-25T07:51:00+00:00` (11:21:00 local time) - **SUCCESS**

2. **The failing run (07:40:00) got stuck** because:
   - Both schedulers are trying to manage the same task instances
   - There's a race condition in the multi-scheduler setup
   - The task was marked as "stuck in queued" by one scheduler while the other scheduler thought it was still processing

### **Evidence from Worker Logs:**

**celery-1 processed the SUCCESSFUL run:**
```
[2025-10-25 11:22:01,144: INFO/ForkPoolWorker-3] [990094a5-7c13-471b-a70a-3a89ac07a571] Executing command in Celery: ['airflow', 'tasks', 'run', 'ha_service_health_monitor', 'check_scheduler_2_airflow_scheduler', 'scheduled__2025-10-25T07:51:00+00:00', ...]
[2025-10-25 11:22:03,214: INFO/ForkPoolWorker-3] Task ... succeeded in 2.0782893300056458s: None
```

**But the 07:40:00 run never got picked up by any worker** - it was stuck in "queued" state.

