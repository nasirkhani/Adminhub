
# Airflow Migration Manual — GitOps for DAGs + MinIO for Logs

**Audience:** Ops/Platform engineers  
**Goal:** Remove NFS from Airflow’s DAG/log path, introduce GitOps (atomic symlink) for DAG distribution and MinIO (S3-compatible) for task/scheduler logs.  
**Scope:** Works with existing stack (2× Scheduler, 2× Workers, Webservers, 3× RabbitMQ, 3× HAProxy, 3× Postgres Patroni + 3× etcd). NFS remains only for backup/archive (optional).

---

## 0) Prerequisites & Sizing

### 0.1 Nodes & Roles (no change to existing Airflow counts)
- Airflow: 2 Schedulers, 2 Workers, Webservers, 3× HAProxy, 3× RabbitMQ, 3× Postgres Patroni + 3× etcd.
- **New MinIO cluster: 4 nodes** behind HAProxy VIP.
- **Git server:** GitLab (self-hosted) or internal Git. Optional: 1–2 read-only mirrors (e.g., Gitea).

### 0.2 Hardware recommendations

#### MinIO (4 nodes, HA with erasure coding)

**Performance profile (high IOPS for logs):**
- CPU: 8 vCPU (or 4 physical cores with HT)
- RAM: 32 GB
- Disks: 2× NVMe 1.92 TB (or 4× SATA SSD 1.92 TB) as JBOD
- Network: 10GbE (prefer 2× bonded), consistent MTU end-to-end
- Filesystem: XFS or ext4, `noatime`
- Capacity note: With 8 devices total (4 nodes × 2 disks), effective usable is ~60–70% of raw (erasure coding).  
  Example: 8 × 1.92 TB ≈ 15.3 TB raw → ~9.5–11 TB usable.

**Capacity profile (large volume, moderate IOPS):**
- CPU: 8 vCPU
- RAM: 16–32 GB
- Disks: 4× HDD 8 TB per node (+ optional SSD cache)
- Network: 10GbE
- Usable ≈ 0.6–0.7 × raw (erasure coding)

> Tip: If you expect rapid log growth, favor SSDs and keep the erasure set balanced from day one.

#### GitLab (or internal Git)
- CPU: 4 vCPU
- RAM: 8–16 GB
- Disk: 200 GB SSD (minimum)
- Network: 1GbE OK (10GbE preferred in DC)

#### Git mirrors (optional)
- CPU: 2 vCPU
- RAM: 4 GB
- Disk: 50–100 GB SSD

---

## 1) Prepare all Airflow nodes (Schedulers/Webservers/Workers)

### 1.1 Base tools
```bash
# Debian/Ubuntu
apt-get update && apt-get install -y git rsync jq curl

# RHEL/CentOS/Rocky
yum install -y git rsync jq curl
```

### 1.2 Common directories & environment
```bash
install -d -o airflow -g airflow /opt/airflow
install -d -o airflow -g airflow /opt/airflow/{dags,logs,scheduler_logs}
install -d -o root    -g root    /etc/airflow/env.d

cat >/etc/airflow/env.d/airflow-gitops-minio <<'EOF'
export AF_USER=airflow
export AF_HOME=/opt/airflow
export DAG_DIR=$AF_HOME/dags
export DAG_RELEASES=$DAG_DIR/releases
export DAG_STAGING=$DAG_DIR/staging

# Git (GitLab VIP or internal Git)
export GIT_URL=git@gitlab-vip:<group_or_user>/airflow-dags.git
export GIT_BRANCH=main

# MinIO (S3-compatible)
export MINIO_ENDPOINT=http://minio-vip:9000
export MINIO_ACCESS_KEY=REPLACE_ME
export MINIO_SECRET_KEY=REPLACE_ME
export MINIO_BUCKET_TASK=airflow-logs
export MINIO_BUCKET_SCHED=airflow-scheduler-logs
EOF

echo 'source /etc/airflow/env.d/airflow-gitops-minio' >/etc/profile.d/airflow.sh
```

