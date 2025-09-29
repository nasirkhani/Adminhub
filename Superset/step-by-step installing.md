
# Apache Superset Installation on Ubuntu 24.04 with Docker Compose

This guide explains how to install **Apache Superset** on **Ubuntu 24.04** step by step using **Docker Compose**.

---

## 0) Prerequisites: Install Docker & Compose

```bash
# Update CA certs
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo update-ca-certificates

# Install Docker Engine + Compose plugin
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# (Optional) allow your user to run docker without sudo
sudo usermod -aG docker $USER
```

---

## 1) Project structure

```bash
mkdir -p ~/superset
cd ~/superset
mkdir superset_home
```

---

## 2) Create `docker-compose.yml`

```yaml
services:
  superset_db:
    image: postgres:15
    container_name: superset_db
    environment:
      POSTGRES_DB: superset
      POSTGRES_USER: superset
      POSTGRES_PASSWORD: superset
    volumes:
      - superset_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U superset"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  superset_cache:
    image: redis:7
    container_name: superset_cache
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - superset_cache:/data
    restart: unless-stopped

  superset_app:
    image: apache/superset:latest
    container_name: superset_app
    depends_on:
      - superset_db
      - superset_cache
    environment:
      SUPERSET_CONFIG_PATH: /app/pythonpath/superset_config.py
      SUPERSET_LOAD_EXAMPLES: "no"
      SUPERSET_SECRET_KEY: "replace_me_with_a_long_random_secret"
    volumes:
      - ./superset_home:/app/superset_home
      - ./superset_config.py:/app/pythonpath/superset_config.py
    ports:
      - "8088:8088"
    command: >
      bash -c "
      superset db upgrade &&
      superset fab create-admin --username admin --firstname Superset --lastname Admin --email admin@superset.com --password admin || true &&
      superset init &&
      gunicorn -b 0.0.0.0:8088 --workers 4 --timeout 300 'superset.app:create_app()'
      "
    restart: unless-stopped

  superset_worker:
    image: apache/superset:latest
    container_name: superset_worker
    depends_on:
      - superset_app
    environment:
      SUPERSET_CONFIG_PATH: /app/pythonpath/superset_config.py
    volumes:
      - ./superset_home:/app/superset_home
      - ./superset_config.py:/app/pythonpath/superset_config.py
    command: worker
    restart: unless-stopped

  superset_worker_beat:
    image: apache/superset:latest
    container_name: superset_worker_beat
    depends_on:
      - superset_app
    environment:
      SUPERSET_CONFIG_PATH: /app/pythonpath/superset_config.py
    volumes:
      - ./superset_home:/app/superset_home
      - ./superset_config.py:/app/pythonpath/superset_config.py
    command: beat
    restart: unless-stopped

volumes:
  superset_db:
  superset_cache:
```

---

## 3) Create `superset_config.py`

```python
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://superset:superset@superset_db:5432/superset"

from cachelib.redis import RedisCache
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "REDIS_HOST": "superset_cache",
    "REDIS_PORT": 6379,
    "REDIS_DB": 1,
    "REDIS_URL": "redis://superset_cache:6379/1",
}

CELERY_BROKER_URL = "redis://superset_cache:6379/0"
CELERY_RESULT_BACKEND = "redis://superset_cache:6379/1"

SECRET_KEY = "replace_me_with_a_long_random_secret"
```

---

## 4) Start Superset

```bash
sudo docker compose up -d
```

Check logs:
```bash
sudo docker logs -f superset_app
```

---

## 5) Open the UI

- URL: [http://localhost:8088](http://localhost:8088)  
- Username: `admin`  
- Password: `admin`

If running on a remote server, replace `localhost` with the server IP.

---

## 6) Import a CSV

```bash
sudo docker cp sales.csv superset_app:/app/sales.csv

sudo docker exec -it superset_app superset import-csv   /app/sales.csv   --table-name sales   --database-name examples
```

---

