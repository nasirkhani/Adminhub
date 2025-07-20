# PokeReturnValue Explained - Simple Guide

## What is PokeReturnValue?

**PokeReturnValue is a special object that sensors return to tell Airflow two things:**
1. **Is the condition met?** (True/False)
2. **What data should I pass to the next task?** (optional)

**Think of it like a report card:**
- **Grade:** Pass or Fail (is_done)
- **Comments:** Additional information (xcom_value)

## Why Do We Need It?

### Before PokeReturnValue (Old Way)
```python
@task.sensor(poke_interval=60)
def old_sensor():
    import os
    if os.path.exists("/data/file.csv"):
        return True   # ✅ File exists, but no info about the file
    else:
        return False  # ❌ File doesn't exist
```

**Problem:** You can only say "yes" or "no", but can't pass file information to the next task.

### With PokeReturnValue (New Way)
```python
@task.sensor(poke_interval=60)
def new_sensor():
    import os
    filepath = "/data/file.csv"
    
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        return PokeReturnValue(
            is_done=True,                           # ✅ Condition met
            xcom_value={"file": filepath, "size": file_size}  # 📦 Pass data to next task
        )
    else:
        return PokeReturnValue(is_done=False)       # ❌ Keep waiting
```

**Benefit:** You can pass useful information to the next task!

## PokeReturnValue Syntax

### Basic Structure
```python
from airflow.sensors.base import PokeReturnValue

PokeReturnValue(
    is_done=True/False,     # Required: Is condition met?
    xcom_value=data         # Optional: Data to pass to next task
)
```

### Simple Examples

**1. Just True/False (no data)**
```python
@task.sensor(poke_interval=30)
def simple_sensor():
    condition_met = check_something()
    
    return PokeReturnValue(is_done=condition_met)
```

**2. Pass a single value**
```python
@task.sensor(poke_interval=60)
def file_size_sensor():
    filepath = "/data/report.csv"
    
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        return PokeReturnValue(
            is_done=True,
            xcom_value=file_size  # Pass file size to next task
        )
    
    return PokeReturnValue(is_done=False)
```

**3. Pass multiple values (dictionary)**
```python
@task.sensor(poke_interval=120)
def detailed_file_sensor():
    filepath = "/data/sales.csv"
    
    if os.path.exists(filepath):
        import os
        file_stats = {
            "filepath": filepath,
            "size": os.path.getsize(filepath),
            "modified": os.path.getmtime(filepath),
            "readable": os.access(filepath, os.R_OK)
        }
        
        return PokeReturnValue(
            is_done=True,
            xcom_value=file_stats  # Pass dictionary to next task
        )
    
    return PokeReturnValue(is_done=False)
```

## Complete Example with Data Passing

```python
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from datetime import datetime
import os

@dag(start_date=datetime(2025, 1, 1), schedule_interval=None)
def sensor_data_passing():
    
    @task.sensor(poke_interval=30, timeout=300)
    def wait_for_csv_file():
        """Wait for CSV file and return file information"""
        filepath = "/tmp/test_data.csv"
        
        if os.path.exists(filepath):
            # File exists, get information about it
            file_info = {
                "path": filepath,
                "size_bytes": os.path.getsize(filepath),
                "size_mb": round(os.path.getsize(filepath) / 1024 / 1024, 2)
            }
            
            return PokeReturnValue(
                is_done=True,           # ✅ Condition met
                xcom_value=file_info    # 📦 Pass file info to next task
            )
        else:
            # File doesn't exist yet
            print(f"Still waiting for {filepath}...")
            return PokeReturnValue(is_done=False)  # ❌ Keep waiting
    
    @task
    def process_file(file_data):
        """Process the file using information from sensor"""
        print(f"📁 Processing file: {file_data['path']}")
        print(f"📊 File size: {file_data['size_mb']} MB")
        
        if file_data['size_mb'] > 10:
            return "Large file processed"
        else:
            return "Small file processed"
    
    # Workflow: Sensor passes data to processing task
    file_info = wait_for_csv_file()
    result = process_file(file_info)

sensor_data_passing()
```

## What If You Don't Use PokeReturnValue?

**You can still return True/False directly:**
```python
@task.sensor(poke_interval=60)
def simple_bool_sensor():
    if condition_met:
        return True   # Works, but no data passing
    else:
        return False
```

**But you lose the ability to pass data to the next task!**

## PokeReturnValue Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `is_done` | bool | ✅ Yes | True = condition met, False = keep waiting |
| `xcom_value` | any | ❌ No | Data to pass to downstream tasks |

## Common Patterns

**1. File Existence Only**
```python
return PokeReturnValue(is_done=os.path.exists(filepath))
```

**2. File Existence + Path**
```python
if os.path.exists(filepath):
    return PokeReturnValue(is_done=True, xcom_value=filepath)
else:
    return PokeReturnValue(is_done=False)
```

**3. Complex Validation + Data**
```python
if file_is_valid(filepath):
    return PokeReturnValue(
        is_done=True, 
        xcom_value={"file": filepath, "records": count_records(filepath)}
    )
else:
    return PokeReturnValue(is_done=False)
```

## Key Takeaway

**PokeReturnValue = Sensor's way to say:**
- ✅ **"I'm done!"** (`is_done=True`) + **"Here's useful data"** (`xcom_value=data`)
- ❌ **"Keep waiting"** (`is_done=False`)

**Without PokeReturnValue:** Only True/False, no data passing
**With PokeReturnValue:** True/False + data passing to next tasks

It's like upgrading from a simple yes/no answer to a detailed report!
