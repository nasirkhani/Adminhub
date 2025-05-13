To install Apache Airflow 2.0 in a Rocky Linux 9 server, configured with Python, PostgreSQL, RabbitMQ, and Celery, I'll guide you step by step. This guide will also include setting up your environment in VirtualBox (on Windows 11) and ensuring that all the dependencies are correctly installed.

### Prerequisites

1. **Rocky Linux 9 VM setup**:

   * Install VirtualBox on your Windows 11 machine.
   * Create a new VM with the following settings:

     * RAM: At least 2GB.
     * CPU: 1 core (can increase depending on your load).
     * Disk: 10GB or more (recommended for testing).
   * Mount the Rocky Linux 9 ISO to the VM and complete the installation.

2. **Basic System Setup**:

   * Update the VM's packages to make sure your system is up to date:

     ```bash
     sudo dnf update -y
     sudo dnf upgrade -y
     sudo reboot
     ```

3. **Ensure you have root or sudo privileges** to install dependencies.

---

### Step 1: Install Dependencies

#### 1.1 **Install Python (3.8 or above)**

First, ensure that Python 3.8 (or above) is installed on your system.

```bash
# Install Python 3.8
sudo dnf install -y python3 python3-pip python3-devel

# Check Python and pip versions
python3 --version
pip3 --version
```

You should have Python 3.8.x and pip3 installed.

#### 1.2 **Install PostgreSQL**

Apache Airflow requires a database to store metadata, and PostgreSQL is a recommended choice. You need to install and configure it.

```bash
# Install PostgreSQL
sudo dnf install -y postgresql-server postgresql-contrib

# Initialize PostgreSQL database
sudo postgresql-setup --initdb

# Start and enable PostgreSQL to run on boot
sudo systemctl enable --now postgresql
sudo systemctl start postgresql

# Verify PostgreSQL status
sudo systemctl status postgresql
```

Now, configure PostgreSQL and create a database and user for Airflow:

```bash
# Switch to the postgres user
sudo -i -u postgres

# Access PostgreSQL prompt
psql

# Create a database and user for Airflow
CREATE DATABASE airflow_db;
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;

# Exit the PostgreSQL prompt
\q
```

Next, allow PostgreSQL to accept remote connections (important if you are setting up multi-node systems later):

```bash
# Edit PostgreSQL configuration file
sudo vi /var/lib/pgsql/data/postgresql.conf

# Change listen_addresses to '*'
listen_addresses = '*'

# Allow remote connections (Edit pg_hba.conf)
sudo vi /var/lib/pgsql/data/pg_hba.conf

# Modify the line to allow remote connections:
host all all 0.0.0.0/0 md5

# Restart PostgreSQL to apply the changes
sudo systemctl restart postgresql
```

---

### Step 2: Install RabbitMQ https://www.rabbitmq.com/docs/install-rpm#downloads

RabbitMQ is required for task distribution between Celery workers in Airflow. Install and configure RabbitMQ on the Rocky Linux 9 server:

#### 2.1 **Install RabbitMQ**

```bash
# Install Erlang (RabbitMQ dependency)
sudo dnf install -y erlang

# Install RabbitMQ
sudo dnf install -y rabbitmq-server

# Enable and start RabbitMQ service
sudo systemctl enable --now rabbitmq-server
sudo systemctl start rabbitmq-server

# Check the status of RabbitMQ
sudo systemctl status rabbitmq-server
```

#### 2.2 **Configure RabbitMQ**

Create a user and a virtual host for Airflow and set appropriate permissions:

```bash
# Add user
sudo rabbitmqctl add_user airflow_user airflow_pass

# Set user tags for admin rights
sudo rabbitmqctl set_user_tags airflow_user administrator

# Create a virtual host for airflow
sudo rabbitmqctl add_vhost airflow_host

# Set permissions for airflow_user on airflow_host
sudo rabbitmqctl set_permissions -p airflow_host airflow_user ".*" ".*" ".*"
```

#### 2.3 **Enable RabbitMQ Management Plugin**

Enable the management plugin to access the RabbitMQ Web UI.

```bash
sudo rabbitmq-plugins enable rabbitmq_management

# Restart RabbitMQ for changes to take effect
sudo systemctl restart rabbitmq-server
```

RabbitMQ will now be available at `http://<your_vm_ip>:15672` (default login: `airflow_user`, password: `airflow_pass`).

---

### Step 3: Install Apache Airflow and Dependencies

#### 3.1 **Install Airflow**

Airflow 2.0 and above is installed via pip. You need to install necessary dependencies first.

```bash
# Install Airflow dependencies (Python packages)
pip3 install apache-airflow[celery,postgres,crypto]

# Install Celery (task queue manager) and Flower (web UI for monitoring Celery)
pip3 install celery==4.4.7 flower==0.9.7
```
but it have to be celery = 5.5.0 

#### 3.2 **Configure Airflow Database**

Before starting Airflow, you need to initialize its database:

```bash
# Initialize Airflow's database (PostgreSQL in this case)
airflow db init
```

#### 3.3 **Configure `airflow.cfg`**

Now, configure the `airflow.cfg` file to set up the executor (CeleryExecutor), database connection, broker URL, and result backend.

Open the `airflow.cfg` file:

```bash
vi ~/airflow/airflow.cfg
```

Modify the following sections:

* **executor = CeleryExecutor**
* **sql\_alchemy\_conn = postgresql://airflow\_user\:airflow\_pass\@localhost:5432/airflow\_db**
* **broker\_url = amqp\://airflow\_user\:airflow\_pass\@localhost:5672/airflow\_host**
* **result\_backend = db+postgresql://airflow\_user\:airflow\_pass\@localhost:5432/airflow\_db**

Ensure that the `queue` section is set to use the correct queue, for example:

```bash
queue = airflow.queue
```

---

### Step 4: Set Up Airflow Users

Airflow needs a user to interact with the UI. You can create an admin user like this:

```bash
# Create an admin user for the Airflow UI
airflow users create --role Admin --username airflow_user --email airflow@airflow.com --firstname airflow --lastname user --password airflow_pass
```

---

### Step 5: Start Airflow Services

#### 5.1 **Start Airflow Web Server, Scheduler, and Celery Worker**

Start the necessary Airflow services:

```bash
# Start the Airflow web server (UI)
airflow webserver --port 8080

# Start the Airflow scheduler
airflow scheduler

# Start the Celery worker
airflow celery worker

# Optionally, you can start Flower for Celery monitoring
airflow celery flower
```

Make sure all services are running without errors. You can check the status in the web UI (`http://<your_vm_ip>:8080`), and Flower can be accessed at `http://<your_vm_ip>:5555`.

---

### Step 6: Verify Installation

1. Access the Airflow web UI at `http://<your_vm_ip>:8080` and log in with the user you created.
2. You should be able to create and execute DAGs.
3. Check Flower at `http://<your_vm_ip>:5555` to monitor the Celery workers.
4. If you installed RabbitMQ, access its web UI at `http://<your_vm_ip>:15672` to manage queues.

---

### Step 7: Final Notes

1. If you want Airflow to start automatically when the system reboots, you can set up a systemd service for Airflow components or use `tmux` to run processes in the background.
2. If you want to scale your Airflow setup across multiple nodes, follow the multi-node configuration guidelines mentioned in the original guide.

---

### Conclusion

You have now successfully installed Apache Airflow with Celery Executor, PostgreSQL, and RabbitMQ on a Rocky Linux 9 server. This setup should work in a production environment or for testing purposes. If you plan to deploy Airflow on multiple machines, you can extend this configuration by setting up additional workers on other servers.