### 1.3 Git deploy keys (read-only)
```bash
sudo -u airflow install -d /opt/airflow/.ssh
sudo -u airflow ssh-keygen -t ed25519 -N "" -f /opt/airflow/.ssh/id_ed25519
cat /opt/airflow/.ssh/id_ed25519.pub
# Add the public key as a Deploy Key (Read-only) to the GitLab project
sudo -u airflow ssh -o StrictHostKeyChecking=accept-new git@gitlab-vip || true
```

---

## 2) Remove NFS from Airflow path (keep boxes for archive if needed)

On each Airflow node:
```bash
systemctl stop airflow-scheduler airflow-webserver airflow-worker 2>/dev/null || true
systemctl disable --now airflow-dags.mount airflow-logs.mount 2>/dev/null || true
umount -f /opt/airflow/dags  2>/dev/null || true
umount -f /opt/airflow/logs  2>/dev/null || true
cp -a /etc/fstab /etc/fstab.bak
sed -i '/airflow-dags/d;/airflow-logs/d' /etc/fstab
```

NFS remains only for backup/archive, not in the Airflow execution path.

---

## 3) GitOps for DAGs (pull + atomic symlink)

### 3.1 Rollout script
`/usr/local/bin/deploy_dag.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
source /etc/airflow/env.d/airflow-gitops-minio

TAG="${1:-}"
[[ -z "$TAG" ]] && { echo "usage: $0 <tag>"; exit 2; }

install -d -m 0755 -o $AF_USER -g $AF_USER "$DAG_STAGING/repo" "$DAG_RELEASES"

cd "$DAG_STAGING"
if [[ ! -d repo/.git ]]; then
  sudo -u $AF_USER git clone --filter=blob:none -b "$GIT_BRANCH" "$GIT_URL" repo
fi

cd repo
sudo -u $AF_USER git fetch --tags --force
sudo -u $AF_USER git checkout --detach "refs/tags/$TAG"
# Optional: sudo -u $AF_USER git verify-tag "$TAG"

SRC="."
DST="$DAG_RELEASES/$TAG"
rm -rf "$DST" && install -d -m 0755 -o $AF_USER -g $AF_USER "$DST"
rsync -a --delete "$SRC/dags" "$SRC/plugins" "$SRC/include" "$DST/" 2>/dev/null || true

# sanity: import test
sudo -u $AF_USER AIRFLOW_HOME=$AF_HOME airflow dags list --subdir "$DST/dags" >/dev/null

ln -sfn "$DST" "$DAG_DIR/current"
date -u +"%FT%TZ $TAG" > "$DST/DEPLOYED"
echo "[ok] DAGs deployed: $TAG"
```
```bash
chmod +x /usr/local/bin/deploy_dag.sh
```

### 3.2 Systemd unit to deploy a specific tag
`/etc/systemd/system/airflow-dag-deploy@.service`:
```ini
[Unit]
Description=Deploy Airflow DAGs at tag %i
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=airflow
Group=airflow
EnvironmentFile=/etc/airflow/env.d/airflow-gitops-minio
ExecStart=/usr/local/bin/deploy_dag.sh %i
```

### 3.3 Timer to poll latest release tag (only `rel-*`)
`/usr/local/bin/dag_timer_check.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
source /etc/airflow/env.d/airflow-gitops-minio
install -d -m 0755 -o $AF_USER -g $AF_USER "$DAG_STAGING/repo"
cd "$DAG_STAGING"

if [[ ! -d repo/.git ]]; then
  sudo -u $AF_USER git clone --filter=blob:none -b "$GIT_BRANCH" "$GIT_URL" repo
fi

cd repo
sudo -u $AF_USER git fetch --tags --force
NEW=$(git tag -l 'rel-*' --sort=-creatordate | head -n1 || echo "")
[[ -z "$NEW" ]] && exit 0

CUR=$(readlink -f "$DAG_DIR/current" | xargs -r basename || true)
[[ "$NEW" == "$CUR" ]] && exit 0

systemctl start "airflow-dag-deploy@${NEW}.service"
```
```bash
chmod +x /usr/local/bin/dag_timer_check.sh
```

