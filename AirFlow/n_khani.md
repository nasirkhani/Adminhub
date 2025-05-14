● airflow-webserver.service - Apache Airflow Webserver
     Loaded: loaded (/etc/systemd/system/airflow-webserver.service; enabled; preset: disabled)
     Active: active (running) since Wed 2025-05-14 17:11:57 +0330; 1min 19s ago
   Main PID: 4270 (airflow)
      Tasks: 6 (limit: 61404)
     Memory: 243.2M
        CPU: 9.042s
     CGroup: /system.slice/airflow-webserver.service
             ├─4270 /usr/bin/python3 /home/rocky/.local/bin/airflow webserver --port 8080
             ├─4283 "gunicorn: master [airflow-webserver]"
             ├─4292 "[ready] gunicorn: worker [airflow-webserver]"
             ├─4293 "[ready] gunicorn: worker [airflow-webserver]"
             ├─4294 "[ready] gunicorn: worker [airflow-webserver]"
             └─4295 "[ready] gunicorn: worker [airflow-webserver]"

May 14 17:12:03 airflow airflow-webserver[4283]: /home/rocky/.local/lib/python3.9/site-packages/airflow/api_connexion/schemas/task_schema.py:52 Changed>
May 14 17:12:03 airflow airflow-webserver[4283]: /home/rocky/.local/lib/python3.9/site-packages/airflow/api_connexion/schemas/task_schema.py:55 Changed>
May 14 17:12:03 airflow airflow-webserver[4283]: /home/rocky/.local/lib/python3.9/site-packages/airflow/api_connexion/schemas/task_schema.py:59 Changed>
May 14 17:12:03 airflow airflow-webserver[4283]: [2025-05-14 17:12:03 +0330] [4283] [INFO] Starting gunicorn 23.0.0
May 14 17:12:04 airflow airflow-webserver[4283]: [2025-05-14 17:12:04 +0330] [4283] [INFO] Listening at: http://0.0.0.0:8080 (4283)
May 14 17:12:04 airflow airflow-webserver[4283]: [2025-05-14 17:12:04 +0330] [4283] [INFO] Using worker: sync
May 14 17:12:04 airflow airflow-webserver[4292]: [2025-05-14 17:12:04 +0330] [4292] [INFO] Booting worker with pid: 4292
May 14 17:12:04 airflow airflow-webserver[4293]: [2025-05-14 17:12:04 +0330] [4293] [INFO] Booting worker with pid: 4293
May 14 17:12:04 airflow airflow-webserver[4294]: [2025-05-14 17:12:04 +0330] [4294] [INFO] Booting worker with pid: 4294
May 14 17:12:04 airflow airflow-webserver[4295]: [2025-05-14 17:12:04 +0330] [4295] [INFO] Booting worker with pid: 4295
