## Step 0 — Understanding scenario

You already have:

* `check_nfs_services.sh` — health probe called by **Keepalived**.
  It writes health results to `/var/log/nfs-keepalived.log` every few seconds:

  * `"HEALTH CHECK PASSED: …"`
  * `"HEALTH CHECK FAILED: …"`

Now you want a **secondary watcher service** that:

1. Tails `/var/log/nfs-keepalived.log` once per second.
2. Reads the **latest** log line.
3. If the latest state is `"PASSED"` → do nothing.
4. If it’s `"FAILED"` → trigger:

   1. `sudo /usr/local/bin/nfs-become-backup.sh`
   2. then SSH to the peer node and run `sudo /usr/local/bin/nfs-become-master.sh`
5. It must:

   * Run continuously as a **systemd service** (non-root, user = `rocky`)
   * Log its own actions under `/var/log/nfs-state-watcher/`
   * Use `logrotate` to prevent unbounded growth

---

## 🧩 Step 1 — set directory - permission - files

1. Create the log directory and file **once with root**:

```bash
sudo mkdir -p /var/log/nfs-state-watcher/
sudo touch /var/log/nfs-state-watcher/nfs-state-watcher.log
sudo chown rocky:rocky /var/log/nfs-state-watcher/ /var/log/nfs-state-watcher/nfs-state-watcher.log
```

2. If you want to keep the script creating the directory/file automatically, you must **use `sudo` inside the script**:

```bash
sudo mkdir -p "$LOG_DIR"
sudo touch "$LOG_FILE"
sudo chown rocky:rocky "$LOG_DIR" "$LOG_FILE"
```

This is necessary **because `/var/log` is root-protected**, and normal users cannot create files there.


## 🧩 Step 2 — The watcher script

**File:** `/usr/local/bin/nfs-state-watcher.sh`

```bash
#!/bin/bash
# nfs-state-watcher.sh
# Monitors /var/log/nfs-keepalived.log for latest state
# If "HEALTH CHECK FAILED", triggers NFS failover actions.

LOG_DIR="/var/log/nfs-state-watcher"
LOG_FILE="$LOG_DIR/nfs-state-watcher.log"
NFS_LOG="/var/log/nfs-keepalived.log"
REMOTE_NODE="10.101.20.203"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
chown rocky:rocky "$LOG_DIR" "$LOG_FILE"

log_msg() {
    echo "$(date '+%F %T') - $1" >> "$LOG_FILE"
}

log_msg "[INFO] NFS state watcher started."

LAST_STATE="UNKNOWN"

while true; do
    # Get the latest log line from nfs-keepalived.log
    LATEST_LINE=$(tail -n 1 "$NFS_LOG" 2>/dev/null)

    if [[ -z "$LATEST_LINE" ]]; then
        log_msg "[WARN] No entries found in $NFS_LOG yet."
        sleep 1
        continue
    fi

    if echo "$LATEST_LINE" | grep -q "HEALTH CHECK PASSED"; then
        CURRENT_STATE="PASSED"
    elif echo "$LATEST_LINE" | grep -q "HEALTH CHECK FAILED"; then
        CURRENT_STATE="FAILED"
    else
        CURRENT_STATE="UNKNOWN"
    fi

    # Only act when state changes from PASSED → FAILED
    if [[ "$CURRENT_STATE" == "FAILED" && "$LAST_STATE" != "FAILED" ]]; then
        log_msg "[ERROR] Detected HEALTH CHECK FAILURE. Initiating failover sequence."

        log_msg "[ACTION] Running: sudo /usr/local/bin/nfs-become-backup.sh"
        if sudo /usr/local/bin/nfs-become-backup.sh >> "$LOG_FILE" 2>&1; then
            log_msg "[SUCCESS] nfs-become-backup.sh executed successfully."
        else
            log_msg "[FATAL] nfs-become-backup.sh failed. Skipping remote promotion."
            LAST_STATE="$CURRENT_STATE"
            sleep 1
            continue
        fi

        log_msg "[ACTION] Running remote master promotion on $REMOTE_NODE."
        if ssh -o StrictHostKeyChecking=no rocky@"$REMOTE_NODE" "sudo /usr/local/bin/nfs-become-master.sh" >> "$LOG_FILE" 2>&1; then
            log_msg "[SUCCESS] Remote master promotion executed successfully."
        else
            log_msg "[ERROR] Remote master promotion failed."
        fi
    fi

    LAST_STATE="$CURRENT_STATE"
    sleep 1
done
```

**Make it executable:**

```bash
sudo chmod +x /usr/local/bin/nfs-state-watcher.sh
```

---

## ⚙️ Step 3 — Systemd unit

