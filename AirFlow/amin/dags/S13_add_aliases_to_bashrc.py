# S13_add_aliases_to_bashrc.py
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import paramiko
import time

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# SSH Configuration
SSH_KEY_PATH = '/home/rocky/.ssh/id_ed25519'  # Change to None if using password
SSH_PASSWORD = '111'  # Used if SSH_KEY_PATH is None
SSH_USERNAME = 'rocky'
SSH_PORT = 22
SSH_TIMEOUT = 30

# Target VMs configuration
TARGET_VMS = [
    {'ip': '192.168.83.129', 'hostname': 'airflow'},
    {'ip': '192.168.83.152', 'hostname': 'airflow2'},
    {'ip': '192.168.83.132', 'hostname': 'ftp'},
    {'ip': '192.168.83.150', 'hostname': 'nfs2'},
    {'ip': '192.168.83.200', 'hostname': 'nfs-cluster'},
    {'ip': '192.168.83.133', 'hostname': 'card1'},
    {'ip': '192.168.83.131', 'hostname': 'worker1'},
    {'ip': '192.168.83.153', 'hostname': 'worker2'},
    {'ip': '192.168.83.141', 'hostname': 'mq1'},
    {'ip': '192.168.83.142', 'hostname': 'mq2'},
    {'ip': '192.168.83.138', 'hostname': 'mq3'},
    {'ip': '192.168.83.148', 'hostname': 'sql1'},
    {'ip': '192.168.83.147', 'hostname': 'sql2'},
    {'ip': '192.168.83.149', 'hostname': 'sql3'},
]

