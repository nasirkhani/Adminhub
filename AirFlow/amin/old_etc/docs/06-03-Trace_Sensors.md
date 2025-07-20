# How Sensors Keep Running - Step by Step Trace

## Simple Sensor Example

Let me show you exactly how a sensor works with a simple file sensor:

```python
from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from datetime import datetime
import os

@dag(start_date=datetime(2025, 1, 1), schedule_interval=None)
def sensor_trace_example():
    
    @task.sensor(
        poke_interval=10,    # Check every 10 seconds
        timeout=60,          # Give up after 60 seconds
        mode='poke'
    )
    def wait_for_test_file():
        """This function gets called repeatedly every 10 seconds"""
        
        filepath = "/tmp/test_file.txt"
        print(f"🔍 CHECKING: Does {filepath} exist?")
        
        if os.path.exists(filepath):
            print(f"✅ SUCCESS: File found!")
            return PokeReturnValue(is_done=True, xcom_value=filepath)
        else:
            print(f"❌ NOT FOUND: File doesn't exist yet, will check again in 10 seconds")
            return PokeReturnValue(is_done=False)
    
    @task
    def process_file(filepath):
        print(f"📁 Processing file: {filepath}")
        return "File processed!"
    
    # Workflow
    file_path = wait_for_test_file()
    result = process_file(file_path)

sensor_trace_example()
```

## Step-by-Step Execution Trace

**Let's trace what happens when you trigger this DAG:**

### Time: 0:00 - DAG Starts
```
🚀 DAG triggered
📋 Scheduler: "Starting wait_for_test_file task"
🔄 Airflow: "This is a sensor, I'll keep calling the function until it returns True"
```

### Time: 0:00 - First Check
```
🔍 CHECKING: Does /tmp/test_file.txt exist?
❌ NOT FOUND: File doesn't exist yet, will check again in 10 seconds

📋 Airflow Internal Logic:
   - Function returned: PokeReturnValue(is_done=False)
   - is_done = False means "keep waiting"
   - Sleep for 10 seconds (poke_interval)
   - Don't move to next task yet
```

### Time: 0:10 - Second Check
```
🔍 CHECKING: Does /tmp/test_file.txt exist?
❌ NOT FOUND: File doesn't exist yet, will check again in 10 seconds

📋 Airflow Internal Logic:
   - Function returned: PokeReturnValue(is_done=False)
   - Still waiting...
   - Sleep for another 10 seconds
```

### Time: 0:20 - Third Check
```
🔍 CHECKING: Does /tmp/test_file.txt exist?
❌ NOT FOUND: File doesn't exist yet, will check again in 10 seconds

📋 Airflow Internal Logic:
   - Function returned: PokeReturnValue(is_done=False)
   - Still waiting...
   - Sleep for another 10 seconds
```

### Time: 0:25 - Someone Creates the File
```
💾 External process: echo "Hello World" > /tmp/test_file.txt
📁 File now exists on filesystem
```

### Time: 0:30 - Fourth Check
```
🔍 CHECKING: Does /tmp/test_file.txt exist?
✅ SUCCESS: File found!

📋 Airflow Internal Logic:
   - Function returned: PokeReturnValue(is_done=True, xcom_value="/tmp/test_file.txt")
   - is_done = True means "condition met!"
   - Mark sensor task as SUCCESS
   - Move to next task: process_file
   - Pass xcom_value to next task
```

### Time: 0:30 - Next Task Runs
```
📁 Processing file: /tmp/test_file.txt
✅ Task completed successfully
🎉 DAG finished!
```

## What Airflow Does Behind the Scenes

**Airflow's sensor logic (simplified):**

```python
# This is what Airflow does internally (simplified)
def run_sensor_task(sensor_function, poke_interval, timeout):
    start_time = time.time()
    
    while True:
        # Call your sensor function
        result = sensor_function()
        
        if result.is_done == True:
            print("✅ Sensor condition met!")
            return result.xcom_value  # Pass data to next task
        
        # Check if we've exceeded timeout
        if time.time() - start_time > timeout:
            print("⏰ Sensor timed out!")
            raise Exception("Sensor timeout")
        
        print(f"😴 Sleeping for {poke_interval} seconds...")
        time.sleep(poke_interval)
        # Loop back and check again
```

## Visual Timeline

```
Timeline of sensor execution:

0:00  🔍 Check #1 → ❌ Not found → 😴 Sleep 10s
0:10  🔍 Check #2 → ❌ Not found → 😴 Sleep 10s  
0:20  🔍 Check #3 → ❌ Not found → 😴 Sleep 10s
0:25  💾 [External: File created]
0:30  🔍 Check #4 → ✅ Found! → 🚀 Continue to next task
0:30  📁 Process file → ✅ Done!
```

## Test This Yourself

**1. Create and run the DAG**
**2. Watch the logs in real-time:**
```bash
# In one terminal, trigger the DAG
# In another terminal, watch logs
tail -f ~/airflow/logs/dag_id/task_id/*/attempt=1.log
```

**3. Create the file while sensor is running:**
```bash
# Wait a few seconds after triggering, then run:
echo "Hello World" > /tmp/test_file.txt
```

**4. Watch the sensor immediately detect the file and move to the next task!**

## Key Points

1. **Your sensor function gets called repeatedly** every `poke_interval` seconds
2. **Each time it returns `is_done=False`**, Airflow sleeps and calls it again
3. **When it returns `is_done=True`**, Airflow stops the loop and continues the workflow
4. **The sensor task stays "running"** until the condition is met or timeout occurs
5. **Your function doesn't need to handle the looping** - Airflow does that for you

**The magic:** You just write the "check once" logic, Airflow handles the "keep checking" part!
