# Understanding TaskFlow API and Python Decorators

Let me explain decorators and TaskFlow API step by step, starting from the core concepts.

## What are Python Decorators?

**Simple Definition:** A decorator is like a **wrapper** or **modifier** that changes how a function behaves without changing the function's code.

**Real-world analogy:** Think of decorators like gift wrapping:
- You have a gift (your function)
- You wrap it with decorative paper (the decorator)
- The gift is still the same inside, but now it looks different and has extra features

### Basic Decorator Example

```python
# This is a simple decorator
def make_bold(func):
    def wrapper():
        result = func()
        return f"**{result}**"  # Add bold formatting
    return wrapper

# Using the decorator
@make_bold
def say_hello():
    return "Hello World"

# When you call the function:
print(say_hello())  # Output: **Hello World**
```

**What happened:**
1. The `@make_bold` decorator "wrapped" the `say_hello` function
2. Now when you call `say_hello()`, it runs through the decorator first
3. The decorator adds `**` around the result

### How Decorators Work (Step by Step)

```python
# Without decorator (manual way):
def say_hello():
    return "Hello World"

# Manually applying the decorator:
say_hello = make_bold(say_hello)

# With decorator (automatic way):
@make_bold
def say_hello():
    return "Hello World"
```

Both approaches do the same thing - the `@` symbol is just syntactic sugar!

## Airflow's TaskFlow API Decorators

Airflow uses decorators to transform regular Python functions into Airflow tasks and DAGs.

### Core TaskFlow Decorators

1. **`@dag`** - Transforms a function into a DAG
2. **`@task`** - Transforms a function into a Task

Let's break down your example:

## Complete TaskFlow API Breakdown

```python
from airflow.decorators import dag, task
from datetime import datetime

# DECORATOR: @dag transforms this function into a DAG
@dag(
    dag_id='taskflow_example',        # Unique identifier for this DAG
    schedule_interval='@daily',       # Run once per day
    start_date=datetime(2025, 1, 1),  # When to start running
    catchup=False                     # Don't run for past dates
)
def my_taskflow_dag():
    """This function becomes a DAG thanks to @dag decorator"""
    
    # DECORATOR: @task transforms this function into a Task
    @task
    def extract():
        """This function becomes a task that extracts data"""
        return ['file1.txt', 'file2.txt']  # Return data to next task
    
    # DECORATOR: Another @task for processing
    @task  
    def process(files):
        """This function becomes a task that processes data"""
        # The 'files' parameter receives data from extract() task
        return f"Processed {len(files)} files"
    
    # TASK FLOW: Define how tasks connect
    files = extract()      # Run extract task, get result
    result = process(files) # Run process task with extract's result
    
    # Note: No explicit return needed for DAG function

# CREATE DAG INSTANCE: This actually creates the DAG object
dag_instance = my_taskflow_dag()
```

## What Happens Behind the Scenes

### Traditional Way (Before TaskFlow API):

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# 1. Define functions separately
def extract_func():
    return ['file1.txt', 'file2.txt']

def process_func(**context):
    # Complex XCom pulling required
    ti = context['task_instance']
    files = ti.xcom_pull(task_ids='extract_task')
    return f"Processed {len(files)} files"

