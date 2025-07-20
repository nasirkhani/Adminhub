# Essential TaskFlow Sensor Tips Summary

## @task.sensor Basics
```python
@task.sensor(poke_interval=60, timeout=3600, mode='reschedule')
def my_sensor():
    if condition_met:
        return PokeReturnValue(is_done=True, xcom_value=data)
    else:
        return PokeReturnValue(is_done=False)
```

## PokeReturnValue - Key Points
- **Purpose:** Tell Airflow if condition is met + pass data to next task
- **Syntax:** `PokeReturnValue(is_done=True/False, xcom_value=optional_data)`
- **Without it:** Can only return True/False, no data passing
- **With it:** Can pass file paths, sizes, or any data to downstream tasks

## Worker Slots - Critical Understanding
**Worker Slots = Limited parking spaces for tasks**

### Poke Mode Problems:
```python
mode='poke'  # ❌ Occupies worker slot while waiting
# Like person sitting in chair for hours doing nothing
# Blocks other tasks from running
```

### Reschedule Mode Solution:
```python
mode='reschedule'  # ✅ Frees worker slot between checks  
# Like person leaving chair, coming back later
# Other tasks can use the slot
```

## Quick Decision Rules
- **Use `mode='poke'`:** Quick waits (<5 minutes), immediate response needed
- **Use `mode='reschedule'`:** Long waits (>5 minutes), limited worker slots
- **Check worker slots:** `airflow config get-value core parallelism`
- **Data passing:** Always use `PokeReturnValue` if you need file info in next task

## Common Pattern
```python
@task.sensor(mode='reschedule', poke_interval=300, timeout=3600)
def wait_for_file():
    if os.path.exists(filepath):
        return PokeReturnValue(is_done=True, xcom_value={"path": filepath, "size": os.path.getsize(filepath)})
    return PokeReturnValue(is_done=False)
```

**Bottom Line:** Use reschedule mode for most production sensors to avoid blocking workers!


# Additional TaskFlow Sensor Tips Not Covered

## 1. Soft Fail Parameter
```python
@task.sensor(poke_interval=60, timeout=300, soft_fail=True)
def optional_file_sensor():
    """If sensor times out, mark as SKIPPED instead of FAILED"""
    # This allows downstream tasks to continue even if file never arrives
    return PokeReturnValue(is_done=os.path.exists("/optional/file.csv"))
```

## 2. Dynamic Parameters with Templating
```python
@task.sensor(poke_interval=60, timeout=1800)
def templated_sensor(**context):
    """Use Airflow macros and variables"""
    # Access execution date, variables, etc.
    date_str = context['ds']  # YYYY-MM-DD format
    filepath = f"/data/report_{date_str}.csv"
    
    return PokeReturnValue(is_done=os.path.exists(filepath), xcom_value=filepath)
```

## 3. Multiple Condition Checking
```python
@task.sensor(poke_interval=120, timeout=3600)
def multi_condition_sensor():
    """Check multiple conditions before succeeding"""
    conditions = {
        'file_exists': os.path.exists('/data/file.csv'),
        'file_size_ok': os.path.getsize('/data/file.csv') > 1000 if os.path.exists('/data/file.csv') else False,
        'lock_file_gone': not os.path.exists('/data/file.csv.lock')
    }
    
    all_conditions_met = all(conditions.values())
    
    if all_conditions_met:
        return PokeReturnValue(is_done=True, xcom_value=conditions)
    else:
        print(f"Waiting for conditions: {conditions}")
        return PokeReturnValue(is_done=False)
```

## 4. Sensor with Custom Queues
```python
@task.sensor(poke_interval=60, timeout=1800, queue='sensor_queue')
def dedicated_queue_sensor():
    """Run sensor on dedicated worker queue"""
    # Useful for isolating long-running sensors
    return PokeReturnValue(is_done=check_condition())
```

