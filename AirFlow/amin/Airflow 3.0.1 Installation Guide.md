# Apache Airflow 3.0.1 Installation Guide - Rocky Linux 9

Complete guide for installing Apache Airflow 3.0.1 with Python 3.12, PostgreSQL 15, RabbitMQ, and Celery on Rocky Linux 9.

## Prerequisites

### System Update
```bash
sudo dnf update -y
sudo dnf upgrade -y
sudo reboot
```

---

## Step 1: Install Python 3.12

Rocky Linux 9 comes with Python 3.9, but we need Python 3.12.

### Method 1: Using EPEL and Additional Repositories (Recommended)

```bash
# Install EPEL repository
sudo dnf install -y epel-release

# Add Python 3.12 from additional repositories
sudo dnf install -y python3.12 python3.12-pip python3.12-devel

# Verify installation
python3.12 --version
python3.12 -m pip --version
```

### Method 2: Compile from Source (Alternative)

```bash
# Install build dependencies
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y wget openssl-devel bzip2-devel libffi-devel zlib-devel \
    readline-devel sqlite-devel ncurses-devel tk-devel gdbm-devel \
    db4-devel libpcap-devel xz-devel expat-devel

# Download and compile Python 3.12
cd /tmp
wget https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz
tar xzf Python-3.12.7.tgz
cd Python-3.12.7

./configure --enable-optimizations --with-ensurepip=install
make -j$(nproc)
sudo make altinstall

# Verify installation
python3.12 --version
```

---

## Step 2: Install PostgreSQL 15

### Remove existing PostgreSQL 13 (if installed)
```bash
# Stop PostgreSQL service
sudo systemctl stop postgresql

# Remove PostgreSQL 13
sudo dnf remove -y postgresql-server postgresql

# Remove data directory (BACKUP FIRST if you have data!)
sudo rm -rf /var/lib/pgsql
```

### Install PostgreSQL 15
```bash
# Install PostgreSQL 15 repository
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# Install PostgreSQL 15
sudo dnf install -y postgresql15-server postgresql15-contrib

# Initialize database
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb

# Enable and start PostgreSQL 15
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15

# Verify status
sudo systemctl status postgresql-15
```

### Configure PostgreSQL 15
```bash
# Switch to postgres user
sudo -i -u postgres

# Access PostgreSQL prompt
/usr/pgsql-15/bin/psql

# Create database and user for Airflow
CREATE DATABASE airflow_db;
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER USER airflow_user CREATEDB;

# Exit PostgreSQL
\q
```

Press `Ctrl+D` to exit postgres user.

### Configure PostgreSQL for remote connections
```bash
# Edit PostgreSQL configuration
sudo vi /var/lib/pgsql/15/data/postgresql.conf

# Change listen_addresses to '*'
listen_addresses = '*'

# Edit authentication file
sudo vi /var/lib/pgsql/15/data/pg_hba.conf

# Add line for remote connections:
host all all 0.0.0.0/0 md5

# Restart PostgreSQL
sudo systemctl restart postgresql-15
```

---

## Step 3: Install and Configure RabbitMQ

```bash
# Install Erlang and RabbitMQ
sudo dnf install -y erlang rabbitmq-server

# Enable and start RabbitMQ
sudo systemctl enable --now rabbitmq-server
sudo systemctl start rabbitmq-server

# Configure RabbitMQ
sudo rabbitmqctl add_user airflow_user airflow_pass
sudo rabbitmqctl set_user_tags airflow_user administrator
sudo rabbitmqctl add_vhost airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management
sudo systemctl restart rabbitmq-server
```

### Disable Firewall and SELinux (for development)
```bash
sudo systemctl disable firewalld.service
sudo systemctl stop firewalld.service

# Disable SELinux
sudo vi /etc/selinux/config
# Change: SELINUX=disabled

sudo reboot
```

---

## Step 4: Set Up Python Virtual Environment

### Create virtual environment
```bash
# Create airflow user (optional but recommended)
sudo useradd -m -s /bin/bash airflow
sudo su - airflow  # Or continue as rocky user

# Create virtual environment with Python 3.12
python3.12 -m venv ~/airflow_env

# Activate virtual environment
source ~/airflow_env/bin/activate

# Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel
```

### Set up environment variables
```bash
# Add to ~/.bashrc
echo 'export AIRFLOW_HOME=~/airflow' >> ~/.bashrc
echo 'source ~/airflow_env/bin/activate' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 5: Install Apache Airflow 3.0.1

### Install Airflow with constraints
```bash
# Activate virtual environment
source ~/airflow_env/bin/activate

# Install Airflow 3.0.1 with PostgreSQL, Celery, and other extras
pip install "apache-airflow[celery,postgres,crypto,ssh]==3.0.1" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/refs/tags/constraints-3.0.1/constraints-3.12.txt"

# Install additional packages
pip install "celery==5.5.0" "flower==1.2.0" "paramiko"
```

### Initialize Airflow database
```bash
# Set Airflow home
export AIRFLOW_HOME=~/airflow

# Initialize database
airflow db init
```

---

## Step 6: Configure Airflow

### Edit airflow.cfg
```bash
vi ~/airflow/airflow.cfg
```

**Key configuration changes:**
```ini
[core]
executor = CeleryExecutor
default_timezone = Asia/Tehran
dags_are_paused_at_creation = False

