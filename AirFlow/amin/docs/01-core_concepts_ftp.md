# Airflow DAG Components - Essential Concepts

## 1. DAG (Directed Acyclic Graph)

**What it is:** The entire workflow/pipeline definition

```python
# This is a DAG
from airflow import DAG

my_dag = DAG(
    dag_id='my_workflow',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1)
)
```

**Think of it as:** A blueprint for your entire workflow

## 2. Task vs Task Instance

### Task
**What it is:** The definition/template of work to be done

```python
# This is a TASK definition
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_function,
    dag=my_dag
)
```

### Task Instance  
**What it is:** A specific execution of a task at a specific time

```python
# Task Instance examples:
# - extract_data running on 2025-05-26 at 10:00 AM
# - extract_data running on 2025-05-27 at 10:00 AM
# Each run = different Task Instance
```

**Analogy:**
- **Task** = "Send daily report email" (the plan)
- **Task Instance** = "Send daily report email on May 26, 2025" (actual execution)

## 3. Operator

**What it is:** A class that defines what type of work to do

```python
# Different operators for different work types:

# Python work
PythonOperator(python_callable=my_function)

# Bash commands  
BashOperator(bash_command='ls -la')

# SQL queries
PostgresOperator(sql='SELECT * FROM users')

# SSH commands
SSHOperator(command='python script.py')
```

**Think of it as:** Different tools for different jobs

## 4. Complete Example with All Components

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# 1. FUNCTIONS (what the work actually does)
def extract_data():
    return ["file1.txt", "file2.txt"]

def process_data(**context):
    files = context['task_instance'].xcom_pull(task_ids='extract')
    return f"Processed {len(files)} files"

# 2. DAG (the workflow container)
dag = DAG(
    dag_id='file_processing_workflow',           # DAG name
    description='Process files daily',
    schedule_interval='@daily',                  # When to run
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={
        'owner': 'data_team',
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    }
)

# 3. TASKS (using operators)
extract_task = PythonOperator(                   # This is a TASK
    task_id='extract',                           # Task name
    python_callable=extract_data,                # Function to run
    dag=dag                                      # Which DAG it belongs to
)

process_task = PythonOperator(                   # Another TASK
    task_id='process', 
    python_callable=process_data,
    dag=dag
)

cleanup_task = BashOperator(                     # TASK using different operator
    task_id='cleanup',
    bash_command='rm -f /tmp/*.temp',
    dag=dag
)

# 4. DEPENDENCIES (task order)
extract_task >> process_task >> cleanup_task
```

## 5. Key Relationships

```
DAG
 ├── Task 1 (using PythonOperator)
 ├── Task 2 (using BashOperator)  
 └── Task 3 (using SSHOperator)
      
When DAG runs:
 ├── Task Instance 1 (May 26, 10:00 AM)
 ├── Task Instance 2 (May 26, 10:05 AM)
 └── Task Instance 3 (May 26, 10:10 AM)
```

## 6. Essential Terminology Summary

| Term | What It Is | Example |
|------|------------|---------|
| **DAG** | Entire workflow | "Daily file processing pipeline" |
| **Task** | Work definition | "Extract data from API" |
| **Task Instance** | Specific task run | "Extract data on May 26, 2025" |
| **Operator** | Type of work | PythonOperator, BashOperator |
| **Function** | Actual work code | `def extract_data():` |
| **Context** | Runtime info | Current date, task details, etc. |
| **XCom** | Data sharing | Pass data between tasks |
| **Dependencies** | Task order | Task A >> Task B |

## 7. Your Code Breakdown

```python
# Your DAG file components:

# 1. FUNCTIONS (the actual work)
def discover_files_on_ftp(**context): pass
def transfer_files_via_ftp(**context): pass  
def process_files_on_vm3(**context): pass

# 2. DAG (workflow container)
with DAG(
    'ftp_file_processing_workflow',  # DAG name
    # ... DAG settings
) as dag:

    # 3. TASKS (using PythonOperator)
    discover_task = PythonOperator(           # TASK
        task_id='discover_files',             # Task name
        python_callable=discover_files_on_ftp # Function to run
    )
    
    transfer_task = PythonOperator(           # Another TASK
        task_id='transfer_files',
        python_callable=transfer_files_via_ftp
    )
    
    # 4. DEPENDENCIES
    discover_task >> transfer_task            # Task order
```

## 8. When DAG Runs (Runtime)

1. **Scheduler** reads your DAG file
2. Creates **Task Instances** for each task
3. **Executor** runs each Task Instance
4. **Tasks** communicate via **XCom**
5. **Context** provides runtime information

**Simple Mental Model:**
- **DAG** = Recipe book
- **Task** = Recipe steps  
- **Task Instance** = Actually cooking the meal
- **Operator** = Kitchen tools (oven, blender, etc.)
- **Function** = Your cooking skills
- **Context** = Current time, ingredients available, etc.

The beauty is that you write the recipe once (DAG + Tasks), and Airflow handles cooking it every day (Task Instances)!

```
Complete Flow Visualization

