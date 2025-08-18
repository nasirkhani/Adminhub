#!/usr/bin/env python3

import subprocess
import sys

# Target VMs
targets = {
    '10.101.20.47': 'celery-1',
    '10.101.20.48': 'celery-2',
    '10.101.20.49': 'celery-3',
    '10.101.20.50': 'celery-4',
    '10.101.20.56': 'ftp',
    '10.101.20.57': 'zabbix',
    '10.101.20.54': 'nfs-1',
    '10.101.20.55': 'nfs-2',
    '10.101.20.40': 'postgre-1',
    '10.101.20.41': 'postgre-2',
    '10.101.20.42': 'postgre-3',
    '10.101.20.51': 'rabbit-1',
    '10.101.20.52': 'rabbit-2',
    '10.101.20.53': 'rabbit-3',
    '10.101.20.45': 'scheduler-1',
    '10.101.20.46': 'scheduler-2',
    '10.101.20.43': 'webserver-1',
    '10.101.20.44': 'webserver-2',
    '10.101.20.159': 'informix',
    '10.101.20.135': 'ibmmq',
    '10.101.20.143': 'tcp',
    '10.101.20.131': 'sw'
}

username = 'rocky'

def run_ssh_command(ip, command):
    """Run SSH command on remote server"""
    # Try SSH key first
    ssh_cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o PasswordAuthentication=no {username}@{ip} '{command}'"
    
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Command successful on {ip} (SSH key)")
            return True
    except:
        pass
    
    # If SSH key fails, try with password using sshpass
    ssh_cmd_pass = f"sshpass -p '111' ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {username}@{ip} '{command}'"
    
    try:
        result = subprocess.run(ssh_cmd_pass, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Command successful on {ip} (password)")
            return True
        else:
            print(f"✗ Command failed on {ip}: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error connecting to {ip}: {e}")
        return False

# Create hosts entries file
hosts_content = ""
for ip, hostname in targets.items():
    hosts_content += f"{ip} {hostname}\\n"

# Main script
for ip, hostname in targets.items():
    print(f"\n--- Working on {hostname} ({ip}) ---")
    
    # 1. Update system packages
    print("Updating system packages...")
    run_ssh_command(ip, "sudo dnf update -y")
    run_ssh_command(ip, "sudo dnf upgrade -y")
    
    # 2. Install common packages
    print("Installing common packages...")
    run_ssh_command(ip, "sudo dnf install -y vim curl wget rsync nfs-utils firewalld")
    
    # 3. Disable SELinux
    print("Disabling SELinux...")
    run_ssh_command(ip, "sudo setenforce 0")
    run_ssh_command(ip, "sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config")
    
    # 4. Configure timezone
    print("Setting timezone to Asia/Tehran...")
    run_ssh_command(ip, "sudo timedatectl set-timezone Asia/Tehran")
    
    # 5. Create rocky user with sudo privileges
    print("Setting up rocky user...")
    run_ssh_command(ip, "sudo useradd -m -s /bin/bash rocky")
    run_ssh_command(ip, "echo 'rocky:111' | sudo chpasswd")
    run_ssh_command(ip, "echo 'rocky ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/rocky")
    
    # 6. Add hosts to /etc/hosts (remove duplicates first)
    print("Updating /etc/hosts...")
    
    # Remove old entries
    for target_ip, target_host in targets.items():
        cleanup_cmd = f"sudo sed -i '/{target_ip}/d; /{target_host}/d' /etc/hosts"
        run_ssh_command(ip, cleanup_cmd)
    
    # Add new entries
    add_hosts_cmd = f"echo -e '{hosts_content}' | sudo tee -a /etc/hosts"
    run_ssh_command(ip, add_hosts_cmd)
    
    print(f"Finished {hostname}")

print("\nAll done!")