**File:** `/etc/systemd/system/nfs-state-watcher.service`

```ini
[Unit]
Description=NFS Health Log Watcher
After=network.target keepalived.service

[Service]
Type=simple
User=rocky
ExecStartPre=/bin/mkdir -p /var/log/nfs-state-watcher
ExecStartPre=/bin/chown rocky:rocky /var/log/nfs-state-watcher
ExecStart=/usr/local/bin/nfs-state-watcher.sh
Restart=always
RestartSec=5s
StandardOutput=append:/var/log/nfs-state-watcher/nfs-state-watcher.log
StandardError=append:/var/log/nfs-state-watcher/nfs-state-watcher.log
SyslogIdentifier=nfs-state-watcher

[Install]
WantedBy=multi-user.target
```

---

## 🔐 Step 4 — Configure passwordless sudo

Allow `rocky` to run the needed commands non-interactively:

**File:** `/etc/sudoers.d/nfs-watcher`

```bash
rocky ALL=(ALL) NOPASSWD: /usr/local/bin/nfs-become-backup.sh
rocky ALL=(ALL) NOPASSWD: /usr/local/bin/nfs-become-master.sh
```

Validate:

```bash
sudo visudo -c
```

Make sure SSH key-based login from this node to `10.101.20.203` is already configured for user `rocky`.

---

## 🪶 Step 5 — Log rotation

**File:** `/etc/logrotate.d/nfs-state-watcher`

```bash
/var/log/nfs-state-watcher/nfs-state-watcher.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 rocky rocky
    postrotate
        systemctl kill -s HUP nfs-state-watcher.service >/dev/null 2>&1 || true
    endscript
}
```


## Logrotate explanation

`logrotate` is a Linux utility that automatically rotates, compresses, and manages log files to prevent them from growing indefinitely.
- break it down:

| Directive                                                                                                                                                             | Meaning                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `/var/log/nfs-state-watcher/nfs-state-watcher.log`                                                                                                                    | Path of the log file to rotate.                                                                |
| `daily`                                                                                                                                                               | Rotate the log **once a day**.                                                                 |
| `rotate 7`                                                                                                                                                            | Keep **7 old logs**, delete older ones.                                                        |
| `compress`                                                                                                                                                            | Compress old log files using gzip (`.gz`).                                                     |
| `missingok`                                                                                                                                                           | Don’t fail if the log file is missing.                                                         |
| `notifempty`                                                                                                                                                          | Only rotate if the file is **not empty**.                                                      |
| `create 0640 rocky rocky`                                                                                                                                             | After rotation, create a new log file with permissions **0640**, owner `rocky`, group `rocky`. |
| `postrotate ... endscript`                                                                                                                                            | Commands to run **after log rotation**.                                                        |
| `systemctl kill -s HUP nfs-state-watcher.service` tells the service to **reload the log file** without restarting completely, so it writes to the new empty log file. |                                                                                                |

---

---

## 🔄 Step 6 — Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable nfs-state-watcher.service
sudo systemctl start nfs-state-watcher.service
```

Check:

```bash
sudo systemctl status nfs-state-watcher
sudo tail -f /var/log/nfs-state-watcher/nfs-state-watcher.log
```

---

## 🧪 Step 7 — Test failover sequence

1. Temporarily stop NFS:

   ```bash
   sudo systemctl stop nfs-server
   ```
2. Watch logs:

   ```bash
   tail -f /var/log/nfs-state-watcher/nfs-state-watcher.log
   ```

   You should see:

   ```
   [ERROR] Detected HEALTH CHECK FAILURE. Initiating failover sequence.
   [ACTION] Running: sudo /usr/local/bin/nfs-become-backup.sh
   [SUCCESS] nfs-become-backup.sh executed successfully.
   [ACTION] Running remote master promotion on 10.101.20.203.
   [SUCCESS] Remote master promotion executed successfully.
   ```
3. Restart NFS and verify that it doesn’t retrigger failover when “PASSED”.

---

## ✅ Summary

| Component           | Path                                            | Purpose                                   |
| ------------------- | ----------------------------------------------- | ----------------------------------------- |
| **Watcher script**  | `/usr/local/bin/nfs-state-watcher.sh`           | Monitors health log & triggers failover   |
| **Systemd service** | `/etc/systemd/system/nfs-state-watcher.service` | Runs watcher continuously                 |
| **Logs**            | `/var/log/nfs-state-watcher/`                   | Stores watcher’s own logs                 |
| **Sudo rules**      | `/etc/sudoers.d/nfs-watcher`                    | Allows required commands without password |
| **Logrotate**       | `/etc/logrotate.d/nfs-state-watcher`            | Prevents unbounded log growth             |

---



