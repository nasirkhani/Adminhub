Your DAG processor is now running successfully (`Active: active (running)`). The previous permission errors were resolved by the bash wrapper approach.

VM2 needs the same configuration as VM4 to connect to PostgreSQL and RabbitMQ on VM1.

## VM2 airflow.cfg Configuration

```ini
[database]
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db

[celery]
broker_url = amqp://airflow_user:airflow_pass@192.168.83.129:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@192.168.83.129:5432/airflow_db
```

The DAG processor needs database access to serialize DAGs into the metadata database.

## SystemD Service Explained Line by Line

Let me explain the `airflow-dag-processor.service` file in detail:

```ini
[Unit]
Description=Airflow Standalone DAG Processor
# ^ Human-readable description shown in 'systemctl status'

After=network.target
# ^ This service should start AFTER network is ready
# Common targets: network.target, multi-user.target, graphical.target
```

### [Unit] Section
- **Description**: What you see when running `systemctl status`
- **After**: Defines startup order - this service waits for network to be ready
- **Before**: (not used here) Would make other services wait for this one
- **Requires**: (not used here) Hard dependency - if required service fails, this fails too
- **Wants**: (not used here) Soft dependency - tries to start other service but continues if it fails

```ini
[Service]
Type=simple
# ^ Service type:
#   - simple: Main process stays in foreground (most common)
#   - forking: Process forks and parent exits (like traditional daemons)
#   - oneshot: Process exits when done (for scripts)
#   - notify: Service tells systemd when it's ready

User=rocky
Group=rocky
# ^ Run the service as this user/group instead of root (security!)
```

### Service Types Explained:
- **simple**: The process doesn't fork/daemonize. SystemD considers it started immediately
- **forking**: For traditional daemons that fork into background
- **oneshot**: Runs once and exits (like a cleanup script)
- **notify**: Service sends "READY=1" to systemd when fully initialized

```ini
Environment="AIRFLOW_HOME=/home/rocky/airflow"
Environment="PATH=/home/rocky/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/rocky/airflow:/home/rocky/.local/lib/python3.9/site-packages"
# ^ Set environment variables for the service
# These are NOT inherited from user's shell environment!
# Format: Environment="KEY=value" or Environment="KEY=value" "KEY2=value2"

WorkingDirectory=/home/rocky/airflow
# ^ cd to this directory before starting the service
```

### Environment Variables:
- Services run in a clean environment (no user's .bashrc)
- Must explicitly set PATH, PYTHONPATH, etc.
- Can also use `EnvironmentFile=/path/to/file` to load from file

```ini
ExecStart=/bin/bash -c 'source /home/rocky/.bashrc && exec /home/rocky/.local/bin/airflow dag-processor'
# ^ The actual command to run
# Using bash -c to:
#   1. Load user's .bashrc (gets user's environment)
#   2. exec replaces bash with airflow process (cleaner)
```

### ExecStart Options:
- **ExecStart**: Main command (required)
- **ExecStartPre**: Run before main command (setup)
- **ExecStartPost**: Run after main command starts
- **ExecStop**: How to stop service (default: SIGTERM)
- **ExecReload**: How to reload config without restart

```ini
Restart=on-failure
# ^ When to restart:
#   - no: Never restart (default)
#   - on-failure: Restart if exit code != 0
#   - on-success: Restart if exit code = 0  
#   - always: Always restart
#   - on-abnormal: Restart on signal/timeout

RestartSec=10s
# ^ Wait 10 seconds before restarting (prevent rapid restart loops)

StandardOutput=journal
StandardError=journal
# ^ Where to send output:
#   - journal: To systemd journal (view with journalctl)
#   - syslog: To syslog
#   - null: Discard
#   - file:/path/to/file: To specific file

SyslogIdentifier=airflow-dag-processor
# ^ Tag for syslog/journal entries (makes filtering easier)
```

### Restart Policies:
- **on-failure**: Most common - restarts on crashes
- **always**: For critical services that must stay running
- **no**: For one-time tasks

```ini
LimitNOFILE=65536
# ^ Maximum number of open files (default ~1024 too low for some services)

LimitNPROC=4096  
# ^ Maximum number of processes/threads
```

### Resource Limits:
- Prevents runaway services from consuming all resources
- Common limits: LimitNOFILE, LimitNPROC, LimitMEMLOCK, LimitCPU

```ini
[Install]
WantedBy=multi-user.target
# ^ Which "target" should include this service
# multi-user.target = normal multi-user system (most common)
# graphical.target = GUI systems
```

### [Install] Section:
- **WantedBy**: Creates a "wants" symlink when you run `systemctl enable`
- **RequiredBy**: Creates a "requires" symlink (stronger dependency)
- **Also**: Enable/disable other units with this one

## Complete SystemD Workflow

```bash
# 1. Create service file
sudo vi /etc/systemd/system/myservice.service

# 2. Reload systemd to recognize new service
sudo systemctl daemon-reload

# 3. Enable service (start at boot)
sudo systemctl enable myservice

# 4. Start service now
sudo systemctl start myservice

# 5. Check status
sudo systemctl status myservice

# 6. View logs
sudo journalctl -u myservice -f

# 7. Stop service
sudo systemctl stop myservice

# 8. Disable service (don't start at boot)
sudo systemctl disable myservice
```

## Common Debugging Commands

```bash
# See why service failed
sudo systemctl status myservice
sudo journalctl -xe -u myservice

# List service dependencies
sudo systemctl list-dependencies myservice

# Analyze boot times
sudo systemd-analyze blame

# Test service configuration
sudo systemd-analyze verify /etc/systemd/system/myservice.service

# See all service properties
sudo systemctl show myservice
```

## Example: Simple Python Script Service

```ini
[Unit]
Description=My Python Script
After=network.target

[Service]
Type=simple
User=myuser
Group=myuser
WorkingDirectory=/home/myuser/project
Environment="PATH=/home/myuser/.local/bin:/usr/bin"
ExecStart=/usr/bin/python3 /home/myuser/project/script.py
Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
```

## Tips for Writing Services

1. **Always run as non-root user** when possible
2. **Set working directory** for relative path scripts
3. **Use absolute paths** in ExecStart
4. **Set environment variables** explicitly
5. **Use appropriate restart policy**
6. **Set resource limits** for production services
7. **Log to journal** for easy debugging

The key concept: SystemD services run in a clean, minimal environment - not your user's shell environment. You must explicitly set everything the service needs!
