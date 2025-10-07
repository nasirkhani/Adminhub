### **Issue Summary**

When starting the **Airflow Celery Worker** service, it failed with:

```
AirflowConfigException: Failed to convert value to int. Please check "WORKER_LOG_SERVER_PORT" key in "logging" section. Current value: "".
```

### **Root Cause**

The Airflow worker configuration (`airflow.cfg`) had an empty setting for
`worker_log_server_port` in the `[logging]` section.
This port is required by Airflow even if logs are written to shared storage, because each worker starts a small internal HTTP server that allows the Airflow web UI to fetch and display task logs remotely.

### **Resolution**

We added the missing configuration line:

```ini
worker_log_server_port = 8793
```

and restarted the worker service:

```bash
sudo systemctl restart airflow-worker
```

After the fix, the worker started successfully and began processing tasks normally.

### **Logging Behavior Explained**

| Type                  | Purpose                                                                                               | How Logs Are Accessed                             | Our Setup                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------- |
| **Local Logging**     | Writes logs to a folder defined by `base_log_folder`.                                                 | Files stored directly on each worker.             | Enabled (`/home/rocky/airflow/logs` mounted on NFS).        |
| **Worker Log Server** | Serves logs over HTTP from each worker to the Airflow Web UI. Controlled by `worker_log_server_port`. | The Web UI fetches logs from this port if needed. | Required syntactically; not heavily used due to shared NFS. |
| **Remote Logging**    | Sends logs to external storage (S3, GCS, Elasticsearch, etc.).                                        | UI reads logs from remote backend.                | Not used.                                                   |

### **Outcome**

* Worker services now start cleanly.
* Logs are correctly written to and accessible via the shared NFS directory.
* Airflow UI can retrieve logs seamlessly from either shared storage or worker HTTP port if required.

---

