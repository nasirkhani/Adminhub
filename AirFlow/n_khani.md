Thanks for sharing the log — the problem is clear:

> **`/usr/local/bin/airflow: No such file or directory`**

This means the `airflow` command is **not installed at `/usr/local/bin/airflow`**, which is what the `systemd` service is trying to execute.

---

## ✅ Fix: Locate the Correct Airflow Path

### Step 1: Find where `airflow` is installed

Run this in your terminal:

```bash
which airflow
```

**Example output**:

```
/home/rocky/.local/bin/airflow
```

Or if you're using a virtual environment, it might be something like:

```
/home/rocky/venv/bin/airflow
```

---

## ✅ Step 2: Update the systemd service file

Now that you know the correct path (let's say it's `/home/rocky/.local/bin/airflow`), update your unit file:

```bash
sudo vi /etc/systemd/system/airflow-webserver.service
```

Change this line:

```ini
ExecStart=/usr/local/bin/airflow webserver --port 8080
```

To:

```ini
ExecStart=/home/rocky/.local/bin/airflow webserver --port 8080
```

---

## ✅ Step 3: Reload systemd and restart

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart airflow-webserver
```

Check status:

```bash
sudo systemctl status airflow-webserver
```

---

## 🧠 Tip: PATH Environment

If `airflow` lives in `.local/bin` or a venv, `systemd` doesn’t automatically use that `PATH`. To make sure it runs correctly, you can also set the `PATH` explicitly in your service:

```ini
Environment=PATH=/home/rocky/.local/bin:/usr/bin:/bin
```

Add that line under `[Service]` if needed.

---

Let me know if you'd like help:

* Integrating with a virtualenv
* Logging to a file instead of journal
* Setting up `scheduler`, `worker`, `flower` as services too

I'll walk you through it.
