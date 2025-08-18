#!/bin/bash

# Simple Airflow Cluster Setup Script
# Run from celery-1 VM

# List of all VMs (hostname:ip)
VMS="
celery-2:10.101.20.48
celery-3:10.101.20.49
celery-4:10.101.20.50
ftp:10.101.20.56
zabbix:10.101.20.57
nfs-1:10.101.20.54
nfs-2:10.101.20.55
postgre-1:10.101.20.40
postgre-2:10.101.20.41
postgre-3:10.101.20.42
rabbit-1:10.101.20.51
rabbit-2:10.101.20.52
rabbit-3:10.101.20.53
scheduler-1:10.101.20.45
scheduler-2:10.101.20.46
webserver-1:10.101.20.43
webserver-2:10.101.20.44
informix:10.101.20.159
ibmmq:10.101.20.135
tcp:10.101.20.143
sw:10.101.20.131
"

USERNAME="rocky"
PASSWORD="111"

# Function to run command on remote VM
run_on_vm() {
    local host=$1
    local ip=$2
    local cmd=$3
    
    echo "Running on $host ($ip): $cmd"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USERNAME@$ip "$cmd"
}

# Install sshpass if not available
install_sshpass() {
    if ! command -v sshpass &> /dev/null; then
        echo "Installing sshpass..."
        sudo dnf install -y sshpass
    fi
}

# Main setup function
setup_vm() {
    local hostname=$1
    local ip=$2
    
    echo "=================================="
    echo "Setting up $hostname ($ip)"
    echo "=================================="
    
    # 1. Update system
    run_on_vm $hostname $ip "sudo dnf update -y"
    
    # 2. Install basic packages
    run_on_vm $hostname $ip "sudo dnf install -y vim curl wget nfs-utils"
    
    # 3. Disable SELinux
    run_on_vm $hostname $ip "sudo setenforce 0"
    run_on_vm $hostname $ip "sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config"
    
    # 4. Set timezone
    run_on_vm $hostname $ip "sudo timedatectl set-timezone Asia/Tehran"
    
    # 5. Set hostname
    run_on_vm $hostname $ip "sudo nmcli general hostname $hostname"
    
    # 6. Add hosts entries
    run_on_vm $hostname $ip "echo '
10.101.20.47 celery-1
10.101.20.48 celery-2
10.101.20.49 celery-3
10.101.20.50 celery-4
10.101.20.56 ftp
10.101.20.57 zabbix
10.101.20.54 nfs-1
10.101.20.55 nfs-2
10.101.20.40 postgre-1
10.101.20.41 postgre-2
10.101.20.42 postgre-3
10.101.20.51 rabbit-1
10.101.20.52 rabbit-2
10.101.20.53 rabbit-3
10.101.20.45 scheduler-1
10.101.20.46 scheduler-2
10.101.20.43 webserver-1
10.101.20.44 webserver-2
10.101.20.159 informix
10.101.20.135 ibmmq
10.101.20.143 tcp
10.101.20.131 sw
' | sudo tee -a /etc/hosts"
    
    echo "✓ $hostname setup completed"
}

# Check what to do
case "${1:-all}" in
    "test")
        echo "Testing connections..."
        install_sshpass
        echo "$VMS" | while read line; do
            if [ -n "$line" ]; then
                hostname=$(echo $line | cut -d: -f1)
                ip=$(echo $line | cut -d: -f2)
                if ping -c 1 $ip >/dev/null 2>&1; then
                    echo "✓ $hostname ($ip) - OK"
                else
                    echo "✗ $hostname ($ip) - FAILED"
                fi
            fi
        done
        ;;
        
    "ssh")
        echo "Setting up SSH keys..."
        install_sshpass
        
        # Generate SSH key if not exists
        if [ ! -f ~/.ssh/id_ed25519 ]; then
            ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
        fi
        
        # Copy SSH key to all VMs
        echo "$VMS" | while read line; do
            if [ -n "$line" ]; then
                hostname=$(echo $line | cut -d: -f1)
                ip=$(echo $line | cut -d: -f2)
                echo "Copying SSH key to $hostname..."
                sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $USERNAME@$ip
            fi
        done
        ;;
        
    "all")
        echo "Starting complete setup..."
        install_sshpass
        
        # Setup each VM
        echo "$VMS" | while read line; do
            if [ -n "$line" ]; then
                hostname=$(echo $line | cut -d: -f1)
                ip=$(echo $line | cut -d: -f2)
                setup_vm $hostname $ip
            fi
        done
        
        echo "Setup completed! Now rebooting all VMs..."
        
        # Reboot all VMs
        echo "$VMS" | while read line; do
            if [ -n "$line" ]; then
                hostname=$(echo $line | cut -d: -f1)
                ip=$(echo $line | cut -d: -f2)
                echo "Rebooting $hostname..."
                run_on_vm $hostname $ip "sudo reboot" || true
            fi
        done
        
        echo "All VMs are rebooting. Wait 2-3 minutes."
        ;;
        
    *)
        echo "Usage: $0 [test|ssh|all]"
        echo ""
        echo "  test - Test connectivity to all VMs"
        echo "  ssh  - Setup SSH keys"
        echo "  all  - Complete setup (default)"
        echo ""
        echo "Examples:"
        echo "  $0 test    # Test if all VMs are reachable"
        echo "  $0 ssh     # Setup SSH keys"
        echo "  $0 all     # Do everything"
        ;;
esac
