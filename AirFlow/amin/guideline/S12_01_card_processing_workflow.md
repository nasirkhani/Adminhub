# Card Processing Queue Configuration

## Overview

This document describes how to configure a dedicated queue (`card_processing_queue`) for the card processing workflow with specific concurrency settings.

## Configuration Steps

### 1. Update Worker Configuration on VM4

Edit the worker systemd service to listen to the new queue:

```bash
# On VM4
sudo vi /etc/systemd/system/airflow-worker.service
```

Update the ExecStart line to include the new queue:
```ini
ExecStart=/bin/bash -c 'exec /home/rocky/.local/bin/airflow celery worker --queues card_processing_queue,remote_tasks,default --concurrency 5'
```

Note: `--concurrency 5` sets the worker to handle 5 tasks simultaneously.

Restart the worker:
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-worker
sudo systemctl status airflow-worker
```

### 2. Create Card Processor Script on VM3

SSH into VM3 and create the processing script:

```bash
# On VM3
ssh rocky@192.168.83.133

# Create scripts directory
mkdir -p ~/scripts

# Create the card processor script
vi ~/scripts/card_processor.py
```

Example card processor script:
```python
#!/usr/bin/env python3
"""
Card processor script for VM3
Processes card batch files and generates output files
"""
import sys
import os
from datetime import datetime

def process_card_file(input_file):
    """Process a card batch file"""
    
    if not os.path.exists(input_file):
        raise Exception(f"Input file not found: {input_file}")
    
    # Read input file
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Generate output files
    base_name = input_file.replace('.txt', '')
    processed_file = f"{base_name}.processed"
    report_file = f"{base_name}.report"
    
    # Process data (example logic)
    processed_count = 0
    with open(processed_file, 'w') as pf:
        for line in lines:
            # Your card processing logic here
            processed_line = line.strip().upper()  # Example transformation
            pf.write(f"{processed_line}\n")
            processed_count += 1
    
    # Write report
    with open(report_file, 'w') as rf:
        rf.write(f"Processing Report\n")
        rf.write(f"================\n")
        rf.write(f"Input File: {input_file}\n")
        rf.write(f"Processing Time: {datetime.now()}\n")
        rf.write(f"Total Records: {processed_count}\n")
        rf.write(f"Status: SUCCESS\n")
    
    print(f"Processed {processed_count} records from {input_file}")
    return processed_count

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: card_processor.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    try:
        count = process_card_file(input_file)
        print(f"Success: Processed {count} records")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
```

Make it executable:
```bash
chmod +x ~/scripts/card_processor.py
```

### 3. Update VM Configuration

Update the VM configuration file on VM2 to include VM3:

```bash
# On VM2
vi /srv/airflow/dags/config/simple_vms.py
```

Ensure it includes:
```python
TARGET_VMS = {
    'vm1': {
        'host': '192.168.83.131',
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519'
    },
    'vm3': {
        'host': '192.168.83.133',
        'username': 'rocky',
        'ssh_key': '/home/rocky/.ssh/id_ed25519'
    }
}
```

### 4. Create Test Card Files on VM2

Create test files to trigger the workflow:

```bash
# On VM2
mkdir -p ~/card/in
mkdir -p ~/card/archive

# Create test card batch files
echo "CARD001,John Doe,1234567890123456,2025-12" > ~/card/in/card_batch_001.txt
echo "CARD002,Jane Smith,2345678901234567,2026-01" >> ~/card/in/card_batch_001.txt

echo "CARD003,Bob Johnson,3456789012345678,2025-06" > ~/card/in/card_batch_002.txt
echo "CARD004,Alice Brown,4567890123456789,2026-03" >> ~/card/in/card_batch_002.txt

echo "CARD005,Charlie Wilson,5678901234567890,2025-09" > ~/card/in/card_batch_003.txt
```

### 5. Deploy the DAG

Copy the DAG file to VM2's DAG folder:

```bash
# On VM2
cd /srv/airflow/dags
# Create S12_card_processing_workflow.py with the content from the artifact above
```

### 6. Monitor Queue Usage

To monitor the card processing queue:

```bash
# Check RabbitMQ queues
sudo rabbitmqctl list_queues name messages consumers | grep card

