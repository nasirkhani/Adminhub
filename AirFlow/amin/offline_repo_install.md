# system packages (RPMs) and Python packages (wheels). 

## System Packages (RPMs) for Rocky Linux 9

### For All VMs (Common Requirements):
```bash
# Development Tools
gcc
gcc-c++
make
python3
python3-devel
python3-pip
python3-setuptools
python3-wheel

# Libraries
openssl-devel
libffi-devel
libevent-devel
libxml2-devel
libxslt-devel
zlib-devel
bzip2-devel
readline-devel
sqlite-devel

# System Utilities
git
wget
curl
tar
gzip
unzip
vim
nano
tmux
screen
htop

# NFS (for VM1, VM2, VM4)
nfs-utils
rpcbind
```

### For VM1 (Additional):
```bash
# PostgreSQL
postgresql-server
postgresql
postgresql-contrib
postgresql-devel

# RabbitMQ and Dependencies
erlang
erlang-asn1
erlang-crypto
erlang-eldap
erlang-inets
erlang-mnesia
erlang-os_mon
erlang-public_key
erlang-sasl
erlang-ssl
erlang-syntax_tools
erlang-tools
erlang-xmerl
rabbitmq-server
socat

# Additional for compilation
libpq-devel
cyrus-sasl-devel
```

### For VM2 (Additional):
```bash
# NFS Server specific
nfs-utils
rpc.nfsd
exportfs
```

## Python Packages List

### Create requirements file with all dependencies:
```bash
# Create a requirements.txt with exact versions from constraint file
cat > airflow_offline_requirements.txt << 'EOF'
# Airflow 2.9.0 with extras
apache-airflow[celery,postgres,crypto,ssh]==2.9.0

# From constraints-2.9.0/constraints-3.9.txt (key packages)
celery==5.3.6
flower==2.0.1
kombu==5.3.5
redis==5.0.1
amqp==5.2.0
billiard==4.2.0
vine==5.1.0

# Database
psycopg2-binary==2.9.9
SQLAlchemy==1.4.51
alembic==1.13.1

# SSH and Crypto
paramiko==3.4.0
cryptography==41.0.7
bcrypt==4.1.2
pysftp==0.2.9
sshtunnel==0.4.0

# Airflow Providers
apache-airflow-providers-celery==3.6.1
apache-airflow-providers-common-sql==1.11.1
apache-airflow-providers-ftp==3.8.0
apache-airflow-providers-http==4.9.0
apache-airflow-providers-postgres==5.10.2
apache-airflow-providers-ssh==3.10.1

# Web Framework
Flask==2.2.5
Flask-AppBuilder==4.4.1
Flask-Babel==2.0.0
Flask-Caching==2.1.0
Flask-JWT-Extended==4.6.0
Flask-Limiter==3.5.1
Flask-Login==0.6.3
Flask-Session==0.5.0
Flask-SQLAlchemy==2.5.1
Flask-WTF==1.2.1
Werkzeug==2.2.3
WTForms==3.1.2

# API and Serialization
connexion==2.14.2
marshmallow==3.20.2
marshmallow-sqlalchemy==0.29.0
apispec==6.4.0

# Task Queue and Scheduling
croniter==2.0.2
pendulum==3.0.0
python-dateutil==2.8.2
pytz==2024.1

# Utilities
click==8.1.7
colorlog==4.8.0
configupdater==3.2
dill==0.3.8
graphviz==0.20.1
gunicorn==21.2.0
httpcore==1.0.2
httpx==0.25.2
itsdangerous==2.1.2
Jinja2==3.1.3
jsonschema==4.21.1
lazy-object-proxy==1.10.0
lockfile==0.12.2
Mako==1.3.2
Markdown==3.5.2
MarkupSafe==2.1.5
packaging==23.2
pathspec==0.12.1
pluggy==1.4.0
pygments==2.17.2
python-daemon==3.0.1
python-nvd3==0.15.0
python-slugify==8.0.4
PyYAML==6.0.1
requests==2.31.0
rich==13.7.0
setproctitle==1.3.3
sqlparse==0.4.4
tabulate==0.9.0
tenacity==8.2.3
termcolor==2.4.0
typing_extensions==4.9.0
unicodecsv==0.14.1
urllib3==2.2.0

# Monitoring
statsd==4.0.1
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0

# Documentation
docutils==0.20.1
sphinx==7.2.6

# Authentication
argon2-cffi==23.1.0
pyjwt==2.8.0

# Additional dependencies
asgiref==3.7.2
attrs==23.2.0
blinker==1.7.0
cachelib==0.9.0
cattrs==23.2.3
certifi==2024.2.2
cffi==1.16.0
charset-normalizer==3.3.2
deprecated==1.2.14
dnspython==2.5.0
email-validator==2.1.0.post1
googleapis-common-protos==1.62.0
grpcio==1.60.1
h11==0.14.0
idna==3.6
importlib-metadata==7.0.1
inflection==0.5.1
limits==3.9.0
linkify-it-py==2.0.3
markdown-it-py==3.0.0
mdit-py-plugins==0.4.0
mdurl==0.1.2
opentelemetry-exporter-otlp==1.22.0
opentelemetry-exporter-otlp-proto-common==1.22.0
opentelemetry-exporter-otlp-proto-grpc==1.22.0
opentelemetry-exporter-otlp-proto-http==1.22.0
opentelemetry-proto==1.22.0
ordered-set==4.1.0
prison==0.2.1
protobuf==4.25.2
psutil==5.9.8
pycparser==2.21
pydantic==2.6.0
pydantic-core==2.16.1
pyparsing==3.1.1
python-multipart==0.0.7
referencing==0.33.0
rfc3339-validator==0.1.4
rpds-py==0.17.1
six==1.16.0
sniffio==1.3.0
text-unidecode==1.3
uc-micro-py==1.0.3
universal-pathlib==0.1.4
wrapt==1.16.0
zipp==3.17.0
EOF
```

