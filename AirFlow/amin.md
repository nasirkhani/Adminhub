Great — now let’s set up **Airflow Scheduler** to run as a **systemd service** on your Rocky Linux 9 system, just like you did for the webserver.

---

## 🧾 Step-by-Step: Create a systemd Service for `airflow scheduler`

### 🔹 1. Verify the `airflow` binary path

We’ll reuse what you found earlier:

```bash
which airflow
```

➡️ Output: `/home/rocky/.local/bin/airflow`

---

### 🔹 2. Create the systemd service file

```bash
sudo vi /etc/systemd/system/airflow-scheduler.service
```

Paste the following:

```ini
[Unit]
Description=Apache Airflow Scheduler
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
ExecStart=/home/rocky/.local/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

---

### 🔹 3. Reload systemd and enable the service

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler
sudo systemctl start airflow-scheduler
```

---

### 🔹 4. Check that it’s working

```bash
sudo systemctl status airflow-scheduler
```

You should see:

* `Active: active (running)`
* Logs in journal with `journalctl -u airflow-scheduler -f`

---

✅ That’s it — the **Airflow scheduler** is now:

* Automatically started on boot
* Managed as a system-wide service
* Running as user `rocky`

Would you like to continue with `airflow celery worker` next?
