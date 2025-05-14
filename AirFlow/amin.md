Perfect — now let’s set up **Airflow Celery Worker** as a `systemd` service on your Rocky Linux 9 system.

---

## 🧾 Step-by-Step: Create a systemd Service for `airflow celery worker`

---

### 🔹 1. Confirm the path to `airflow`

You already know it's:

```bash
/home/rocky/.local/bin/airflow
```

---

### 🔹 2. Create the service file

```bash
sudo vi /etc/systemd/system/airflow-celery-worker.service
```

Paste the following:

```ini
[Unit]
Description=Apache Airflow Celery Worker
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery worker
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-celery-worker
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

---

### 🔹 3. Reload systemd and enable the service

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable airflow-celery-worker
sudo systemctl start airflow-celery-worker
```

---

### 🔹 4. Check status and logs

```bash
sudo systemctl status airflow-celery-worker
journalctl -u airflow-celery-worker -f
```

Look for lines like:

* `Connected to broker`
* `Ready to accept tasks`
* `airflow worker: Starting up`

---

✅ Done! Your **Airflow Celery Worker** is now:

* Running as a systemd service
* Restartable and boot-enabled
* Integrated cleanly with the webserver and scheduler

---

Shall we continue with the final one: `airflow celery flower` (for monitoring the worker queue)?



Great — let’s now set up the final service: **Airflow Flower**, the Celery monitoring tool, as a `systemd` service on your Rocky Linux 9 server.

---

## 🧾 Step-by-Step: Create a systemd Service for `airflow celery flower`

---

### 🔹 1. Confirm the path to `airflow`

You're using:

```bash
/home/rocky/.local/bin/airflow
```

Perfect — we'll use that path.

---

### 🔹 2. Create the systemd service file

```bash
sudo vi /etc/systemd/system/airflow-flower.service
```

Paste this config:

```ini
[Unit]
Description=Apache Airflow Flower (Celery Monitor)
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-flower
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

> 📝 If you want Flower to be password-protected or to show custom workers, you can extend the `ExecStart` line with options like:

```bash
ExecStart=/home/rocky/.local/bin/airflow celery flower --port=5555 --basic_auth=user:pass
```

---

### 🔹 3. Reload systemd and enable/start Flower

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable airflow-flower
sudo systemctl start airflow-flower
```

---

### 🔹 4. Verify it’s running

```bash
sudo systemctl status airflow-flower
journalctl -u airflow-flower -f
```

And then visit Flower in your browser:

```
http://<your_server_ip>:5555
```

You should see:

* Your Celery workers listed
* Task stats and queue activity

---

✅ Done! You now have:

* `airflow webserver`
* `airflow scheduler`
* `airflow celery worker`
* `airflow celery flower`

**All managed as persistent `systemd` services.**

---

Would you like help with:

* Logging to files instead of journal?
* Restarting all services at once?
* Monitoring/alerts (Prometheus, etc.)?

Or are you ready to move on to DAG deployment/sync?
