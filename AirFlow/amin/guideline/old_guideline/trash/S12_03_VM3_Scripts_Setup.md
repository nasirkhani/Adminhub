# S12 VM3 Scripts Setup

Create these scripts on VM3 (192.168.83.133) to support the card processing workflow.

## 1. S12_card_processor.py

```bash
# On VM3
vi ~/scripts/S12_card_processor.py
```

Content:
```python
#!/usr/bin/env python3
"""
S12_card_processor.py - Main card processing logic
"""
import sys
import os
import time
from datetime import datetime

def process_card_file(input_file):
    """Process a card batch file"""
    print(f"[PROCESSOR] Starting processing of {input_file}")
    
    if not os.path.exists(input_file):
        raise Exception(f"Input file not found: {input_file}")
    
    # Simulate processing work
    print("[PROCESSOR] Reading card data...")
    time.sleep(2)  # Simulate I/O
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Generate output files
    base_name = input_file.replace('.txt', '')
    processed_file = f"{base_name}.processed"
    report_file = f"{base_name}.report"
    
    print("[PROCESSOR] Processing cards...")
    processed_count = 0
    
    with open(processed_file, 'w') as pf:
        for line in lines:
            # Simulate card processing
            time.sleep(0.1)  # Simulate processing each card
            processed_line = f"PROCESSED: {line.strip()}"
            pf.write(f"{processed_line}\n")
            processed_count += 1
    
    # Write report
    with open(report_file, 'w') as rf:
        rf.write(f"S12 Card Processing Report\n")
        rf.write(f"========================\n")
        rf.write(f"Input File: {input_file}\n")
        rf.write(f"Processing Time: {datetime.now()}\n")
        rf.write(f"Total Records: {processed_count}\n")
        rf.write(f"Output File: {processed_file}\n")
        rf.write(f"Status: SUCCESS\n")
    
    print(f"[PROCESSOR] Completed: {processed_count} records processed")
    return processed_count

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: S12_card_processor.py <input_file>")
        sys.exit(1)
    
    try:
        count = process_card_file(sys.argv[1])
        print(f"SUCCESS: Processed {count} records")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
```

## 2. S12_card_validator.py

```bash
vi ~/scripts/S12_card_validator.py
```

Content:
```python
#!/usr/bin/env python3
"""
S12_card_validator.py - Validate card data files
"""
import sys
import os
import time

def validate_card_file(input_file):
    """Validate card file format and content"""
    print(f"[VALIDATOR] Starting validation of {input_file}")
    
    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        return False
    
    # Simulate validation work
    time.sleep(1)
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    if len(lines) == 0:
        print("ERROR: Empty file")
        return False
    
    # Validate each line (simple validation)
    for i, line in enumerate(lines):
        parts = line.strip().split(',')
        if len(parts) < 4:
            print(f"ERROR: Invalid format at line {i+1}")
            return False
    
    print(f"[VALIDATOR] File is VALID: {len(lines)} records")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: S12_card_validator.py <input_file>")
        sys.exit(1)
    
    if validate_card_file(sys.argv[1]):
        print("VALID")
        sys.exit(0)
    else:
        print("INVALID")
        sys.exit(1)
```

## 3. S12_card_reporter.py

```bash
vi ~/scripts/S12_card_reporter.py
```

Content:
```python
#!/usr/bin/env python3
"""
S12_card_reporter.py - Generate processing reports
"""
import sys
import os
import glob
from datetime import datetime

def generate_report(directory):
    """Generate summary report for all processed files"""
    print(f"[REPORTER] Generating report for {directory}")
    
    processed_files = glob.glob(f"{directory}/*.processed")
    report_files = glob.glob(f"{directory}/*.report")
    
    summary = {
        'total_files': len(processed_files),
        'total_records': 0,
        'report_time': datetime.now()
    }
    
    # Count total records
    for pf in processed_files:
        with open(pf, 'r') as f:
            summary['total_records'] += len(f.readlines())
    
    # Generate summary report
    report_path = f"{directory}/S12_summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_path, 'w') as rf:
        rf.write("S12 CARD PROCESSING SUMMARY REPORT\n")
        rf.write("==================================\n")
        rf.write(f"Report Generated: {summary['report_time']}\n")
        rf.write(f"Total Files Processed: {summary['total_files']}\n")
        rf.write(f"Total Records Processed: {summary['total_records']}\n")
        rf.write("\nFile Details:\n")
        
        for pf in sorted(processed_files):
            rf.write(f"- {os.path.basename(pf)}\n")
    
    print(f"[REPORTER] Report saved to: {report_path}")
    return report_path

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: S12_card_reporter.py <directory>")
        sys.exit(1)
    
    try:
        report_path = generate_report(sys.argv[1])
        print(f"SUCCESS: Report generated at {report_path}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
```

## 4. Make Scripts Executable

```bash
# On VM3
chmod +x ~/scripts/S12_*.py

# Test the scripts
~/scripts/S12_card_validator.py --help
~/scripts/S12_card_processor.py --help
~/scripts/S12_card_reporter.py --help
```

## 5. Create Test Data on VM2

```bash
# On VM2 - Create test card files
mkdir -p ~/card/in

# Create 5 test files for concurrency demo
for i in {1..5}; do
    cat > ~/card/in/card_batch_00${i}.txt << EOF
CARD00${i}1,John Doe ${i},1234567890123456,2025-12
CARD00${i}2,Jane Smith ${i},2345678901234567,2026-01
CARD00${i}3,Bob Johnson ${i},3456789012345678,2025-06
CARD00${i}4,Alice Brown ${i},4567890123456789,2026-03
CARD00${i}5,Charlie Wilson ${i},5678901234567890,2025-09
EOF
done

ls -la ~/card/in/
```

## 6. Monitor Concurrency in Action

When you run the concurrent DAG, use these commands to see parallelism:

### On VM1 - Monitor Queues
```bash
# Watch queue activity
watch -n 1 'sudo rabbitmqctl list_queues name messages consumers'

# Monitor in Flower
# http://192.168.83.129:5555/tasks
# Look for multiple tasks in "STARTED" state
```

### On VM3 - Monitor Processing
```bash
# Watch files being created in real-time
watch -n 1 'ls -la ~/card/in/*.processed 2>/dev/null | wc -l'

# See active Python processes
watch -n 1 'ps aux | grep S12_card | grep -v grep'
```

### On VM4 - Monitor Worker
```bash
# Watch worker logs
sudo journalctl -u airflow-worker -f | grep CONCURRENT

# See worker CPU/memory usage
top -u rocky
```
