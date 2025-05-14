Here is your guide in **Markdown (.md)** format:

````markdown
# Apache Airflow 2.8.1 Installation on Rocky Linux 9.4 with Python 3.11 + PostgreSQL

This guide walks you through installing **Apache Airflow 2.8.1** on **Rocky Linux 9.4 Server** inside a **VirtualBox VM** with:

- Python 3.11
- PostgreSQL (v15 recommended)
- LocalExecutor
- Virtualenv

---

## ⚙️ Step 0: VM Prep (VirtualBox)

- Create a new VM:
  - OS: Rocky Linux 9.4 (get from https://rockylinux.org)
  - 2 CPUs, 4+ GB RAM, 20+ GB disk
  - Bridged Adapter or NAT with port forwarding

---

## 📦 Step 1: Update System and Install EPEL

```bash
sudo dnf update -y
sudo dnf install -y epel-release
````

---

## 🐍 Step 2: Install Python 3.11 & Pip

```bash
sudo dnf install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make
sudo dnf install -y python3.11 python3.11-devel python3.11-pip

sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1

python3 --version
```

---

## 🧱 Step 3: Install Required System Packages

```bash
sudo dnf groupinstall -y "Development Tools"

sudo dnf install -y \
  libpq-devel mysql-devel openldap-devel krb5-devel \
  cyrus-sasl-devel libxml2-devel libxslt-devel \
  unixODBC-devel sqlite-devel \
  freetds-devel nc net-tools \
  libffi-devel cairo-devel \
  curl which git tmux
```

---

## 🐘 Step 4: Install and Configure PostgreSQL

```bash
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/15/redhat/rhel-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql15 postgresql15-server postgresql15-devel

sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
sudo systemctl enable --now postgresql-15
```

Create database and user:

```bash
sudo -i -u postgres
createuser airflow_user --createdb --pwprompt
createdb airflow_db --owner=airflow_user
psql
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
\q
exit
```

---

## 🐍 Step 5: Set Up Virtualenv

```bash
python3 -m venv ~/airflow-venv
source ~/airflow-venv/bin/activate
pip install --upgrade pip setuptools wheel
```

---

## 📥 Step 6: Download or Set Constraints File

**Option A**: Download manually (from Windows or browser):

* [https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.11.txt](https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.11.txt)

**Option B**: Download directly (if GitHub works):

```bash
export AIRFLOW_VERSION=2.8.1
export PYTHON_VERSION=3.11
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
```

---

## 📦 Step 7: Install Apache Airflow

With local file:

```bash
pip install "apache-airflow[postgres]==2.8.1" --constraint ./constraints-3.11.txt
```

Or with online constraints:

```bash
pip install "apache-airflow[postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
```

---

## ⚙️ Step 8: Set Environment and Airflow Config

```bash
export AIRFLOW_HOME=~/airflow
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow_user:airflow@localhost/airflow_db"
```

Add to `.bashrc`:

```bash
echo 'export AIRFLOW_HOME=~/airflow' >> ~/.bashrc
echo 'export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow_user:airflow@localhost/airflow_db"' >> ~/.bashrc
source ~/.bashrc
```

Switch to LocalExecutor:

```bash
sed -i 's/executor = SequentialExecutor/executor = LocalExecutor/' $AIRFLOW_HOME/airflow.cfg
```

---

## 🛠️ Step 9: Initialize DB and Create Admin

```bash
airflow db migrate

airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password airflow
```

---

## 🚀 Step 10: Start Services

```bash
tmux new -s airflow-scheduler
airflow scheduler
# Ctrl+b then d to detach

tmux new -s airflow-webserver
airflow webserver --host 0.0.0.0 --port 8080
```

---

## 🌐 Step 11: Access from Host Browser

### Option A: Bridged Network

Find IP:

```bash
ip a
```

Open `http://<vm_ip>:8080` in your browser.

### Option B: NAT with Port Forwarding

Set port forwarding:
**Host Port 8080 → Guest Port 8080**
Open `http://localhost:8080`

---

## ✅ Final Summary

| Component       | Status                                           |
| --------------- | ------------------------------------------------ |
| OS              | Rocky Linux 9.4 ✅                                |
| Python          | 3.11 ✅                                           |
| PostgreSQL      | 15 ✅                                             |
| Airflow Version | 2.8.1 ✅                                          |
| Executor        | LocalExecutor ✅                                  |
| Web UI          | [http://localhost:8080](http://localhost:8080) ✅ |

---