`/etc/systemd/system/airflow-dag-pull.service`:
```ini
[Unit]
Description=Poll Git for newest DAG tag and deploy
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/dag_timer_check.sh
```

`/etc/systemd/system/airflow-dag-pull.timer`:
```ini
[Unit]
Description=Run DAG pull every 60s

[Timer]
OnBootSec=30
OnUnitActiveSec=60
Unit=airflow-dag-pull.service

[Install]
WantedBy=timers.target
```
Enable:
```bash
systemctl daemon-reload
systemctl enable --now airflow-dag-pull.timer
```

---

## 4) MinIO cluster (4 nodes) + HAProxy VIP

### 4.1 MinIO install on each MinIO node
```bash
useradd -r -s /sbin/nologin minio-user || true
install -d -o minio-user -g minio-user /data/minio{1,2}

curl -L https://dl.min.io/server/minio/release/linux-amd64/minio -o /usr/local/bin/minio
chmod +x /usr/local/bin/minio

cat >/etc/minio.env <<'EOF'
MINIO_ROOT_USER=REPLACE_ME
MINIO_ROOT_PASSWORD=REPLACE_ME_STRONG
MINIO_VOLUMES="/data/minio1 /data/minio2"
MINIO_SERVER_URL="http://minio-vip:9000"
EOF
chmod 600 /etc/minio.env
```

`/etc/systemd/system/minio.service`:
```ini
[Unit]
Description=MinIO
After=network-online.target
Wants=network-online.target

[Service]
User=minio-user
Group=minio-user
EnvironmentFile=/etc/minio.env
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES --address :9000 --console-address :9001
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```
Start:
```bash
systemctl daemon-reload
systemctl enable --now minio
```

### 4.2 HAProxy for S3 VIP
Example:
```
backend s3_back
  balance roundrobin
  option httpchk GET /minio/health/cluster
  server m1 10.0.0.11:9000 check
  server m2 10.0.0.12:9000 check
  server m3 10.0.0.13:9000 check
  server m4 10.0.0.14:9000 check

frontend s3_front
  bind *:9000
  default_backend s3_back
```

### 4.3 Buckets & ILM
```bash
curl -L https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
chmod +x /usr/local/bin/mc

source /etc/airflow/env.d/airflow-gitops-minio
mc alias set minio $MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc mb minio/$MINIO_BUCKET_TASK
mc mb minio/$MINIO_BUCKET_SCHED
mc ilm add --expire-days 90 minio/$MINIO_BUCKET_TASK
mc ilm add --expire-days 90 minio/$MINIO_BUCKET_SCHED
```

---

## 5) Airflow remote logging (MinIO)

### 5.1 Install Amazon provider
```bash
pip install 'apache-airflow-providers-amazon>=10'
```

### 5.2 Create MinIO connection
Option A (CLI):
```bash
source /etc/airflow/env.d/airflow-gitops-minio
airflow connections add minio_conn \
  --conn-type aws \
  --conn-extra '{"endpoint_url":"'"$MINIO_ENDPOINT"'","aws_access_key_id":"'"$MINIO_ACCESS_KEY"'","aws_secret_access_key":"'"$MINIO_SECRET_KEY"'"}'
```
Option B (ENV):
```bash
export AIRFLOW_CONN_MINIO_CONN='aws://?aws_access_key_id='"$MINIO_ACCESS_KEY"'&aws_secret_access_key='"$MINIO_SECRET_KEY"'&endpoint_url='"$MINIO_ENDPOINT"
```

### 5.3 Edit `airflow.cfg` on all Airflow nodes
```ini
[core]
dags_folder = /opt/airflow/dags/current/dags
base_log_folder = /opt/airflow/logs
store_serialized_dags = True

[logging]
remote_logging = True
remote_log_conn_id = minio_conn
remote_base_log_folder = s3://airflow-logs
```

> Scheduler logs: either ship via Fluent Bit from `/opt/airflow/scheduler_logs` to `s3://airflow-scheduler-logs`, or author a custom `logging_config.py` with S3 handlers.