[database]
sql_alchemy_conn = postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

[celery]
broker_url = amqp://airflow_user:airflow_pass@localhost:5672/airflow_host
result_backend = db+postgresql://airflow_user:airflow_pass@localhost:5432/airflow_db

[celery_kubernetes_executor]
kubernetes_queue = kubernetes

[webserver]
web_server_port = 8080
secret_key = your_secret_key_here

[scheduler]
dag_dir_list_interval = 300
```

---

## Step 7: Create Airflow Admin User

```bash
# Create admin user
airflow users create \
    --username airflow_user \
    --firstname Airflow \
    --lastname Admin \
    --role Admin \
    --email admin@example.com \
    --password airflow_pass
```

---

## Step 8: Set Up Systemd Services

### Create systemd service files

#### Airflow Webserver Service
```bash
sudo vi /etc/systemd/system/airflow-webserver.service
```

```ini
[Unit]
Description=Apache Airflow Webserver
After=network.target postgresql-15.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/airflow_env/bin:/usr/bin:/bin
ExecStart=/home/rocky/airflow_env/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-webserver
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

#### Airflow Scheduler Service
```bash
sudo vi /etc/systemd/system/airflow-scheduler.service
```

```ini
[Unit]
Description=Apache Airflow Scheduler
After=network.target postgresql-15.service
Requires=postgresql-15.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/airflow_env/bin:/usr/bin:/bin
ExecStart=/home/rocky/airflow_env/bin/airflow scheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-scheduler
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

#### Airflow Celery Worker Service
```bash
sudo vi /etc/systemd/system/airflow-celery-worker.service
```

```ini
[Unit]
Description=Apache Airflow Celery Worker
After=airflow-scheduler.service rabbitmq-server.service
Requires=airflow-scheduler.service rabbitmq-server.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/airflow_env/bin:/usr/bin:/bin
ExecStart=/home/rocky/airflow_env/bin/airflow celery worker
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-celery-worker
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

#### Airflow Flower Service
```bash
sudo vi /etc/systemd/system/airflow-flower.service
```

```ini
[Unit]
Description=Apache Airflow Flower
After=airflow-celery-worker.service
Requires=airflow-celery-worker.service

[Service]
User=rocky
Group=rocky
Environment=AIRFLOW_HOME=/home/rocky/airflow
Environment=PATH=/home/rocky/airflow_env/bin:/usr/bin:/bin
ExecStart=/home/rocky/airflow_env/bin/airflow celery flower --port=5555
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=30
SyslogIdentifier=airflow-flower
WorkingDirectory=/home/rocky/airflow

[Install]
WantedBy=multi-user.target
```

### Enable and start services
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable airflow-scheduler
sudo systemctl enable airflow-celery-worker
sudo systemctl enable airflow-webserver
sudo systemctl enable airflow-flower

# Start services in order
sudo systemctl start airflow-scheduler
sleep 10
sudo systemctl start airflow-celery-worker
sleep 5
sudo systemctl start airflow-webserver
sleep 5
sudo systemctl start airflow-flower

# Check status
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-celery-worker
sudo systemctl status airflow-webserver
sudo systemctl status airflow-flower
```

---

## Step 9: Verification

### Check service status
```bash
# Check all Airflow services
sudo systemctl status airflow-scheduler airflow-celery-worker airflow-webserver airflow-flower

# Check logs if needed
journalctl -u airflow-scheduler -f
journalctl -u airflow-celery-worker -f
journalctl -u airflow-webserver -f
```

### Access interfaces
- **Airflow Web UI**: `http://your_vm_ip:8080`
- **Flower (Celery Monitor)**: `http://your_vm_ip:5555`
- **RabbitMQ Management**: `http://your_vm_ip:15672`

### Test installation
```bash
# Activate virtual environment
source ~/airflow_env/bin/activate

# Check Airflow version
airflow version

# List DAGs
airflow dags list

# Test database connection
airflow db check
```

---

## Step 10: Additional Configuration

### Create DAGs directory
```bash
mkdir -p ~/airflow/dags
chmod 755 ~/airflow/dags
```

### Set up SSH keys (for your existing DAGs)
```bash
# Generate SSH key if not exists
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# Copy public key to target VMs
ssh-copy-id rocky@192.168.83.132
ssh-copy-id rocky@192.168.83.133
```

### Install additional Python packages for your DAGs
```bash
source ~/airflow_env/bin/activate
pip install paramiko requests pandas
```

---

## Troubleshooting

### Check Python and Airflow versions
```bash
source ~/airflow_env/bin/activate
python --version  # Should show Python 3.12.x
airflow version   # Should show Airflow 3.0.1
```

### Reset database (if needed)
```bash
source ~/airflow_env/bin/activate
airflow db reset
airflow db init
```

### Check PostgreSQL connection
```bash
psql -h localhost -U airflow_user -d airflow_db
```

---

## Benefits of This Setup

✅ **Virtual Environment**: Clean isolation and easy management  
✅ **Python 3.12**: Latest Python version with better performance  
✅ **PostgreSQL 15**: Latest PostgreSQL with improved features  
✅ **Airflow 3.0.1**: Latest Airflow with new features and improvements  
✅ **Systemd Services**: Automatic startup and better service management  
✅ **Proper Dependencies**: All services start in correct order  

This setup provides a production-ready Airflow 3.0.1 installation with all the components you need!
