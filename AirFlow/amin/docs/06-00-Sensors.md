# File Sensors and @task.sensor Decorators
## Complete Guide from Basics to Expert

---

## Chapter 1: Understanding Sensors - Core Concepts

### What is a Sensor?

**A sensor is a special type of Airflow task that waits for something to happen.**

**Real-world analogy:** Think of a motion sensor light:
- It **waits** for movement
- When movement is detected, it **triggers** (turns on the light)
- If no movement, it **keeps waiting**

**In Airflow:**
- Sensors **wait** for conditions to be met
- When the condition is satisfied, the task **succeeds** and workflow continues
- If condition isn't met, sensor **keeps checking** (polling)

### What is a File Sensor?

**A File Sensor waits for files to appear in a specific location.**

**Common use cases:**
- Wait for data files to arrive from external systems
- Wait for reports to be generated
- Wait for backup files to complete
- Wait for partner companies to upload files

---

## Chapter 2: Basic File Sensor Syntax

### Traditional FileSensor (Old Way)

```python
from airflow.sensors.filesystem import FileSensor

wait_for_file = FileSensor(
    task_id='wait_for_data_file',
    filepath='/data/input/daily_report.csv',
    timeout=300,  # Wait 5 minutes maximum
    poke_interval=30  # Check every 30 seconds
)
```

### TaskFlow Sensor (New Way)

```python
from airflow.decorators import task
from airflow.sensors.base import PokeReturnValue

@task.sensor(
    poke_interval=30,    # Check every 30 seconds
    timeout=300,         # Give up after 5 minutes
    mode='poke'          # Keep checking continuously
)
def wait_for_file():
    import os
    filepath = '/data/input/daily_report.csv'
    
    if os.path.exists(filepath):
        return PokeReturnValue(is_done=True, xcom_value=filepath)
    else:
        return PokeReturnValue(is_done=False)
```

---

## Chapter 3: Sensor Parameters Explained

### Essential Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `poke_interval` | int | Seconds between checks | `poke_interval=60` |
| `timeout` | int | Maximum wait time (seconds) | `timeout=3600` |
| `mode` | string | How to wait ('poke' or 'reschedule') | `mode='reschedule'` |

### Sensor Modes

**1. Poke Mode (Default)**
```python
@task.sensor(mode='poke', poke_interval=30)
def wait_for_file_poke():
    # Keeps the worker busy, checking every 30 seconds
    return PokeReturnValue(is_done=True)
```
- **Pros:** Immediate response when condition is met
- **Cons:** Occupies worker slot while waiting

**2. Reschedule Mode**
```python
@task.sensor(mode='reschedule', poke_interval=300)
def wait_for_file_reschedule():
    # Releases worker, reschedules task every 5 minutes
    return PokeReturnValue(is_done=True)
```
- **Pros:** Frees up worker slots
- **Cons:** Slight delay in detection



# Poke vs Reschedule Mode - Key Difference

**Poke Mode:** The sensor task **stays running continuously** and occupies a worker slot the entire time. Every 30 seconds, it wakes up, checks the condition, then goes back to sleep - but the worker slot remains **blocked**. Think of it like a person sitting in a chair for hours, occasionally checking their phone, but never leaving the chair.

**Reschedule Mode:** The sensor task **runs once, checks the condition, then completely finishes** and frees up the worker slot. After 30 seconds, Airflow **creates a brand new task instance** to check again. Think of it like a person checking once, leaving the chair (freeing it for others), then coming back 30 seconds later to check again. This allows other tasks to use that worker slot while the sensor is waiting.

**Bottom line:** Both check every 30 seconds, but **poke mode blocks a worker** while **reschedule mode frees the worker** between checks.

---

## Chapter 4: Real-World File Sensor Examples

### Example 1: Simple File Existence Check

```python
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from datetime import datetime
import os

@dag(
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False
)
def file_processing_workflow():
    
    @task.sensor(poke_interval=60, timeout=1800)  # Check every minute, timeout after 30 min
    def wait_for_daily_report():
        """Wait for daily sales report to arrive"""
        filepath = "/data/reports/daily_sales.csv"
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            return PokeReturnValue(
                is_done=True, 
                xcom_value={"filepath": filepath, "size": file_size}
            )
        return PokeReturnValue(is_done=False)
    
    @task
    def process_report(file_info):
        """Process the report once it arrives"""
        print(f"Processing file: {file_info['filepath']}")
        print(f"File size: {file_info['size']} bytes")
        return "Report processed successfully"
    
    # Workflow
    file_info = wait_for_daily_report()
    process_report(file_info)

file_processing_workflow()
```

### Example 2: Advanced File Validation

