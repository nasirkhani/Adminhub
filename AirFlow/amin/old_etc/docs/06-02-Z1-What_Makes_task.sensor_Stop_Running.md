# What Makes @task.sensor Stop Running

## Normal Stopping Conditions

### 1. Success Condition Met
```python
@task.sensor(poke_interval=60, timeout=1800)
def my_sensor():
    if condition_met:
        return PokeReturnValue(is_done=True)  # ✅ STOPS HERE - Success
    else:
        return PokeReturnValue(is_done=False)  # ❌ CONTINUES - Keep checking
```

### 2. Timeout Reached
```python
@task.sensor(timeout=300)  # Stops after 5 minutes
def timeout_sensor():
    return PokeReturnValue(is_done=False)  # Eventually times out
```

### 3. Unhandled Exceptions
```python
@task.sensor(poke_interval=60, timeout=1800)
def error_sensor():
    if some_condition:
        raise Exception("Something went wrong!")  # ✅ STOPS - Task fails
    return PokeReturnValue(is_done=False)
```

## Manual Stopping Methods

### 4. Manual Task Termination (Web UI)
- **Web UI:** Click task → "Mark Failed" 
- **Web UI:** Click task → "Clear" 
- **CLI:** `airflow tasks clear <dag_id> --task_regex <task_id>`

### 5. DAG Run Termination
- **Web UI:** Stop entire DAG run
- **CLI:** Kill DAG run

### 6. System-Level Interrupts
```python
@task.sensor(poke_interval=60, timeout=1800)
def interruptible_sensor():
    import signal
    
    def signal_handler(signum, frame):
        print("Received interrupt signal")
        raise KeyboardInterrupt("Sensor interrupted")
    
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Normal sensor logic
    return PokeReturnValue(is_done=check_condition())
```

## Important: What DOESN'T Stop the Sensor

### ❌ Regular `return` Statements
```python
@task.sensor(poke_interval=60, timeout=1800)
def wrong_sensor():
    if condition_met:
        return True  # ⚠️ This works but NO data passing
    else:
        return False  # ⚠️ This continues checking
    
    # This code never runs (unreachable)
    print("This never executes")
```

### ❌ `break` Statements (Not Applicable)
```python
@task.sensor(poke_interval=60, timeout=1800)
def no_break_sensor():
    while True:  # ❌ DON'T DO THIS - Airflow handles the loop
        if condition_met:
            break  # ❌ This doesn't work as expected
        time.sleep(60)  # ❌ Don't manually sleep
```

## Complete Examples of Stopping Scenarios

### Example 1: Graceful Success
```python
@task.sensor(poke_interval=30, timeout=600)
def file_ready_sensor():
    """Stops when file is ready"""
    filepath = "/data/important_file.csv"
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        print("✅ File is ready!")
        return PokeReturnValue(is_done=True, xcom_value=filepath)  # STOPS
    else:
        print("⏳ File not ready yet...")
        return PokeReturnValue(is_done=False)  # CONTINUES
```

### Example 2: Error-Based Stopping
```python
@task.sensor(poke_interval=60, timeout=1800)
def connection_sensor():
    """Stops on connection errors"""
    try:
        response = requests.get("http://api.example.com/health", timeout=10)
        if response.status_code == 200:
            return PokeReturnValue(is_done=True)  # STOPS - Success
        else:
            return PokeReturnValue(is_done=False)  # CONTINUES
    
    except requests.exceptions.ConnectionError:
        raise Exception("API is completely down!")  # STOPS - Task fails
```

### Example 3: Conditional Stopping
```python
@task.sensor(poke_interval=120, timeout=3600, soft_fail=True)
def business_logic_sensor(**context):
    """Stops based on business rules"""
    current_hour = datetime.now().hour
    
    # Stop checking outside business hours
    if current_hour < 8 or current_hour > 18:
        print("Outside business hours, stopping sensor")
        return PokeReturnValue(is_done=True, xcom_value="outside_hours")  # STOPS
    
    # Normal condition check
    if check_business_condition():
        return PokeReturnValue(is_done=True, xcom_value="condition_met")  # STOPS
    else:
        return PokeReturnValue(is_done=False)  # CONTINUES
```

### Example 4: Max Attempts Pattern
```python
@task.sensor(poke_interval=60, timeout=1800)
def limited_attempts_sensor(**context):
    """Stop after certain number of failed attempts"""
    from airflow.models import Variable
    
    attempt_count = int(Variable.get("sensor_attempts", default_var=0))
    max_attempts = 10
    
    if attempt_count >= max_attempts:
        raise Exception(f"Max attempts ({max_attempts}) reached!")  # STOPS - Fails
    
    Variable.set("sensor_attempts", attempt_count + 1)
    
    if check_condition():
        Variable.set("sensor_attempts", 0)  # Reset counter
        return PokeReturnValue(is_done=True)  # STOPS - Success
    else:
        return PokeReturnValue(is_done=False)  # CONTINUES
```

## Summary of Stopping Conditions

| Condition | Result | Task Status |
|-----------|--------|-------------|
| `PokeReturnValue(is_done=True)` | ✅ Stops | SUCCESS |
| `return True` | ✅ Stops | SUCCESS |
| `raise Exception()` | ✅ Stops | FAILED |
| Timeout reached | ✅ Stops | FAILED (or SKIPPED with soft_fail) |
| Manual termination | ✅ Stops | User-defined |
| System interrupt (SIGTERM) | ✅ Stops | FAILED |
| `PokeReturnValue(is_done=False)` | ❌ Continues | RUNNING |
| `return False` | ❌ Continues | RUNNING |

## Key Points

1. **The function executes once per poke_interval** - Airflow handles the looping
2. **Only `is_done=True` or exceptions stop the sensor** normally
3. **Manual intervention** can always stop any running task
4. **Timeout is your safety net** - always set reasonable timeouts
5. **Use `soft_fail=True`** if timeout should be treated as success

**Remember:** Your sensor function is called repeatedly by Airflow's scheduling mechanism, not in a continuous loop within your function!



=============================================================


# soft_fail=True Summary

## Core Concept
**soft_fail=True** changes sensor timeout behavior:
- **Normal:** Timeout → Task FAILED → Workflow STOPS
- **soft_fail=True:** Timeout → Task SKIPPED → Workflow CONTINUES

## Simple Example
```python
@task.sensor(timeout=300, soft_fail=True)  # Skip if timeout
def wait_for_optional_file():
    return PokeReturnValue(is_done=os.path.exists("/optional/data.csv"))

@task
def process_data():
    return "Processing continues even if file missing"
```

## When to Use
**✅ Use soft_fail=True for:**
- Optional files that don't always arrive
- External systems that might be down
- "Nice-to-have" data that enriches but isn't essential

**❌ Don't use for:**
- Critical files required for processing
- Data where integrity depends on the file

## Handling Skipped Results
```python
@task
def handle_result(sensor_data):
    if sensor_data is None:  # Sensor was skipped
        return "Process without optional data"
    else:  # Sensor succeeded
        return f"Process with data: {sensor_data}"
```

**Bottom Line:** Use `soft_fail=True` to make workflows resilient to missing optional data - they'll skip the sensor and continue processing instead of failing completely.