# Monitor in Flower UI
# http://192.168.83.129:5555
# Look for tasks with queue='card_processing_queue'

# Check worker logs
sudo journalctl -u airflow-worker -f | grep card_processing_queue
```

## Queue Architecture Benefits

1. **Dedicated Resources**: Card processing tasks won't compete with other tasks
2. **Scalability**: Can add more workers listening to this queue
3. **Priority Control**: Can prioritize card processing over other workflows
4. **Monitoring**: Easy to track card-specific task performance

## Testing the Workflow

1. **Trigger the DAG**:
   - Access Airflow UI: http://192.168.83.129:8080
   - Find `S12_card_processing_workflow`
   - Click "Trigger DAG"

2. **Monitor Execution**:
   - The sensor will check for files every 5 minutes
   - Once files are detected, they'll be transferred to VM3
   - Processing will happen on VM3
   - Source files will be archived on VM2

3. **Verify Results**:
   ```bash
   # On VM3 - Check processed files
   ls -la ~/card/in/*.processed
   ls -la ~/card/in/*.report
   cat ~/card/in/*.report
   
   # On VM2 - Check archived files
   ls -la ~/card/archive/
   ```

## Concurrency Explained

- **DAG-level concurrency**: `max_active_tasks=5` means maximum 5 tasks from this DAG can run simultaneously
- **Worker concurrency**: `--concurrency 5` means the worker can handle 5 tasks total (from all DAGs)
- **Queue-specific**: All tasks use `card_processing_queue`, isolating them from other workflows

## Future Enhancements

1. **Multiple Workers**: Add more workers listening to `card_processing_queue` for scaling
2. **Priority Queues**: Create high/low priority queues for different card types
3. **Error Queue**: Separate queue for retry/error handling
4. **Real-time Processing**: Reduce sensor interval for near real-time processing

===============================================================

I'll create a comprehensive walkthrough documentation that includes all the fixes we discovered, followed by the new DAG implementation.Now, let me create the new DAG for your card processing workflow:
## Summary

I've created two comprehensive documents for you:

### 1. **Distributed Airflow Setup - Complete Walkthrough**
This document includes all the fixes we discovered during our debugging:
- Firewall configurations for all VMs
- Permission fixes using bash wrappers
- Missing dependencies (SSH provider, paramiko)
- Proper airflow.cfg configuration for VM2
- SystemD service configurations with all corrections

### 2. **Card Processing Workflow (S12)**
A new DAG that implements your requirements:
- **Custom Queue**: `card_processing_queue` 
- **Concurrency**: Set to 5 (both DAG-level and worker-level)
- **Target VM**: All processing happens on VM3 (card1, 192.168.83.133)
- **Workflow Logic**: Similar to S06_02 with sensor → transfer → check → process → cleanup

### Key Configuration Changes Needed:

1. **On VM4 (Worker)**: Update the systemd service to listen to the new queue with concurrency 5:
   ```bash
   ExecStart=/bin/bash -c 'exec /home/rocky/.local/bin/airflow celery worker --queues card_processing_queue,remote_tasks,default --concurrency 5'
   ```

2. **On VM3 (Target)**: Create the card processor script at `/home/rocky/scripts/card_processor.py`

3. **On VM2 (NFS)**: 
   - Save the DAG as `/srv/airflow/dags/S12_card_processing_workflow.py`
   - Create test files in `/home/rocky/card/in/`

The workflow will:
- Monitor for card files on VM2 every 5 minutes
- Transfer detected files to VM3 via FTP
- Check if processing is needed (skip if already processed)
- Run the card processor script on VM3
- Archive processed source files on VM2

All tasks will run on the dedicated `card_processing_queue` with a maximum of 5 concurrent tasks, ensuring isolated and controlled processing of card data.
