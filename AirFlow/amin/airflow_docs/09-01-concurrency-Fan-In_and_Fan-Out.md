# Fan-In and Fan-Out Patterns in Apache Airflow

## Introduction: What Are These Patterns?

Think of fan-out and fan-in patterns like a river system:
- **Fan-Out**: One river splitting into multiple streams
- **Fan-In**: Multiple streams converging into one river

In Airflow, these patterns control how tasks branch out and merge back together, directly impacting parallel execution and concurrency.

## 1. Fan-Out Pattern (One-to-Many)

### **Definition**
Fan-out occurs when one task triggers multiple downstream tasks that can run in parallel.

### **Visual Representation**
```
                  ┌─→ Task B
                  │
    Task A ───────┼─→ Task C
                  │
                  └─→ Task D
```

### **How It Works**
- Task A completes successfully
- Tasks B, C, and D all become eligible to run
- With sufficient concurrency, B, C, and D run **simultaneously**
- Execution time = max(B, C, D) instead of sum(B, C, D)

### **Syntax Examples**

**Method 1: Using >> operator with list**
```python
@dag(...)
def fanout_example():
    @task
    def prepare_data():
        return "data ready"
    
    @task
    def process_type_a(data):
        return f"Processed A: {data}"
    
    @task
    def process_type_b(data):
        return f"Processed B: {data}"
    
    @task
    def process_type_c(data):
        return f"Processed C: {data}"
    
    # Fan-out pattern
    prep = prepare_data()
    
    # These three will run in parallel
    a = process_type_a(prep)
    b = process_type_b(prep)
    c = process_type_c(prep)
    
    # Explicit dependency syntax
    prep >> [a, b, c]
```

**Method 2: Dynamic fan-out with loop**
```python
@dag(...)
def dynamic_fanout():
    @task
    def get_items():
        return ['vm1', 'vm2', 'vm3', 'vm4', 'vm5']
    
    @task
    def process_item(item):
        # This will create 5 parallel tasks
        return f"Processed {item}"
    
    items = get_items()
    
    # Dynamic fan-out - creates parallel tasks
    results = []
    for item in items:
        results.append(process_item(item))
```

### **Real-World Example: Multi-VM Health Check**
```python
@dag(...)
def vm_health_check():
    @task
    def identify_vms():
        """Get list of VMs to check"""
        return {
            'web_servers': ['web1', 'web2', 'web3'],
            'db_servers': ['db1', 'db2'],
            'app_servers': ['app1', 'app2', 'app3']
        }
    
    @task
    def check_cpu(server_name):
        """Check CPU usage - runs in parallel for each server"""
        # SSH to server and check CPU
        return f"{server_name}: CPU 45%"
    
    @task
    def check_memory(server_name):
        """Check memory - runs in parallel"""
        return f"{server_name}: Memory 60%"
    
    @task
    def check_disk(server_name):
        """Check disk - runs in parallel"""
        return f"{server_name}: Disk 30%"
    
    vms = identify_vms()
    
    # Fan-out: Each VM gets 3 parallel checks
    for category, servers in vms.items():
        for server in servers:
            cpu = check_cpu(server)
            mem = check_memory(server)
            disk = check_disk(server)
            
            # All three checks run simultaneously for each server
```

## 2. Fan-In Pattern (Many-to-One)

### **Definition**
Fan-in occurs when multiple tasks must complete before a single downstream task can run.

### **Visual Representation**
```
    Task B ───┐
              │
    Task C ───┼─→ Task E
              │
    Task D ───┘
```

### **How It Works**
- Tasks B, C, and D can run in parallel
- Task E waits for ALL upstream tasks to complete
- E only starts when B AND C AND D are successful
- Natural synchronization point in your workflow

### **Syntax Examples**

**Method 1: Multiple inputs to a task**
```python
@dag(...)
def fanin_example():
    @task
    def extract_from_api():
        return {"source": "api", "records": 100}
    
    @task
    def extract_from_database():
        return {"source": "db", "records": 200}
    
    @task
    def extract_from_file():
        return {"source": "file", "records": 150}
    
    @task
    def combine_data(api_data, db_data, file_data):
        """This task waits for all three extracts"""
        total = api_data['records'] + db_data['records'] + file_data['records']
        return f"Combined {total} records from 3 sources"
    
    # Fan-in pattern - combine waits for all
    api = extract_from_api()
    db = extract_from_database()
    file = extract_from_file()
    
    result = combine_data(api, db, file)
```

**Method 2: Using list syntax**
```python
@dag(...)
def fanin_with_lists():
    @task
    def start():
        return "go"
    
    @task
    def parallel_task_1():
        return 1
    
    @task
    def parallel_task_2():
        return 2
    
    @task
    def parallel_task_3():
        return 3
    
    @task
    def aggregate():
        return "all done"
    
    s = start()
    p1 = parallel_task_1()
    p2 = parallel_task_2()
    p3 = parallel_task_3()
    agg = aggregate()
    
    # Fan-out then fan-in
    s >> [p1, p2, p3] >> agg
```

