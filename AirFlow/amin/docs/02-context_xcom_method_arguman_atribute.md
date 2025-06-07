# Airflow Context Classes - Methods & Arguments

## 1. Context Classes and Their Key Methods

### `context['task_instance']` - TaskInstance Class
```python
ti = context['task_instance']

# Data Methods
ti.xcom_pull(task_ids='task_name', key='return_value')
ti.xcom_push(key='my_key', value='my_data')

# Properties
ti.task_id          # Current task name
ti.dag_id           # DAG name  
ti.execution_date   # When task should run
ti.state            # Task status (running, success, failed)
ti.try_number       # Which attempt (1, 2, 3...)
```

### `context['dag']` - DAG Class
```python
dag = context['dag']

# Properties
dag.dag_id          # DAG name
dag.description     # DAG description
dag.schedule_interval  # How often it runs
dag.start_date      # When DAG starts
dag.tags            # DAG tags list

# Methods
dag.get_task(task_id='task_name')  # Get specific task
```

### `context['dag_run']` - DagRun Class
```python
dag_run = context['dag_run']

# Properties  
dag_run.dag_id         # DAG name
dag_run.execution_date # When this run started
dag_run.run_id         # Unique run identifier
dag_run.state          # Run status (running, success, failed)
dag_run.conf           # Runtime configuration

# Methods
dag_run.get_task_instances()  # All task instances in this run
```

### `context['task']` - Task Class
```python
task = context['task']

# Properties
task.task_id        # Task name
task.owner          # Task owner
task.retries        # Number of retries
task.email          # Email for notifications
task.pool           # Resource pool
```

## 2. XCom Methods Arguments

### `xcom_pull()` Arguments
```python
ti.xcom_pull(
    task_ids='task_name',           # Required: which task's data
    key='return_value',             # Optional: specific key (default: 'return_value')
    include_prior_dates=False,      # Optional: search previous dates
    dag_id=None,                    # Optional: different DAG (default: current)
    map_indexes=None                # Optional: for mapped tasks
)

# Examples:
files = ti.xcom_pull(task_ids='discover_files')
data = ti.xcom_pull(task_ids='process', key='result')
multi = ti.xcom_pull(task_ids=['task1', 'task2'])
```

### `xcom_push()` Arguments
```python
ti.xcom_push(
    key='my_key',                   # Required: data identifier
    value='my_data',                # Required: actual data
    execution_date=None             # Optional: specific date (default: current)
)

# Examples:
ti.xcom_push(key='files', value=['file1.txt', 'file2.txt'])
ti.xcom_push(key='count', value=42)
ti.xcom_push(key='result', value={'status': 'success'})
```

## 3. Other Useful Context Items

### `context['execution_date']` - datetime
```python
exec_date = context['execution_date']
exec_date.strftime('%Y-%m-%d')      # Format date
exec_date.year                      # Get year
```

### `context['params']` - dict
```python
params = context['params']          # User-defined parameters
value = params.get('my_param', 'default')
```

### `context['conf']` - dict  
```python
conf = context['conf']              # Runtime configuration
setting = conf.get('my_setting')
```

## 4. Quick Reference Table

| Context Key | Type | Main Use | Key Methods/Properties |
|-------------|------|----------|----------------------|
| `task_instance` | TaskInstance | Current task info | `.xcom_pull()`, `.xcom_push()`, `.task_id` |
| `dag` | DAG | Workflow info | `.dag_id`, `.schedule_interval` |
| `dag_run` | DagRun | Current run info | `.execution_date`, `.run_id`, `.state` |
| `task` | Task | Task definition | `.task_id`, `.owner`, `.retries` |
| `execution_date` | datetime | When task runs | `.strftime()`, `.year`, `.month` |
| `params` | dict | User parameters | `.get()`, `['key']` |

## 5. Common Usage Patterns

```python
def my_task(**context):
    # Get current task info
    ti = context['task_instance']
    current_task = ti.task_id
    
    # Get data from previous task
    data = ti.xcom_pull(task_ids='previous_task')
    
    # Get execution date
    run_date = context['execution_date']
    
    # Send data to next task
    ti.xcom_push(key='result', value=processed_data)
    
    # Get DAG info
    dag_name = context['dag'].dag_id
```