## 5. Exponential Backoff Pattern
```python
@task.sensor(poke_interval=30, timeout=1800)
def smart_backoff_sensor(**context):
    """Increase check interval over time"""
    task_instance = context['task_instance']
    try_number = task_instance.try_number
    
    # Increase interval: 30s, 60s, 120s, 240s (max 5 min)
    dynamic_interval = min(30 * (2 ** (try_number - 1)), 300)
    
    print(f"Check #{try_number}, next check in {dynamic_interval}s")
    
    # You'd need to implement custom logic to actually use dynamic_interval
    return PokeReturnValue(is_done=check_condition())
```

## 6. Sensor State Monitoring
```python
@task.sensor(poke_interval=60, timeout=3600)
def monitored_sensor(**context):
    """Add custom metrics and monitoring"""
    import time
    
    start_time = time.time()
    
    # Custom logging/metrics
    from airflow.models import Variable
    check_count = Variable.get("sensor_check_count", default_var=0, deserialize_json=False)
    Variable.set("sensor_check_count", int(check_count) + 1)
    
    if check_condition():
        elapsed = time.time() - start_time
        print(f"✅ Condition met after {elapsed:.1f}s, total checks: {int(check_count) + 1}")
        return PokeReturnValue(is_done=True, xcom_value={"wait_time": elapsed})
    
    return PokeReturnValue(is_done=False)
```

## 7. Sensor with Cleanup Logic
```python
@task.sensor(poke_interval=60, timeout=1800)
def sensor_with_cleanup(**context):
    """Perform cleanup actions on timeout or success"""
    try:
        if check_condition():
            return PokeReturnValue(is_done=True)
        return PokeReturnValue(is_done=False)
    
    except Exception as e:
        # Cleanup on error
        cleanup_temp_files()
        print(f"Sensor failed with cleanup: {e}")
        return PokeReturnValue(is_done=False)
```

## 8. Cross-Sensor Communication
```python
@task.sensor(poke_interval=30, timeout=900)
def coordinated_sensor_1(**context):
    """Sensor that coordinates with other sensors"""
    from airflow.models import Variable
    
    # Check own condition
    my_condition = check_my_condition()
    
    # Check if other sensor is ready
    other_sensor_ready = Variable.get("sensor_2_ready", default_var="false") == "true"
    
    if my_condition:
        Variable.set("sensor_1_ready", "true")
        
        if other_sensor_ready:
            # Both sensors ready
            return PokeReturnValue(is_done=True, xcom_value="both_ready")
    
    return PokeReturnValue(is_done=False)
```

## 9. Conditional Sensor Success
```python
@task.sensor(poke_interval=120, timeout=1800)
def business_hours_sensor(**context):
    """Only succeed during business hours"""
    from datetime import datetime
    
    file_exists = os.path.exists('/data/file.csv')
    current_hour = datetime.now().hour
    is_business_hours = 9 <= current_hour <= 17
    
    if file_exists and is_business_hours:
        return PokeReturnValue(is_done=True, xcom_value="processed_during_business_hours")
    elif file_exists and not is_business_hours:
        print("File exists but outside business hours, waiting...")
        return PokeReturnValue(is_done=False)
    else:
        print("File not found")
        return PokeReturnValue(is_done=False)
```

## 10. Testing Sensor Functions
```python
# You can test sensor functions independently!
def test_my_sensor():
    """Unit test for sensor logic"""
    # Mock file existence
    with patch('os.path.exists', return_value=True):
        result = my_sensor_function()
        assert result.is_done == True
        assert 'filepath' in result.xcom_value
```

## Key Advanced Tips:

1. **Use `soft_fail=True`** for optional sensors that shouldn't block the workflow
2. **Monitor sensor performance** with custom metrics and logging
3. **Use dedicated queues** for long-running sensors to avoid blocking other tasks
4. **Test sensor functions** independently of Airflow context
5. **Implement cleanup logic** for failed or timed-out sensors
6. **Consider business logic** in sensor conditions (time of day, etc.)
7. **Use Variables** for sensor coordination and state sharing
8. **Add detailed logging** to help debug sensor behavior in production

These patterns make sensors more robust and production-ready!