# 2. Create DAG manually
with DAG(
    dag_id='traditional_example',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:
    
    # 3. Create operators manually
    extract_task = PythonOperator(
        task_id='extract_task',
        python_callable=extract_func
    )
    
    process_task = PythonOperator(
        task_id='process_task',
        python_callable=process_func
    )
    
    # 4. Define dependencies manually
    extract_task >> process_task
```

### TaskFlow Way (Airflow 2.0+):

```python
from airflow.decorators import dag, task
from datetime import datetime

@dag(
    dag_id='taskflow_example',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False
)
def my_taskflow_dag():
    
    @task
    def extract():
        return ['file1.txt', 'file2.txt']
    
    @task  
    def process(files):
        return f"Processed {len(files)} files"
    
    # TaskFlow automatically handles XCom passing
    files = extract()
    result = process(files)

dag_instance = my_taskflow_dag()
```

**Much simpler!** TaskFlow handles all the complex XCom passing automatically.

## Advanced TaskFlow Examples

### 1. Multiple Outputs
```python
@task(multiple_outputs=True)
def extract_multiple():
    return {
        "users": ["Alice", "Bob"],
        "orders": [100, 200, 300]
    }

@task
def process_users(users):
    return f"Found {len(users)} users"

@task
def process_orders(orders):
    return f"Found {len(orders)} orders"

# Usage in DAG
data = extract_multiple()
user_result = process_users(data["users"])
order_result = process_orders(data["orders"])
```

### 2. Task with Configuration
```python
@task(retries=3, retry_delay=timedelta(minutes=5))
def risky_task():
    # This task will retry 3 times if it fails
    return "Success after potential retries"

@task.bash
def run_shell_command():
    return "echo 'Hello from bash'"
```

### 3. Conditional Tasks
```python
@task
def check_condition():
    return True  # Some business logic

@task
def task_if_true():
    return "Condition was true"

@task
def task_if_false():
    return "Condition was false"

# Conditional execution
condition = check_condition()
if condition:
    result = task_if_true()
else:
    result = task_if_false()
```

## Benefits of TaskFlow API

1. **Simpler Syntax**: Less boilerplate code
2. **Automatic XCom Handling**: Data passing is transparent
3. **Type Hints**: Better IDE support and documentation
4. **Pythonic**: Feels like normal Python code
5. **Automatic Dependencies**: Task flow is inferred from function calls

## Common TaskFlow Decorators

| Decorator | Purpose | Example |
|-----------|---------|---------|
| `@dag` | Creates a DAG | `@dag(schedule_interval='@daily')` |
| `@task` | Creates a Python task | `@task` |
| `@task.bash` | Creates a Bash task | `@task.bash` |
| `@task.python` | Same as `@task` | `@task.python` |
| `@task.virtualenv` | Task in virtual environment | `@task.virtualenv(requirements=['pandas'])` |
| `@task.docker` | Task in Docker container | `@task.docker(image='python:3.9')` |

## Complete Real-World Example

```python
from airflow.decorators import dag, task
from datetime import datetime, timedelta
import requests
import pandas as pd

@dag(
    dag_id='data_pipeline',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=5)
    }
)
def data_processing_pipeline():
    """
    A complete data pipeline using TaskFlow API
    """
    
    @task
    def extract_data(api_url: str = "https://api.example.com/data"):
        """Extract data from API"""
        response = requests.get(api_url)
        return response.json()
    
    @task
    def transform_data(raw_data: dict):
        """Transform the raw data"""
        df = pd.DataFrame(raw_data)
        # Perform transformations
        df['processed_date'] = datetime.now()
        return df.to_dict('records')
    
    @task
    def load_data(processed_data: list):
        """Load data to destination"""
        print(f"Loading {len(processed_data)} records")
        # In real scenario: save to database
        return f"Successfully loaded {len(processed_data)} records"
    
    @task
    def send_notification(load_result: str):
        """Send completion notification"""
        print(f"Pipeline completed: {load_result}")
    
    # Define the pipeline flow
    raw_data = extract_data()
    processed_data = transform_data(raw_data)
    load_result = load_data(processed_data)
    send_notification(load_result)

# Create the DAG instance
data_pipeline = data_processing_pipeline()
```

This pipeline automatically handles:
- Data passing between tasks via XCom
- Task dependencies based on function calls
- Error handling and retries
- Clean, readable code structure

The TaskFlow API makes Airflow DAGs much more intuitive and Pythonic!    


```
================================================================================   
```

# TaskFlow Decorators Explained

## @task.bash - Running Shell Commands

```python
@task.bash
def run_shell_command():
    return "echo 'Hello from bash'"
```

**What happens when this runs:**
1. Airflow takes the **return value** (`"echo 'Hello from bash'"`)
2. Executes it as a **bash command** in the terminal
3. You'll see output: `Hello from bash`

**Key Point:** The function **returns a bash command string**, not Python code!

## @task vs @task.python

**They are EXACTLY the same!**

```python
@task
def my_function():
    return "Hello from Python"

