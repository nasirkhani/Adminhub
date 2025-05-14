```
[rocky@airflow ~]$ sudo systemctl status airflow-scheduler
● airflow-scheduler.service - Apache Airflow Scheduler
     Loaded: loaded (/etc/systemd/system/airflow-scheduler.service; enabled; preset: disabled)
     Active: active (running) since Wed 2025-05-14 17:34:46 +0330; 4s ago
   Main PID: 5043 (airflow)
      Tasks: 4 (limit: 61404)
     Memory: 209.2M
        CPU: 6.089s
     CGroup: /system.slice/airflow-scheduler.service
             ├─5043 /usr/bin/python3 /home/rocky/.local/bin/airflow scheduler
             ├─5064 "airflow scheduler -- DagFileProcessorManager"
             ├─5120 "airflow scheduler - DagFileProcessor /home/rocky/.local/lib/python3.9/site-packages/airflow/example_dags/example_sla_dag.py"
             └─5121 "airflow scheduler - DagFileProcessor /home/rocky/.local/lib/python3.9/site-packages/airflow/example_dags/example_params_ui_tutoria


[rocky@airflow ~]$ journalctl -u airflow-scheduler -f
May 14 17:34:48 airflow airflow-scheduler[5043]: ___  ___ |  / _  /   _  __/ _  / / /_/ /_ |/ |/ /
May 14 17:34:48 airflow airflow-scheduler[5043]:  _/_/  |_/_/  /_/    /_/    /_/  \____/____/|__/
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.244+0330] {task_context_logger.py:63} INFO - Task context logging is enabled
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.389+0330] {executor_loader.py:235} INFO - Loaded executor: CeleryExecutor
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.419+0330] {scheduler_job_runner.py:796} INFO - Starting the scheduler
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.419+0330] {scheduler_job_runner.py:803} INFO - Processing each file at most -1 times
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.424+0330] {manager.py:170} INFO - Launched DagFileProcessorManager with pid: 5064
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.427+0330] {scheduler_job_runner.py:1595} INFO - Adopting or resetting orphaned tasks for active dag runs
May 14 17:34:48 airflow airflow-scheduler[5064]: [2025-05-14T17:34:48.444+0330] {settings.py:60} INFO - Configured default timezone Asia/Tehran
May 14 17:34:48 airflow airflow-scheduler[5043]: [2025-05-14T17:34:48.521+0330] {scheduler_job_runner.py:1618} INFO - Marked 1 SchedulerJob instances as failed

```