```python
@task.sensor(
    poke_interval=120,    # Check every 2 minutes
    timeout=7200,         # Timeout after 2 hours
    mode='reschedule'     # Free up worker slots
)
def wait_for_valid_csv():
    """Wait for CSV file with proper content"""
    import pandas as pd
    
    filepath = "/data/input/transactions.csv"
    
    # Check if file exists
    if not os.path.exists(filepath):
        return PokeReturnValue(is_done=False)
    
    try:
        # Validate file content
        df = pd.read_csv(filepath)
        
        # Business rules validation
        if len(df) < 10:  # Must have at least 10 records
            return PokeReturnValue(is_done=False)
            
        required_columns = ['transaction_id', 'amount', 'date']
        if not all(col in df.columns for col in required_columns):
            return PokeReturnValue(is_done=False)
        
        # File is valid
        return PokeReturnValue(
            is_done=True,
            xcom_value={
                "filepath": filepath,
                "record_count": len(df),
                "validation_passed": True
            }
        )
        
    except Exception as e:
        # File exists but is invalid (corrupted, wrong format, etc.)
        return PokeReturnValue(is_done=False)
```

---

## Chapter 5: Pattern-Based File Sensors

### Wait for Files with Date Patterns

```python
@task.sensor(poke_interval=300, timeout=3600)
def wait_for_dated_file():
    """Wait for file with today's date in filename"""
    import glob
    from datetime import datetime
    
    today = datetime.now().strftime("%Y%m%d")
    pattern = f"/data/reports/sales_{today}_*.csv"
    
    matching_files = glob.glob(pattern)
    
    if matching_files:
        return PokeReturnValue(
            is_done=True,
            xcom_value={"files": matching_files, "count": len(matching_files)}
        )
    
    return PokeReturnValue(is_done=False)
```

### Wait for Multiple Files

```python
@task.sensor(poke_interval=180, timeout=1800)
def wait_for_batch_files():
    """Wait for all required files in a batch"""
    required_files = [
        "/data/input/customers.csv",
        "/data/input/orders.csv", 
        "/data/input/products.csv"
    ]
    
    existing_files = []
    missing_files = []
    
    for filepath in required_files:
        if os.path.exists(filepath):
            existing_files.append(filepath)
        else:
            missing_files.append(filepath)
    
    if not missing_files:  # All files exist
        return PokeReturnValue(
            is_done=True,
            xcom_value={"all_files": existing_files}
        )
    
    # Still waiting for some files
    print(f"Still waiting for: {missing_files}")
    return PokeReturnValue(is_done=False)
```

---

## Chapter 6: Expert Patterns and Best Practices

### 1. Sensor with Timeout Handling

```python
@dag(start_date=datetime(2025, 1, 1), schedule_interval='@daily')
def robust_file_processing():
    
    @task.sensor(
        poke_interval=60,
        timeout=3600,
        mode='reschedule'
    )
    def wait_for_file_with_fallback():
        """Sensor with detailed logging and fallback logic"""
        import logging
        
        filepath = "/data/input/{{ ds }}_data.csv"  # Uses Airflow templating
        
        if os.path.exists(filepath):
            logging.info(f"✅ File found: {filepath}")
            return PokeReturnValue(is_done=True, xcom_value=filepath)
        else:
            logging.warning(f"⏳ Still waiting for: {filepath}")
            return PokeReturnValue(is_done=False)
    
    @task
    def handle_timeout():
        """Handle case when file never arrives"""
        print("File didn't arrive within timeout period")
        print("Sending alert to data team...")
        return "timeout_handled"
    
    @task
    def process_file(filepath):
        """Process the file when it arrives"""
        print(f"Processing file: {filepath}")
        return "file_processed"
    
    # Workflow with timeout handling
    try:
        filepath = wait_for_file_with_fallback()
        result = process_file(filepath)
    except Exception:
        result = handle_timeout()

robust_file_processing()
```

### 2. Dynamic File Sensors

```python
@task.sensor(poke_interval=30, timeout=900)
def wait_for_partner_files():
    """Wait for files from multiple partners"""
    import json
    
    # Configuration could come from Airflow Variables
    partners = ["partner_a", "partner_b", "partner_c"]
    base_path = "/data/partners"
    
    ready_partners = []
    pending_partners = []
    
    for partner in partners:
        partner_file = f"{base_path}/{partner}/daily_feed.json"
        
        if os.path.exists(partner_file):
            # Validate JSON file
            try:
                with open(partner_file, 'r') as f:
                    data = json.load(f)
                    if data.get('status') == 'complete':
                        ready_partners.append(partner)
                    else:
                        pending_partners.append(partner)
            except:
                pending_partners.append(partner)
        else:
            pending_partners.append(partner)
    
    # Check if we have minimum required partners
    min_required = 2  # Need at least 2 out of 3 partners
    
    if len(ready_partners) >= min_required:
        return PokeReturnValue(
            is_done=True,
            xcom_value={
                "ready_partners": ready_partners,
                "pending_partners": pending_partners,
                "total_ready": len(ready_partners)
            }
        )
    
    return PokeReturnValue(is_done=False)
```