### **Real-World Example: Data Processing Pipeline**
```python
@dag(...)
def etl_pipeline():
    @task
    def extract_sales_data():
        """Extract from sales system"""
        time.sleep(10)  # Simulate extraction
        return {"sales": 1000}
    
    @task
    def extract_inventory_data():
        """Extract from inventory system"""  
        time.sleep(15)  # Simulate extraction
        return {"inventory": 500}
    
    @task
    def extract_customer_data():
        """Extract from CRM"""
        time.sleep(8)  # Simulate extraction
        return {"customers": 300}
    
    @task
    def validate_and_combine(sales, inventory, customers):
        """Fan-in: Wait for all data before processing"""
        # This only runs after ALL extracts complete
        return {
            "total_records": sales["sales"] + inventory["inventory"] + customers["customers"],
            "status": "ready for loading"
        }
    
    @task
    def load_to_warehouse(combined_data):
        """Final load step"""
        return f"Loaded {combined_data['total_records']} records"
    
    # Parallel extraction (fan-out from implicit start)
    sales = extract_sales_data()
    inv = extract_inventory_data()
    cust = extract_customer_data()
    
    # Fan-in to combine
    combined = validate_and_combine(sales, inv, cust)
    
    # Final step
    load_to_warehouse(combined)
```

## 3. Combined Patterns (Diamond Pattern)

### **Visual Representation**
```
                  ┌─→ Task B ─┐
                  │           │
    Task A ───────┼─→ Task C ─┼─→ Task E
                  │           │
                  └─→ Task D ─┘
```

### **Example: Complete Workflow**
```python
@dag(...)
def diamond_pattern():
    @task
    def init_process():
        """Single starting point"""
        return {"timestamp": datetime.now(), "run_id": "12345"}
    
    @task
    def process_in_region_1(config):
        """Process in US region"""
        time.sleep(5)
        return {"region": "US", "status": "complete"}
    
    @task
    def process_in_region_2(config):
        """Process in EU region"""
        time.sleep(7)
        return {"region": "EU", "status": "complete"}
    
    @task
    def process_in_region_3(config):
        """Process in ASIA region"""
        time.sleep(6)
        return {"region": "ASIA", "status": "complete"}
    
    @task
    def consolidate_results(r1, r2, r3):
        """Fan-in: Wait for all regions"""
        return {
            "regions_processed": [r1["region"], r2["region"], r3["region"]],
            "all_complete": all(r["status"] == "complete" for r in [r1, r2, r3])
        }
    
    @task
    def final_report(results):
        """Single final task"""
        return f"Processed {len(results['regions_processed'])} regions successfully"
    
    # Diamond pattern
    init = init_process()
    
    # Fan-out to regions (parallel processing)
    us = process_in_region_1(init)
    eu = process_in_region_2(init)
    asia = process_in_region_3(init)
    
    # Fan-in from regions
    consolidated = consolidate_results(us, eu, asia)
    
    # Final single task
    report = final_report(consolidated)
```

## 4. Impact on Concurrency

### **How Fan-Out Affects Concurrency**
```python
# With concurrency=1: Tasks run serially (30 seconds total)
# With concurrency=3: Tasks run in parallel (10 seconds total)

@task
def task_10_seconds():
    time.sleep(10)
    
start >> [task_10_seconds(), task_10_seconds(), task_10_seconds()] >> end
```

### **Concurrency Limits and Fan-Out**
```python
# If you fan-out to 10 tasks but concurrency=3
# Only 3 tasks run at a time, others queue

@dag(default_args={'max_active_tis_per_dag': 3})  # Limit concurrent tasks
def concurrency_limited():
    @task
    def create_tasks():
        return list(range(10))  # Creates 10 tasks
    
    @task
    def process(item):
        print(f"Processing {item}")
        time.sleep(5)
        
    items = create_tasks()
    
    # This creates 10 tasks, but only 3 run at once
    for item in items:
        process(item)
```

## 5. Best Practices

### **1. Balance Fan-Out Width**
```python
# Good: Reasonable fan-out
prep >> [process_a(), process_b(), process_c()]  # 3-way split

# Caution: Very wide fan-out
prep >> [task() for _ in range(100)]  # May overwhelm system
```

### **2. Use Fan-In for Synchronization**
```python
# Ensure all data is ready before critical step
[extract_1(), extract_2(), extract_3()] >> validate_all_data() >> load()
```

### **3. Consider Queue Segregation**
```python
@task(queue='high_priority')
def critical_path():
    pass

@task(queue='bulk_processing')  
def parallel_bulk_task():
    pass
```

### **4. Monitor Parallel Execution**
```python
@task
def log_timing(task_name):
    start = time.time()
    # ... do work ...
    end = time.time()
    print(f"{task_name} took {end-start} seconds")
```

## Summary Table

| Pattern | Description | Use Case | Concurrency Impact |
|---------|-------------|----------|-------------------|
| Fan-Out | 1 → Many | Parallel processing of independent tasks | Increases parallelism |
| Fan-In | Many → 1 | Synchronization point, aggregation | Creates wait point |
| Diamond | 1 → Many → 1 | Complete parallel workflow | Maximum parallelism in middle |

## Testing Patterns

```python
# Create this DAG to experiment with patterns
@dag(dag_id='pattern_tester', ...)
def test_patterns():
    @task
    def show_pattern(pattern_name, start_time):
        end_time = time.time()
        return f"{pattern_name}: {end_time - start_time:.1f}s"
    
    start_time = time.time()
    
    # Test different patterns and measure execution time
    # Run with different concurrency settings to see impact
```

The key insight: **Fan-out creates opportunities for parallel execution, while fan-in creates synchronization points. Proper use of these patterns, combined with appropriate concurrency settings, can dramatically reduce total execution time.**