# Same as:
@task.python  
def my_function():
    return "Hello from Python"
```

`@task` is just a shortcut for `@task.python`. Both run Python code.

## Common TaskFlow Decorators with Examples

### 1. @task.virtualenv - Different Python Environment

```python
@task.virtualenv(
    requirements=["pandas==1.5.0", "requests==2.28.0"],  # Install these packages
    python_version="3.9",                                # Use Python 3.9
    system_site_packages=False                           # Don't use system packages
)
def analyze_data():
    import pandas as pd  # This pandas version only exists in this task
    import requests
    
    # Your code here - runs in isolated environment
    df = pd.DataFrame({"col1": [1, 2, 3]})
    return df.to_dict()
```

**What happens:** Creates a temporary Python environment just for this task.

### 2. @task.docker - Run in Docker Container

```python
@task.docker(
    image="python:3.9-slim",          # Docker image to use
    command=None,                     # Let Airflow handle the command
    environment={"MY_VAR": "value"}   # Environment variables
)
def process_in_container():
    # This runs inside a Docker container
    return "Hello from Docker!"
```

### 3. @task.kubernetes - Run in Kubernetes Pod

```python
@task.kubernetes(
    image="python:3.9",
    namespace="airflow",              # Kubernetes namespace
    name="my-k8s-task"               # Pod name
)
def run_in_k8s():
    return "Hello from Kubernetes!"
```

### 4. @task.external_python - Use Different Python Installation

```python
@task.external_python(
    python="/usr/bin/python3.8"      # Path to specific Python version
)
def run_with_different_python():
    import sys
    return f"Running with Python {sys.version}"
```

### 5. @task with Configuration Parameters

```python
@task(
    retries=3,                        # Retry 3 times if fails
    retry_delay=timedelta(minutes=5), # Wait 5 minutes between retries
    pool="slow_tasks",                # Use specific resource pool
    queue="high_priority"             # Use specific Celery queue
)
def configured_task():
    return "Task with custom config"
```

## Decorator Parameters Syntax

**General Pattern:**
```python
@decorator_name(
    parameter1=value1,
    parameter2=value2,
    parameter3=value3
)
def my_function():
    # function body
```

**Common Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `retries` | int | How many times to retry | `retries=3` |
| `retry_delay` | timedelta | Wait time between retries | `retry_delay=timedelta(minutes=5)` |
| `pool` | string | Resource pool name | `pool="database_pool"` |
| `queue` | string | Celery queue name | `queue="high_priority"` |
| `timeout` | int | Task timeout in seconds | `timeout=300` |
| `depends_on_past` | bool | Wait for previous run | `depends_on_past=True` |

## Complete Example with Multiple Decorators

```python
from airflow.decorators import dag, task
from datetime import datetime, timedelta

@dag(start_date=datetime(2025, 1, 1), schedule_interval='@daily')
def multi_environment_pipeline():
    
    @task.bash
    def create_directory():
        return "mkdir -p /tmp/airflow_data"
    
    @task
    def generate_data():
        return {"users": 100, "orders": 250}
    
    @task.virtualenv(
        requirements=["pandas==1.5.0"],
        system_site_packages=False
    )
    def analyze_with_pandas(data):
        import pandas as pd
        df = pd.DataFrame([data])
        return df.describe().to_dict()
    
    @task.docker(
        image="python:3.9-alpine",
        environment={"LOG_LEVEL": "INFO"}
    )
    def process_in_docker(analysis):
        import os
        log_level = os.getenv("LOG_LEVEL", "DEBUG")
        return f"Processed analysis with log level: {log_level}"
    
    # Workflow
    create_directory()
    data = generate_data()
    analysis = analyze_with_pandas(data)
    result = process_in_docker(analysis)

multi_environment_pipeline()
```

**Key Takeaway:** Different decorators run your code in different environments, but the syntax pattern is always the same: `@decorator(parameters)`.