---

## 6) Service coordination & remove NFS dependencies

Adjust Airflow systemd units to remove any `Requires=/After=` on NFS mounts.  
Optional: ensure scheduler starts after first pull:
```ini
# /etc/systemd/system/airflow-scheduler.service (example)
[Unit]
After=network-online.target airflow-dag-pull.service
Wants=network-online.target
```
Apply:
```bash
systemctl daemon-reload
systemctl enable airflow-scheduler airflow-webserver airflow-worker
```

---

## 7) Cutover & acceptance

1) Start services:
```bash
systemctl start airflow-scheduler airflow-webserver airflow-worker
```
2) Create a release tag:
```bash
git tag -a rel-YYYY.MM.DD-01 -m "first gitops release"
git push --tags
```
3) Wait for timer (~60s) or trigger manually:
```bash
systemctl start airflow-dag-deploy@rel-YYYY.MM.DD-01
```
4) DAG sanity:
```bash
sudo -u airflow AIRFLOW_HOME=/opt/airflow airflow dags list
```
5) Log test:
```bash
sudo -u airflow AIRFLOW_HOME=/opt/airflow airflow tasks test example_bash_operator runme_0 2025-10-25
mc ls -r minio/airflow-logs | head
```
6) Acceptance criteria:
- UI shows task logs from MinIO.
- `readlink -f /opt/airflow/dags/current` identical across nodes.
- No write errors to MinIO; normal latency on Rabbit/PG.

---

## 8) Migrate old logs (optional)
```bash
# rclone
rclone copy /OLD/NFS/airflow/logs minio:$MINIO_BUCKET_TASK \
  --s3-provider Minio --s3-endpoint $MINIO_ENDPOINT \
  --s3-access-key-id $MINIO_ACCESS_KEY --s3-secret-access-key $MINIO_SECRET_KEY

# or mc
mc mirror /OLD/NFS/airflow/logs minio/$MINIO_BUCKET_TASK
```

---

## 9) GitLab CI (optional but recommended)

### 9.1 Protections
- Protected Tags: `rel-*`
- Deploy Keys: read-only keys of Airflow nodes

### 9.2 RC → REL flow (example `.gitlab-ci.yml`)
- CI runs lint & import tests on `rc-*` tags, then promotes to `rel-*` if green.
- Airflow agents deploy only `rel-*` tags (already enforced in `dag_timer_check.sh`).

---

## 10) Monitoring & operations
- **MinIO:** `/minio/health/cluster` health; alert on write errors and >80% capacity.
- **Airflow:** scheduler heartbeat, task failure rate, parse time.
- **RabbitMQ:** ready/unacked, flow control.
- **Postgres:** replication lag, lock waits.
- **GitOps:** a “Health DAG” to check tag/version across nodes and alert on mismatch.

---

## 11) Rollback
- **DAGs:**
```bash
PREV=$(ls -1 /opt/airflow/dags/releases | sort | tail -n2 | head -n1)
systemctl start "airflow-dag-deploy@${PREV}.service"
```
- **Logs:** temporarily set
```ini
[logging]
remote_logging = False
```
and point `base_log_folder` to a local path, then re-enable after fix.

---

### Appendix A — File list to create
- `/etc/airflow/env.d/airflow-gitops-minio`
- `/usr/local/bin/deploy_dag.sh` (chmod +x)
- `/etc/systemd/system/airflow-dag-deploy@.service`
- `/usr/local/bin/dag_timer_check.sh` (chmod +x)
- `/etc/systemd/system/airflow-dag-pull.service`
- `/etc/systemd/system/airflow-dag-pull.timer`
- `/etc/systemd/system/minio.service` (on MinIO nodes)

### Appendix B — Quick checklist
- NFS mounts disabled and removed from `/etc/fstab`
- GitOps timer enabled, symlink points to a tagged release
- Airflow remote logging configured to MinIO and connection present
- MinIO buckets created with ILM
- Acceptance tests passed and monitoring dashboards updated

