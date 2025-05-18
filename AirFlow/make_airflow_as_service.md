turn `airflow webserver --port 8080` into a **systemd service** on your **Rocky Linux 9** server, so it starts automatically on boot.

---

## 🎯 Goal

* Create a `systemd` unit file for `airflow webserver`.
* Ensure it runs as your user: `rocky`.
* Autostart on reboot.
* Log output to the journal.

---

## 🧾 Step-by-Step: Create a systemd Service for `airflow webserver`

### 🔹 1. Create a systemd unit file

Create the file:

```bash
sudo vi /etc/systemd/system/airflow-webserver.service
```

Paste the following content:

```ini
[Unit]
Description=Apache Airflow Webserver
After=network.target

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
#ExecStart=/usr/local/bin/airflow webserver --port 8080
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

> 🔧 Notes:
>
> * Adjust `ExecStart` path to match your Python environment (`which airflow` to verify).
> * If using a virtual environment, you’ll need to activate it in a wrapper script (ask if you need help with that).

```bash
which airflow
```

**Example output**:

```
/home/rocky/.local/bin/airflow
```

---

### 🔹 2. Reload systemd daemon

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
```

---

### 🔹 3. Enable and start the service

```bash
sudo systemctl enable airflow-webserver
sudo systemctl start airflow-webserver
```

---

### 🔹 4. Check status and logs

```bash
sudo systemctl status airflow-webserver
journalctl -u airflow-webserver -f
```

---


If `airflow` lives in `.local/bin` or a venv, `systemd` doesn’t automatically use that `PATH`. To make sure it runs correctly, you can also set the `PATH` explicitly in your service:

```ini
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
```

Add that line under `[Service]` if needed.





---

## 🧾 Step-by-Step: Create a systemd Service for `airflow scheduler`

### 🔹 1. Verify the `airflow` binary path


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


Here's exactly what to add to each `.service` file under the `[Unit]` section to enforce the recommended startup order:

---

### ✅ 1. `airflow-scheduler.service`

Leave as is — it's the **first** to start, so no dependencies.

```ini
[Unit]
Description=Apache Airflow Scheduler
After=network.target
```

---

### ✅ 2. `airflow-celery-worker.service`

Start **after scheduler**.

```ini
[Unit]
Description=Apache Airflow Celery Worker
After=airflow-scheduler.service
Requires=airflow-scheduler.service
```

---

### ✅ 3. `airflow-webserver.service`

Start **after scheduler and worker**.

```ini
[Unit]
Description=Apache Airflow Webserver
After=airflow-scheduler.service airflow-celery-worker.service
Requires=airflow-scheduler.service airflow-celery-worker.service
```

---

### ✅ 4. `airflow-flower.service`

Start **after the worker**.

```ini
[Unit]
Description=Apache Airflow Flower
After=airflow-celery-worker.service
Requires=airflow-celery-worker.service
```

---

### 🔄 After editing all files:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
```

Now `systemd` will start services in a clean, ordered, dependency-aware sequence on boot.





## 🧠 Tip: PATH Environment

If `airflow` lives in `.local/bin` or a venv, `systemd` doesn’t automatically use that `PATH`. To make sure it runs correctly, you can also set the `PATH` explicitly in your service:

```ini
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
```

Add that line under `[Service]` if needed.