1. You write DAG file
   ↓
2. Scheduler reads DAG file  
   ↓
3. Scheduler creates TaskInstance (stores in database)
   ↓
4. Executor picks up TaskInstance
   ↓
5. TaskInstance builds context from:
   - Current TaskInstance object
   - Current DAG object  
   - Current DagRun object
   - Database values
   ↓
6. TaskInstance calls PythonOperator.execute(context)
   ↓
7. PythonOperator calls your_function(**context)
   ↓
8. Your function receives context dictionary
```

============================================================================================   

# Understanding `**context` in Python and Airflow

## 1. What is `**context` in Python?

### Basic Python `**kwargs` Concept

```python
# Example 1: Simple function
def greet(name):
    return f"Hello {name}"

# Example 2: Function with **kwargs
def greet_flexible(**kwargs):
    # kwargs is a dictionary containing all keyword arguments
    print(kwargs)  # Shows what was passed
    name = kwargs.get('name', 'Unknown')
    return f"Hello {name}"

# Usage:
greet_flexible(name="John", age=25, city="NYC")
# kwargs = {'name': 'John', 'age': 25, 'city': 'NYC'}
```

### The `**` Operator
- `**kwargs` = "keyword arguments" 
- `**context` = same thing, just named "context" instead of "kwargs"
- The name after `**` is **arbitrary** - you choose it!

```python
# These are ALL the same:
def my_func(**kwargs): pass
def my_func(**context): pass  
def my_func(**data): pass
def my_func(**whatever): pass
```

## 2. `**context` in Airflow

### Why Airflow Uses `**context`

When Airflow runs your task, it automatically passes **many** pieces of information:

```python
# What Airflow automatically passes (simplified):
airflow_context = {
    'task_instance': <current task object>,
    'dag': <current DAG object>,
    'execution_date': datetime(2025, 5, 26),
    'logical_date': datetime(2025, 5, 26),
    'dag_run': <current DAG run object>,
    'task': <task definition>,
    'params': {...},
    'conf': {...},
    # ... and many more!
}

# When Airflow calls your function:
your_function(**airflow_context)  # Unpacks all these variables
```

### Name Choice: Why "context"?

The name `**context` is **conventional**, not required:
- **"Context"** = surrounding information/environment
- Airflow community uses this name by convention
- Makes code more readable and understandable

```python
# These work exactly the same in Airflow:
def task1(**context): pass      # ✅ Conventional (preferred)
def task2(**kwargs): pass       # ✅ Works but less clear
def task3(**airflow_data): pass # ✅ Works but uncommon
```

## 3. Your Specific Function

```python
def discover_files_on_ftp(**context):
    """Discover all .txt files in /in/ directories on VM2"""
    find_command = f"find /home/{USERNAME} -name '*.txt' -path '*/in/*' -type f"
    
    try:
        result = run_ssh_command(VM2_HOST, find_command)
        # ... rest of function
```

### Why `**context` is There (Even if Unused)

1. **Airflow Requirement**: Some Airflow operators expect functions to accept `**context`
2. **Future-Proofing**: You might need context data later
3. **Consistency**: All Airflow task functions typically have it
4. **No Error**: If Airflow passes context but function doesn't accept it → Error

```python
# This would cause ERROR:
def bad_function():  # No **context
    return "hello"

# Airflow tries to call:
bad_function(task_instance=..., dag=..., execution_date=...)
# ERROR: got unexpected keyword arguments
```

## 4. When You DO Use Context

```python
def task_that_uses_context(**context):
    # Access current task instance
    ti = context['task_instance']
    
    # Access execution date
    exec_date = context['execution_date']
    
    # Access DAG information
    dag_id = context['dag'].dag_id
    
    # Pull data from other tasks
    data = ti.xcom_pull(task_ids='previous_task')
    
    print(f"Running {dag_id} on {exec_date}")
    return data
```

## 5. Alternative Approaches

### Option 1: Only Accept What You Need
```python
# Instead of **context, be specific:
def my_task(task_instance, execution_date, **kwargs):
    # Direct access, no need for context['task_instance']
    data = task_instance.xcom_pull(task_ids='other_task')
    print(f"Date: {execution_date}")
```

### Option 2: Ignore Context Completely
```python
# If you truly don't need any Airflow context:
def simple_task():
    return "I don't need any Airflow data"

# But then use it like this in DAG:
task = PythonOperator(
    task_id='simple',
    python_callable=simple_task,
    provide_context=False  # Tell Airflow not to pass context
)
```

## 6. Summary

| Aspect | Explanation |
|--------|-------------|
| **Name** | `**context` is conventional, not required |
| **Purpose** | Receives all Airflow runtime information |
| **Usage** | Use when you need task data, execution info, etc. |
| **Required?** | Usually yes, to avoid parameter errors |
| **Alternative names** | `**kwargs`, `**data`, etc. (but `**context` is standard) |

### Your Function Strategy:
```python
def discover_files_on_ftp(**context):
    # Even though you don't use context NOW,
    # it's there for:
    # 1. Airflow compatibility
    # 2. Future needs (maybe you'll want execution_date later)
    # 3. Code consistency