## Download Strategy for Offline Installation

### Step 1: On Internet-Connected Machine

```bash
# Create download directory
mkdir -p airflow_offline_packages/{rpms,python}
cd airflow_offline_packages

# Download all Python packages with dependencies
pip3 download -r ../airflow_offline_requirements.txt -d python/

# For Rocky Linux 9 RPMs (on a Rocky 9 machine with internet)
# Download RPMs with dependencies
sudo dnf download --resolve --destdir=rpms/ \
    gcc gcc-c++ make python3 python3-devel python3-pip \
    postgresql-server postgresql postgresql-contrib postgresql-devel \
    erlang rabbitmq-server \
    nfs-utils rpcbind \
    openssl-devel libffi-devel libxml2-devel libxslt-devel \
    git wget curl tar gzip unzip vim nano tmux screen htop

# Create repository metadata
createrepo rpms/
```

### Step 2: Transfer to Offline Environment

```bash
# Create tarball
tar -czf airflow_offline_packages.tar.gz airflow_offline_packages/

# Transfer to offline servers via USB/Network
```

### Step 3: Setup Local Repository on Offline Servers

On each offline VM:
```bash
# Extract packages
tar -xzf airflow_offline_packages.tar.gz

# Setup local YUM repository
sudo mkdir -p /opt/local-repo
sudo cp -r airflow_offline_packages/rpms/* /opt/local-repo/
sudo createrepo /opt/local-repo/

# Create repo file
sudo cat > /etc/yum.repos.d/local-airflow.repo << 'EOF'
[local-airflow]
name=Local Airflow Repository
baseurl=file:///opt/local-repo/
enabled=1
gpgcheck=0
EOF

# Clean and update cache
sudo dnf clean all
sudo dnf makecache
```

### Step 4: Install Python Packages Offline

```bash
# Install from local wheels
cd airflow_offline_packages/python/
pip3 install --no-index --find-links . apache-airflow[celery,postgres,crypto,ssh]==2.9.0

# Or with constraint file
pip3 install --no-index --find-links . -r ../airflow_offline_requirements.txt
```

## Additional Offline Considerations

### 1. RabbitMQ Offline Installation
```bash
# RabbitMQ requires specific Erlang version
# Download from: https://github.com/rabbitmq/erlang-rpm/releases
# And: https://github.com/rabbitmq/rabbitmq-server/releases

# Include these specific versions:
erlang-25.3.2.8-1.el9.x86_64.rpm
rabbitmq-server-3.12.13-1.el9.noarch.rpm
```

### 2. PostgreSQL Specific Files
```bash
# PostgreSQL 13 for Rocky 9
postgresql13-server
postgresql13
postgresql13-contrib
postgresql13-devel
postgresql13-libs
```

### 3. Python Wheels Architecture
```bash
# Ensure you download wheels for the correct architecture
# For Rocky Linux 9 on x86_64:
# - manylinux2014_x86_64
# - manylinux_2_17_x86_64
# - any (platform independent)
```

### 4. Create Installation Scripts

Create an installation script for each VM type:

```bash
# install_vm1.sh - Main Airflow
#!/bin/bash
sudo dnf install -y gcc gcc-c++ postgresql-server rabbitmq-server nfs-utils
pip3 install --no-index --find-links ./python/ apache-airflow[celery,postgres,crypto,ssh]==2.9.0

# install_vm2.sh - NFS + DAG Processor  
#!/bin/bash
sudo dnf install -y gcc gcc-c++ nfs-utils
pip3 install --no-index --find-links ./python/ apache-airflow[celery,postgres]==2.9.0

# install_vm4.sh - Worker
#!/bin/bash
sudo dnf install -y gcc gcc-c++ nfs-utils
pip3 install --no-index --find-links ./python/ apache-airflow[celery,postgres,ssh]==2.9.0 paramiko
```