### 3. File Sensor with Size and Age Validation

```python
@task.sensor(poke_interval=120, timeout=7200, mode='reschedule')
def wait_for_stable_file():
    """Wait for file that's not being written to anymore"""
    import time
    
    filepath = "/data/large_export.csv"
    min_size_mb = 10  # Minimum 10MB
    stability_seconds = 60  # File size unchanged for 60 seconds
    
    if not os.path.exists(filepath):
        return PokeReturnValue(is_done=False)
    
    # Check file size
    file_size = os.path.getsize(filepath)
    size_mb = file_size / (1024 * 1024)
    
    if size_mb < min_size_mb:
        print(f"File too small: {size_mb:.2f}MB (min: {min_size_mb}MB)")
        return PokeReturnValue(is_done=False)
    
    # Check if file is stable (not being written to)
    modification_time = os.path.getmtime(filepath)
    current_time = time.time()
    
    if (current_time - modification_time) < stability_seconds:
        print("File still being modified, waiting for stability...")
        return PokeReturnValue(is_done=False)
    
    return PokeReturnValue(
        is_done=True,
        xcom_value={
            "filepath": filepath,
            "size_mb": round(size_mb, 2),
            "last_modified": modification_time
        }
    )
```

---

## Chapter 7: Troubleshooting and Monitoring

### Common Issues and Solutions

**1. Sensor Never Completes**
```python
# Add debugging
@task.sensor(poke_interval=60, timeout=600)
def debug_sensor():
    import logging
    
    filepath = "/data/test.csv"
    logging.info(f"Checking for file: {filepath}")
    logging.info(f"Directory exists: {os.path.exists(os.path.dirname(filepath))}")
    logging.info(f"Directory contents: {os.listdir(os.path.dirname(filepath))}")
    
    return PokeReturnValue(is_done=os.path.exists(filepath))
```

**2. Sensor Times Out Too Quickly**
```python
# Increase timeout for large files
@task.sensor(
    poke_interval=300,   # Check every 5 minutes
    timeout=14400        # Wait up to 4 hours
)
def patient_sensor():
    # Implementation here
    pass
```

**3. Performance Issues**
```python
# Use reschedule mode for long waits
@task.sensor(
    mode='reschedule',   # Frees up workers
    poke_interval=600    # Check every 10 minutes
)
def efficient_sensor():
    # Implementation here
    pass
```

### Monitoring Sensor Performance

```python
@task.sensor(poke_interval=60, timeout=1800)
def monitored_sensor():
    """Sensor with built-in monitoring"""
    import time
    import logging
    
    start_time = time.time()
    filepath = "/data/important_file.csv"
    
    if os.path.exists(filepath):
        wait_time = time.time() - start_time
        logging.info(f"✅ File arrived after {wait_time:.1f} seconds")
        
        return PokeReturnValue(
            is_done=True,
            xcom_value={
                "filepath": filepath,
                "wait_time_seconds": wait_time
            }
        )
    else:
        logging.info(f"⏳ Still waiting... ({time.time() - start_time:.1f}s elapsed)")
        return PokeReturnValue(is_done=False)
```

---

## Chapter 8: Best Practices Summary

### ✅ Do's

1. **Use appropriate timeouts** - Don't wait forever
2. **Choose the right mode** - 'reschedule' for long waits
3. **Add logging** - Help with debugging
4. **Validate file content** - Don't just check existence
5. **Return useful XCom data** - Pass file info to next tasks
6. **Handle edge cases** - Empty files, corrupted files, etc.

### ❌ Don'ts

1. **Don't use very short poke_intervals** - Avoid hammering the filesystem
2. **Don't ignore timeouts** - Always have a backup plan
3. **Don't assume file format** - Validate before processing
4. **Don't use poke mode for very long waits** - Use reschedule instead

### 🎯 Quick Reference Template

```python
@task.sensor(
    poke_interval=60,        # Adjust based on urgency
    timeout=3600,            # Set reasonable timeout
    mode='reschedule'        # Use for long waits
)
def my_file_sensor():
    """Template for file sensor"""
    
    # 1. Define file path
    filepath = "/path/to/your/file.csv"
    
    # 2. Check if file exists
    if not os.path.exists(filepath):
        return PokeReturnValue(is_done=False)
    
    # 3. Optional: Validate file
    # Add your validation logic here
    
    # 4. Return success with data
    return PokeReturnValue(
        is_done=True,
        xcom_value={"filepath": filepath}
    )
```

---

**This completes your comprehensive guide to File Sensors in Airflow. Start with the basic examples and gradually implement the advanced patterns as your needs grow more complex.**
