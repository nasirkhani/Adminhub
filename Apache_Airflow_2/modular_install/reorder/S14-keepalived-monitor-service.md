# Full Setup Guide — `keepalived-monitor.service`

This guide creates a **systemd service** that continuously monitors
`keepalived.service` every **0.5 seconds**, and if it’s not active, it runs
`/usr/local/bin/nfs-become-backup.sh`.
It also manages its own logs and uses **logrotate** for cleanup.

---

## 1. Create the monitoring script

**File:** `/usr/local/bin/keepalived-monitor.sh`

```bash
#!/bin/bash
# keepalived-monitor.sh
# Monitors keepalived.service every 0.5 seconds
# If not active, it runs /usr/local/bin/nfs-become-backup.sh
# Logs activity under /var/log/keepalived-monitor/

LOG_DIR="/var/log/keepalived-monitor"
LOG_FILE="$LOG_DIR/keepalived-monitor.log"

mkdir -p "$LOG_DIR"

# Ensure rocky owns the directory and file
chown rocky:rocky "$LOG_DIR"
touch "$LOG_FILE"
chown rocky:rocky "$LOG_FILE"

echo "$(date '+%F %T') [INFO] Keepalived monitor started" >> "$LOG_FILE"

while true; do
    STATUS=$(systemctl is-active keepalived.service 2>&1)
    if [[ "$STATUS" != "active" ]]; then
        echo "$(date '+%F %T') [WARN] Keepalived not active (status: $STATUS), running nfs-become-backup.sh" >> "$LOG_FILE"
        sudo /usr/local/bin/nfs-become-backup.sh >> "$LOG_FILE" 2>&1
    else
        echo "$(date '+%F %T') [OK] Keepalived active" >> "$LOG_FILE"
    fi
    sleep 0.5
done
```

**Set permissions:**

```bash
sudo chmod +x /usr/local/bin/keepalived-monitor.sh
```

---

## 2. Configure sudo permissions

Allow `rocky` to run the NFS script without a password:

**File:** `/etc/sudoers.d/nfs-backup`

```bash
rocky ALL=(ALL) NOPASSWD: /usr/local/bin/nfs-become-backup.sh
```

**Check syntax (important):**

```bash
sudo visudo -c
```

---

## 3. Create the systemd service

**File:** `/etc/systemd/system/keepalived-monitor.service`

```ini
[Unit]
Description=Keepalived Monitor Service
After=network.target keepalived.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=rocky
ExecStartPre=/bin/mkdir -p /var/log/keepalived-monitor
ExecStartPre=/bin/chown rocky:rocky /var/log/keepalived-monitor
ExecStart=/usr/local/bin/keepalived-monitor.sh
Restart=always
RestartSec=5s
StandardOutput=append:/var/log/keepalived-monitor/keepalived-monitor.log
StandardError=append:/var/log/keepalived-monitor/keepalived-monitor.log
SyslogIdentifier=keepalived-monitor

[Install]
WantedBy=multi-user.target
```

---

## 4. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable keepalived-monitor.service
sudo systemctl start keepalived-monitor.service
```

Verify:

```bash
sudo systemctl status keepalived-monitor
```

You should see:

```
Active: active (running)
Main PID: ...
```

---

## 5. Fix log ownership (one-time)

Even though the service now handles directory creation, if you started it before applying those fixes, ensure correct ownership:

```bash
sudo chown rocky:rocky /var/log/keepalived-monitor/keepalived-monitor.log
```

---

## 6. Configure log rotation

**File:** `/etc/logrotate.d/keepalived-monitor`

```bash
/var/log/keepalived-monitor/keepalived-monitor.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 rocky rocky
    postrotate
        systemctl kill -s HUP keepalived-monitor.service >/dev/null 2>&1 || true
    endscript
}
```

Test:

```bash
sudo logrotate -d /etc/logrotate.d/keepalived-monitor
```

---

## 7. Test the behavior

1. Stop keepalived temporarily:

   ```bash
   sudo systemctl stop keepalived
   ```
2. Watch the log:

   ```bash
   tail -f /var/log/keepalived-monitor/keepalived-monitor.log
   ```

   You should see:

   ```
   [WARN] Keepalived not active (status: inactive), running nfs-become-backup.sh
   ```
3. Start keepalived again:

   ```bash
   sudo systemctl start keepalived
   ```

---
