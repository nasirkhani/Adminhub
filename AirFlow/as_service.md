Perfect — let's turn `airflow webserver --port 8080` into a **systemd service** on your **Rocky Linux 9** server, so it starts automatically on boot.

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
ExecStart=/usr/local/bin/airflow webserver --port 8080
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

✅ Done! Now your Airflow Webserver will:

* Start automatically on boot.
* Be restartable with `systemctl restart airflow-webserver`.
* Log to journalctl.

---