```

The `**context` parameter is like having a "Swiss Army knife" available - you might not need it now, but it's good to have it ready!

============================================================================================   

Each task gets its **own fresh context**.

## Example with 2 Tasks

```python
# Task 1
def task_1(**context):
    print(f"Task 1 context: {context['task_instance'].task_id}")
    # Output: "Task 1 context: discover_files"

# Task 2  
def task_2(**context):
    print(f"Task 2 context: {context['task_instance'].task_id}")
    # Output: "Task 2 context: transfer_files"
```

## What Changes in Context Between Tasks?

**Same in all tasks:**
- `execution_date` - same for whole DAG run
- `dag` - same DAG object
- `dag_run` - same DAG run

**Changes for each task:**
- `task_instance` - different for each task
- `task` - different task definition
- Any task-specific data

## Visual Example

```
DAG Run on 2025-05-26:

Task 1 runs:
context = {
    'task_instance': <discover_files task instance>,
    'execution_date': 2025-05-26,
    'dag': <your DAG>
}

Task 1 finishes ✅

Task 2 runs:  
context = {
    'task_instance': <transfer_files task instance>,  # ← CHANGED
    'execution_date': 2025-05-26,                     # ← SAME
    'dag': <your DAG>                                 # ← SAME  
}
```

## In Your Code

```python
# Task 1: discover_files
def discover_files_on_ftp(**context):
    # context['task_instance'].task_id = 'discover_files'
    files = ["file1.txt", "file2.txt"] 
    return files

# Task 2: transfer_files  
def transfer_files_via_ftp(**context):
    # context['task_instance'].task_id = 'transfer_files'  ← NEW CONTEXT!
    # Get data from Task 1
    files = context['task_instance'].xcom_pull(task_ids='discover_files')
```

**Bottom line:** Each task = fresh context with its own `task_instance`, but shared DAG info.

```
Key Point

One task = One context
Multiple functions inside = same context
Multiple tasks = different contexts

The context belongs to the task, not the individual functions inside it!
```




============================================================================================      


# Breaking Down the Line Step by Step

```python
files = context['task_instance'].xcom_pull(task_ids='discover_files')
```

## 1. What is `context['task_instance']`?

**Output:** A TaskInstance object (not a string or number!)

```python
# What you get:
task_instance_object = context['task_instance']
print(task_instance_object)
# Output: <TaskInstance: transfer_files 2025-05-26T10:00:00+00:00 [running]>

print(type(task_instance_object))
# Output: <class 'airflow.models.taskinstance.TaskInstance'>
```

**Think of it as:** An object that represents the currently running task with methods and properties.

## 2. What is `.xcom_pull()`?

**It's a method** (function) that belongs to the TaskInstance object.

```python
# TaskInstance object has many methods:
task_instance_object.xcom_pull()     # ← Method to get data
task_instance_object.xcom_push()     # ← Method to send data  
task_instance_object.task_id         # ← Property (task name)
task_instance_object.execution_date  # ← Property (when it runs)
```

## 3. What is the output of `xcom_pull(task_ids='discover_files')`?

**Output:** The data that was returned by the 'discover_files' task.


## 5. Complete Breakdown Example

```python
def transfer_files(**context):
    # Step 1: Get the TaskInstance object
    ti = context['task_instance']
    print(f"Current task: {ti.task_id}")  # Output: "transfer_files"
    
    # Step 2: Call xcom_pull method on that object
    files = ti.xcom_pull(task_ids='discover_files')
    print(f"Retrieved files: {files}")    # Output: ['/home/rocky/file1.txt', ...]
    
    # Same as your one-liner:
    files2 = context['task_instance'].xcom_pull(task_ids='discover_files')
```

## 6. What's Inside TaskInstance Object?

```python
def debug_task(**context):
    ti = context['task_instance']
    
    print(f"Task ID: {ti.task_id}")                    # 'transfer_files' 
    print(f"DAG ID: {ti.dag_id}")                      # 'ftp_file_processing_workflow'
    print(f"Execution Date: {ti.execution_date}")      # 2025-05-26 10:00:00
    print(f"State: {ti.state}")                        # 'running'
    
    # Methods you can call:
    data = ti.xcom_pull(task_ids='other_task')         # Get data
    ti.xcom_push(key='mykey', value='mydata')          # Send data
```

## 7. Visual Breakdown

```
context['task_instance']
    ↓
<TaskInstance object>
    ↓
.xcom_pull(task_ids='discover_files')
    ↓  
['/home/rocky/file1.txt', '/home/rocky/file2.txt']
    ↓
files = ['/home/rocky/file1.txt', '/home/rocky/file2.txt']
```

**Bottom Line:** You're getting an object, then calling a method on that object to retrieve data from another task!

