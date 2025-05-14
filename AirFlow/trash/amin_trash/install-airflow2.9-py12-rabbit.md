# Step-by-Step Guide to Install Apache Airflow 2.9.0 on Rocky Linux 9

This comprehensive guide will walk you through installing Apache Airflow 2.9.0 with Python 3.12, PostgreSQL, and RabbitMQ on a Rocky Linux 9 VM running in VirtualBox on Windows 11.

## 1. Setting up Rocky Linux 9 VM in VirtualBox

1. **Download Rocky Linux 9 ISO**:
   - Download the ISO from the [Rocky Linux official website](https://rockylinux.org/download/)

2. **Create a new VM in VirtualBox**:
   - Open VirtualBox on your Windows 11 machine
   - Click "New" to create a new VM
   - Name it "Airflow-Rocky9" and select type "Linux" and version "Red Hat (64-bit)"
   - Allocate at least 4GB RAM (8GB recommended)
   - Create a virtual hard disk (at least 20GB)
   - Select the Rocky Linux 9 ISO as the installation media
   - Complete the installation process with default options

3. **Network Configuration**:
   - Configure network adapter as "NAT" or "Bridged" depending on your needs
   - Consider enabling SSH for remote access

## 2. System Preparation

1. **Update system packages**:
```bash
sudo dnf update -y
sudo dnf upgrade -y
```

2. **Install essential tools and dependencies**:
```bash
sudo dnf install -y epel-release
sudo dnf install -y wget curl git vim nano unzip gcc make openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel ncurses-devel tk-devel xz-devel krb5-devel cyrus-sasl-devel openldap-devel
```

## 3. Installing Python 3.12

1. **Download and install Python 3.12**:
```bash
cd /opt
sudo wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
sudo tar xzf Python-3.12.0.tgz
cd Python-3.12.0
sudo ./configure --enable-optimizations
sudo make altinstall
```

2. **Verify installation**:
```bash
python3.12 --version
pip3.12 --version
```

3. **Make Python 3.12 the default** (optional):
```bash
sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.12 1
sudo update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.12 1
```

## 4. Installing PostgreSQL

1. **Install PostgreSQL repository**:
```bash
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
```

2. **Install PostgreSQL 15** (a compatible version for Airflow 2.9.0):
```bash
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql15-server postgresql15-devel postgresql15-contrib
```

3. **Initialize the database**:
```bash
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
```

4. **Start and enable PostgreSQL service**:
```bash
sudo systemctl start postgresql-15
sudo systemctl enable postgresql-15
```

5. **Configure PostgreSQL for Airflow**:
```bash
# Switch to postgres user
sudo -u postgres psql

# Create a database user and the airflow database
CREATE USER airflow WITH PASSWORD 'airflow_password';
CREATE DATABASE airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
ALTER USER airflow SET search_path = public;

# Enable access from localhost
\q
```

6. **Update PostgreSQL configuration for local access**:
```bash
sudo vim /var/lib/pgsql/15/data/pg_hba.conf
```
   Add or modify these lines:
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
```

7. **Restart PostgreSQL**:
```bash
sudo systemctl restart postgresql-15
```

## 5. Installing RabbitMQ

1. **Install Erlang (required for RabbitMQ)**:
```bash
sudo dnf install -y https://github.com/rabbitmq/erlang-rpm/releases/download/v25.3.2/erlang-25.3.2-1.el9.x86_64.rpm
```

2. **Install RabbitMQ server**:
```bash
sudo dnf install -y https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.11.0/rabbitmq-server-3.11.0-1.el9.noarch.rpm
```

3. **Start and enable RabbitMQ service**:
```bash
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

4. **Create RabbitMQ user for Airflow**:
```bash
sudo rabbitmqctl add_user airflow airflow_password
sudo rabbitmqctl add_vhost airflow_vhost
sudo rabbitmqctl set_user_tags airflow administrator
sudo rabbitmqctl set_permissions -p airflow_vhost airflow ".*" ".*" ".*"
```

5. **Enable RabbitMQ management plugin** (optional, for web UI):
```bash
sudo rabbitmq-plugins enable rabbitmq_management
```
   You can access the management interface at http://localhost:15672

## 6. Creating a Python Virtual Environment

1. **Create a dedicated user for Airflow** (recommended for production):
```bash
sudo useradd -m -d /home/airflow -s /bin/bash airflow
sudo passwd airflow
```

2. **Create and activate virtual environment**:
```bash
# Switch to the airflow user
sudo -iu airflow

# Create directories
mkdir -p ~/airflow
cd ~/airflow

# Create virtual environment
python3.12 -m venv airflow_env
source airflow_env/bin/activate
```

## 7. Installing Apache Airflow 2.9.0

1. **Install pip dependencies**:
```bash
pip install --upgrade pip
pip install wheel setuptools
```

2. **Install Airflow with constraints**:
```bash
# Export variables for proper installation
export AIRFLOW_HOME=~/airflow

# Download constraints file for 2.9.0
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.12.txt"
pip install "apache-airflow==2.9.0" --constraint "${CONSTRAINT_URL}"
```

3. **Install required providers for PostgreSQL, RabbitMQ, and Celery**:
```bash
pip install "apache-airflow-providers-postgres==6.0.0" --constraint "${CONSTRAINT_URL}"
pip install "apache-airflow-providers-rabbitmq==3.3.0" --constraint "${CONSTRAINT_URL}"
pip install "apache-airflow-providers-celery==3.3.1" --constraint "${CONSTRAINT_URL}"
```

## 8. Configuring Airflow

1. **Initialize the Airflow config file**:
```bash
# Make sure you're still in the airflow user and virtual environment
cd ~/airflow
airflow config list  # This will create the airflow.cfg file
```

2. **Edit the Airflow config file**:
```bash
vim ~/airflow/airflow.cfg
```

3. **Update these important configuration settings**:

   a. **Core settings**:
   ```
   [core]
   executor = CeleryExecutor
   load_examples = False
   dags_folder = /home/airflow/airflow/dags
   default_timezone = UTC
   ```

   b. **Database settings**:
   ```
   [database]
   sql_alchemy_conn = postgresql+psycopg2://airflow:airflow_password@localhost/airflow
   ```

   c. **Celery settings**:
   ```
   [celery]
   broker_url = pyamqp://airflow:airflow_password@localhost:5672/airflow_vhost
   result_backend = db+postgresql://airflow:airflow_password@localhost/airflow
   ```

   d. **Webserver settings**:
   ```
   [webserver]
   web_server_host = 0.0.0.0
   web_server_port = 8080
   web_server_ssl_cert = 
   web_server_ssl_key = 
   secret_key = your_generated_secret_key
   ```

   e. **Security settings** (based on the security documentation):
   ```
   [webserver]
   x_frame_enabled = False
   
   [core]
   security = kerberos
   
   [api]
   access_control_allow_headers = origin, content-type, accept
   access_control_allow_methods = POST, GET, OPTIONS, DELETE
   access_control_allow_origins = https://yourdomain.com
   ```

4. **Initialize the database**:
```bash
airflow db init
```

5. **Create an admin user**:
```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin_password
```

## 9. Starting Airflow Services

1. **Create systemd service files for Airflow components**:

   a. **For the webserver**:
   ```bash
   sudo vim /etc/systemd/system/airflow-webserver.service
   ```
   Add:
   ```
   [Unit]
   Description=Airflow webserver daemon
   After=network.target postgresql-15.service rabbitmq-server.service
   Wants=postgresql-15.service rabbitmq-server.service

   [Service]
   Environment=AIRFLOW_HOME=/home/airflow/airflow
   User=airflow
   Group=airflow
   Type=simple
   ExecStart=/home/airflow/airflow/airflow_env/bin/airflow webserver
   Restart=on-failure
   RestartSec=5s
   PrivateTmp=true

   [Install]
   WantedBy=multi-user.target
   ```

   b. **For the scheduler**:
   ```bash
   sudo vim /etc/systemd/system/airflow-scheduler.service
   ```
   Add:
   ```
   [Unit]
   Description=Airflow scheduler daemon
   After=network.target postgresql-15.service rabbitmq-server.service
   Wants=postgresql-15.service rabbitmq-server.service

   [Service]
   Environment=AIRFLOW_HOME=/home/airflow/airflow
   User=airflow
   Group=airflow
   Type=simple
   ExecStart=/home/airflow/airflow/airflow_env/bin/airflow scheduler
   Restart=on-failure
   RestartSec=5s
   PrivateTmp=true

   [Install]
   WantedBy=multi-user.target
   ```

   c. **For the Celery worker**:
   ```bash
   sudo vim /etc/systemd/system/airflow-worker.service
   ```
   Add:
   ```
   [Unit]
   Description=Airflow celery worker daemon
   After=network.target postgresql-15.service rabbitmq-server.service
   Wants=postgresql-15.service rabbitmq-server.service

   [Service]
   Environment=AIRFLOW_HOME=/home/airflow/airflow
   User=airflow
   Group=airflow
   Type=simple
   ExecStart=/home/airflow/airflow/airflow_env/bin/airflow celery worker
   Restart=on-failure
   RestartSec=5s
   PrivateTmp=true

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the services**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver airflow-scheduler airflow-worker
sudo systemctl start airflow-webserver airflow-scheduler airflow-worker
```

3. **Check service status**:
```bash
sudo systemctl status airflow-webserver
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-worker
```

## 10. Verifying the Installation

1. **Check the Airflow web UI**:
   - Open a browser and navigate to `http://your_vm_ip:8080`
   - Log in with the admin user you created

2. **Test a simple DAG**:
   - Create a test DAG file:
   ```bash
   mkdir -p /home/airflow/airflow/dags
   vim /home/airflow/airflow/dags/test_dag.py
   ```
   
   - Add a simple DAG:
   ```python
   from datetime import datetime
   from airflow import DAG
   from airflow.operators.bash import BashOperator

   default_args = {
       'owner': 'airflow',
       'depends_on_past': False,
       'start_date': datetime(2023, 1, 1),
       'email_on_failure': False,
       'email_on_retry': False,
       'retries': 1
   }

   with DAG(
       'test_dag',
       default_args=default_args,
       schedule_interval=None,
       catchup=False
   ) as dag:
       t1 = BashOperator(
           task_id='print_date',
           bash_command='date',
       )
       
       t2 = BashOperator(
           task_id='print_hello',
           bash_command='echo "Hello from Airflow!"',
       )
       
       t1 >> t2
   ```

   - Check if the DAG appears in the web UI

## 11. Security Considerations

Based on the security guidelines, consider implementing these additional security measures:

1. **Enable SSL for the webserver**:
   - Generate self-signed certificates:
   ```bash
   mkdir -p /home/airflow/airflow/certs
   cd /home/airflow/airflow/certs
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout airflow.key -out airflow.crt
   ```
   
   - Update airflow.cfg:
   ```
   [webserver]
   web_server_ssl_cert = /home/airflow/airflow/certs/airflow.crt
   web_server_ssl_key = /home/airflow/airflow/certs/airflow.key
   ```

2. **Configure Kerberos** (if needed):
   - Follow the Kerberos section from the documentation to set up Kerberos authentication

3. **Implement rate limiting**:
   - Edit the webserver_config.py file to implement rate limiting

4. **Set up audit logging**:
   - Enable and configure audit logging as per the documentation

5. **Secure the database connection**:
   - Consider using password encryption or external secret managers

6. **Set up proper permissions**:
   - Review and adjust file permissions for all Airflow files

## 12. Troubleshooting

Common issues and their solutions:

1. **Connection errors to PostgreSQL**:
   - Check the pg_hba.conf and postgresql.conf files
   - Ensure the database user has proper permissions

2. **RabbitMQ connection issues**:
   - Verify RabbitMQ is running: `sudo systemctl status rabbitmq-server`
   - Check vhost and user permissions: `sudo rabbitmqctl list_permissions -p airflow_vhost`

3. **Airflow services not starting**:
   - Check logs: `journalctl -u airflow-webserver.service`
   - Verify permissions and paths in the service files

4. **Webserver not accessible**:
   - Check firewall settings: `sudo firewall-cmd --list-all`
   - Add port if needed: `sudo firewall-cmd --permanent --add-port=8080/tcp && sudo firewall-cmd --reload`

This completes the step-by-step guide for installing Apache Airflow 2.9.0 with Python 3.12, PostgreSQL, and RabbitMQ on Rocky Linux 9 in a VirtualBox VM.