# Aliases to add (each line will be added to .bashrc)
ALIASES_TO_ADD = [
    "# --- HAProxy Aliases ---",
    "alias jha='sudo journalctl -u haproxy.service -f'",
    "alias sha='sudo systemctl status haproxy.service'",
    "alias stha='sudo systemctl start haproxy.service'",
    "alias spha='sudo systemctl stop haproxy.service'",
    "alias rha='sudo systemctl restart haproxy.service'",
    "",
    "# --- Airflow Webserver Aliases ---",
    "alias jw='sudo journalctl -u airflow-webserver.service -f'",
    "alias sw='sudo systemctl status airflow-webserver.service'",
    "alias stw='sudo systemctl start airflow-webserver.service'",
    "alias spw='sudo systemctl stop airflow-webserver.service'",
    "alias rw='sudo systemctl restart airflow-webserver.service'",
    "",
    "# --- Airflow Scheduler Aliases ---",
    "alias js='sudo journalctl -u airflow-scheduler.service -f'",
    "alias ss='sudo systemctl status airflow-scheduler.service'",
    "alias sts='sudo systemctl start airflow-scheduler.service'",
    "alias sps='sudo systemctl stop airflow-scheduler.service'",
    "alias rs='sudo systemctl restart airflow-scheduler.service'",
    "",
    "# --- Airflow DAG Processor Aliases ---",
    "alias jd='sudo journalctl -u airflow-dag-processor.service -f'",
    "alias sd='sudo systemctl status airflow-dag-processor.service'",
    "alias std='sudo systemctl start airflow-dag-processor.service'",
    "alias spd='sudo systemctl stop airflow-dag-processor.service'",
    "alias rd='sudo systemctl restart airflow-dag-processor.service'",
    "",
    "# --- Airflow Worker Aliases ---",
    "alias jwork='sudo journalctl -u airflow-worker.service -f'",
    "alias swork='sudo systemctl status airflow-worker.service'",
    "alias stwork='sudo systemctl start airflow-worker.service'",
    "alias spwork='sudo systemctl stop airflow-worker.service'",
    "alias rwork='sudo systemctl restart airflow-worker.service'",
    "",
    "# --- RabbitMQ Server Aliases ---",
    "alias jmq='sudo journalctl -u rabbitmq-server.service -f'",
    "alias smq='sudo systemctl status rabbitmq-server.service'",
    "alias stmq='sudo systemctl start rabbitmq-server.service'",
    "alias spmq='sudo systemctl stop rabbitmq-server.service'",
    "alias rmq='sudo systemctl restart rabbitmq-server.service'",
    "",
    "# --- Patroni Aliases ---",
    "alias jpat='sudo journalctl -u patroni.service -f'",
    "alias spat='sudo systemctl status patroni.service'",
    "alias stpat='sudo systemctl start patroni.service'",
    "alias sppat='sudo systemctl stop patroni.service'",
    "alias rpat='sudo systemctl restart patroni.service'",
    "",
    "# --- ETCD Aliases ---",
    "alias jet='sudo journalctl -u etcd.service -f'",
    "alias set='sudo systemctl status etcd.service'",
    "alias stet='sudo systemctl start etcd.service'"
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def ssh_connect(vm_ip):
    """Create SSH connection to a VM"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        if SSH_KEY_PATH:
            # Use SSH key authentication
            ssh.connect(
                hostname=vm_ip,
                username=SSH_USERNAME,
                key_filename=SSH_KEY_PATH,
                port=SSH_PORT,
                timeout=SSH_TIMEOUT
            )
        else:
            # Use password authentication
            ssh.connect(
                hostname=vm_ip,
                username=SSH_USERNAME,
                password=SSH_PASSWORD,
                port=SSH_PORT,
                timeout=SSH_TIMEOUT
            )
        return ssh
    except Exception as e:
        raise Exception(f"Failed to connect to {vm_ip}: {str(e)}")

def execute_ssh_command(ssh, command):
    """Execute a command via SSH and return output"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    
    if exit_code != 0:
        raise Exception(f"Command failed (exit code {exit_code}): {error}")
    
    return output

def extract_alias_name(alias_line):
    """Extract alias name from alias line (e.g., 'alias jha=' -> 'jha')"""
    if alias_line.strip().startswith('alias ') and '=' in alias_line:
        # Extract text between 'alias ' and '='
        alias_part = alias_line.strip()[6:]  # Remove 'alias '
        alias_name = alias_part.split('=')[0]
        return alias_name
    return None

# Marker comments to detect if aliases section already exists
START_MARKER = "# === Airflow Management Aliases (Added by DAG) ==="
END_MARKER = "# === End of Airflow Management Aliases ==="

# =============================================================================
# DAG DEFINITION
# =============================================================================

@dag(
    dag_id='S13_add_aliases_to_bashrc',
    description='Add system aliases to .bashrc on target VMs',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_tasks=3,  # DAG-level concurrency limit
    default_args={
        'owner': 'rocky',
        'retries': 0,  # No retries as requested
    },
    tags=['bashrc', 'aliases', 'system-management']
)
def add_aliases_workflow():
    
    @task
    def add_aliases_to_vm(vm_config: dict):
        """Add aliases to .bashrc on a single VM"""
        vm_ip = vm_config['ip']
        vm_hostname = vm_config['hostname']
        
        print(f"=== Processing VM: {vm_hostname} ({vm_ip}) ===")
        
        ssh = None
        try:
            # Connect to VM
            print(f"Connecting to {vm_ip}...")
            ssh = ssh_connect(vm_ip)
            print("✓ SSH connection established")
            
            # Read current .bashrc content
            print("Reading current .bashrc content...")
            try:
                current_bashrc = execute_ssh_command(ssh, "cat ~/.bashrc")
            except:
                # If .bashrc doesn't exist, create it
                current_bashrc = ""
                print("⚠ .bashrc not found, will create new one")
            
            # Check if our aliases section already exists
            if START_MARKER in current_bashrc and END_MARKER in current_bashrc:
                print("✓ Airflow aliases section already exists in .bashrc")
                print("✓ No changes needed - skipping to avoid duplicates")
                
                # Count existing aliases in our section
                existing_count = 0
                in_our_section = False
                for line in current_bashrc.split('\n'):
                    if START_MARKER in line:
                        in_our_section = True
                        continue
                    elif END_MARKER in line:
                        in_our_section = False
                        continue
                    elif in_our_section and extract_alias_name(line):
                        existing_count += 1
                
                return {
                    'vm': vm_hostname,
                    'ip': vm_ip,
                    'status': 'success',
                    'action': 'already_exists',
                    'added': 0,
                    'skipped': existing_count,
                    'message': 'Aliases section already exists'
                }
            
            # Find existing alias names in .bashrc (outside our section)
            existing_aliases = set()
            for line in current_bashrc.split('\n'):
                alias_name = extract_alias_name(line)
                if alias_name:
                    existing_aliases.add(alias_name)
            
            print(f"Found {len(existing_aliases)} existing aliases in .bashrc")
            
            # Count aliases that would conflict
            conflicting_aliases = []
            for alias_line in ALIASES_TO_ADD:
                alias_name = extract_alias_name(alias_line)
                if alias_name and alias_name in existing_aliases:
                    conflicting_aliases.append(alias_name)
            
            if conflicting_aliases:
                print(f"⚠ Found {len(conflicting_aliases)} conflicting aliases: {conflicting_aliases}")
                print("⚠ Will skip adding to avoid conflicts")
                return {
                    'vm': vm_hostname,
                    'ip': vm_ip,
                    'status': 'success',
                    'action': 'conflicts_detected',
                    'added': 0,
                    'skipped': len(conflicting_aliases),
                    'conflicts': conflicting_aliases
                }
            
            # Create backup of .bashrc
            backup_cmd = f"cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d_%H%M%S)"
            execute_ssh_command(ssh, backup_cmd)
            print("✓ Created .bashrc backup")
            
            # Add new aliases section to .bashrc
            print("Adding aliases section to .bashrc...")
            
            # Add the complete section
            execute_ssh_command(ssh, f"echo '' >> ~/.bashrc")
            execute_ssh_command(ssh, f"echo '{START_MARKER}' >> ~/.bashrc")
            
            added_count = 0
            for alias_line in ALIASES_TO_ADD:
                if alias_line.strip():  # Skip empty lines in echo
                    # Escape single quotes in the alias line
                    escaped_line = alias_line.replace("'", "'\"'\"'")
                    execute_ssh_command(ssh, f"echo '{escaped_line}' >> ~/.bashrc")
                    if extract_alias_name(alias_line):  # Count only actual aliases, not comments
                        added_count += 1
                else:
                    execute_ssh_command(ssh, f"echo '' >> ~/.bashrc")
            
            # Add closing marker
            execute_ssh_command(ssh, f"echo '{END_MARKER}' >> ~/.bashrc")
            
            print(f"✓ Added {added_count} aliases to .bashrc")
            
            # Source .bashrc to apply changes
            print("Sourcing .bashrc to apply changes...")
            execute_ssh_command(ssh, "source ~/.bashrc")
            print("✓ .bashrc sourced successfully")
            
            return {
                'vm': vm_hostname,
                'ip': vm_ip,
                'status': 'success',
                'action': 'added_aliases',
                'added': added_count,
                'skipped': 0,
                'verified': added_count
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ ERROR processing {vm_hostname} ({vm_ip}): {error_msg}")
            
            return {
                'vm': vm_hostname,
                'ip': vm_ip,
                'status': 'failed',
                'error': error_msg,
                'added': 0,
                'skipped': 0
            }
        
        finally:
            # Always close SSH connection
            if ssh:
                ssh.close()
                print(f"✓ SSH connection to {vm_ip} closed")
    
    @task
    def generate_summary_report(results: list):
        """Generate a summary report of all operations"""
        print("\n" + "="*60)
        print("           ALIASES DEPLOYMENT SUMMARY REPORT")
        print("="*60)
        
        successful_vms = [r for r in results if r['status'] == 'success']
        failed_vms = [r for r in results if r['status'] == 'failed']
        
        print(f"\nTotal VMs processed: {len(results)}")
        print(f"Successful: {len(successful_vms)}")
        print(f"Failed: {len(failed_vms)}")
        
        if successful_vms:
            print(f"\n--- SUCCESSFUL DEPLOYMENTS ---")
            for result in successful_vms:
                if result['action'] == 'already_exists':
                    action_desc = f"Already exists ({result['skipped']} aliases)"
                elif result['action'] == 'conflicts_detected':
                    action_desc = f"Conflicts detected ({result['skipped']} conflicts)"
                elif result['action'] == 'added_aliases':
                    action_desc = f"Added {result['added']} aliases"
                else:
                    action_desc = "No changes needed"
                    
                print(f"✓ {result['vm']:12} ({result['ip']:15}) - {action_desc}")
        
        if failed_vms:
            print(f"\n--- FAILED DEPLOYMENTS ---")
            for result in failed_vms:
                print(f"✗ {result['vm']:12} ({result['ip']:15}) - {result['error']}")
        
        # Calculate totals
        total_added = sum(r.get('added', 0) for r in successful_vms)
        already_exists_count = len([r for r in successful_vms if r['action'] == 'already_exists'])
        conflicts_count = len([r for r in successful_vms if r['action'] == 'conflicts_detected'])
        
        print(f"\n--- STATISTICS ---")
        print(f"Total aliases added: {total_added}")
        print(f"VMs with existing aliases section: {already_exists_count}")
        print(f"VMs with conflicts detected: {conflicts_count}")
        print(f"Success rate: {len(successful_vms)}/{len(results)} ({100*len(successful_vms)/len(results):.1f}%)")
        
        print("\n" + "="*60)
        
        return {
            'total_vms': len(results),
            'successful': len(successful_vms),
            'failed': len(failed_vms),
            'total_added': total_added,
            'already_exists': already_exists_count,
            'conflicts': conflicts_count,
            'success_rate': len(successful_vms)/len(results) if results else 0
        }
    
    # Create tasks for each VM with hostname-based task IDs
    vm_results = []
    for vm_config in TARGET_VMS:
        # Create task with custom task_id based on hostname
        task_id = f"add_aliases_{vm_config['hostname']}"
        
        # Use .override() to set custom task_id
        vm_task = add_aliases_to_vm.override(task_id=task_id)(vm_config)
        vm_results.append(vm_task)
    
    # Generate summary report after all VM tasks complete
    summary = generate_summary_report(vm_results)
    
    return summary

# Create DAG instance
dag_instance = add_aliases_workflow()
