# **Installation Commands by VM**

## **ALL VMs (VM1-VM14) - Base System:**
```bash
sudo dnf update -y
sudo dnf upgrade -y
sudo dnf install -y vim curl wget rsync nfs-utils firewalld
```

## **VM1 (airflow) - Main Scheduler + Webserver + HAProxy:**
```bash
sudo dnf install -y haproxy keepalived curl
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres,crypto]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install "celery==5.5.0" "flower==1.2.0"
pip3 install paramiko
```

## **VM2 (ftp) - NFS Primary + DAG Processor:**
```bash
sudo dnf install -y nfs-utils lsyncd keepalived
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
```

## **VM3 (card1) - Target System:**
```bash
# Base packages only (already installed above)
```

## **VM4 (worker1) - Celery Worker:**
```bash
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install paramiko
```

## **VM5,6,7 (mq1,2,3) - RabbitMQ Cluster:**
```bash
wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.7/rabbitmq-server-3.13.7-1.el8.noarch.rpm
sudo rpm --import https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
sudo dnf install -y socat logrotate
sudo dnf install -y ./rabbitmq-server-3.13.7-1.el8.noarch.rpm
```

## **VM8,9,10 (sql1,2,3) - PostgreSQL + etcd + Patroni:**
```bash
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql16-server postgresql16-contrib

# Install etcd
ETCD_VER=v3.4.34
DOWNLOAD_URL=https://storage.googleapis.com/etcd
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
sudo mv /tmp/etcd-download-test/etcd* /usr/local/bin

# Install Patroni
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++
pip3 install psycopg2-binary
pip3 install patroni[etcd,consul]
```

## **VM12 (nfs2) - NFS Standby + DAG Processor:**
```bash
sudo dnf install -y nfs-utils lsyncd keepalived
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install "apache-airflow-providers-ssh==4.0.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
```

## **VM13 (scheduler2) - Scheduler HA:**
```bash
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres,crypto]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install paramiko
```

## **VM14 (haproxy2) - Webserver + HAProxy Standby:**
```bash
sudo dnf install -y haproxy keepalived curl
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ postgresql-devel

pip3 install "apache-airflow[celery,postgres,crypto]==2.9.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.9.txt"
pip3 install paramiko
```


sudo subscription-manager repos --enable=rhel-9-for-x86_64-baseos-rpms; sudo subscription-manager repos --enable=rhel-9-for-x86_64-appstream-rpms; sudo subscription-manager repos --enable=codeready-builder-for-rhel-9-x86_64-rpms; sudo subscription-manager repos --enable=rhel-9-for-x86_64-supplementary-rpms; sudo subscription-manager repos --enable=rhel-9-for-x86_64-optional-rpms   



   sudo subscription-manager repos --enable codeready-builder-for-rhel-9-$(arch)-rpms ;sudo dnf -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm ; sudo dnf install htop -y


