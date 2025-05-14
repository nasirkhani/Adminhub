#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root."
    exit 1
fi

# Function to check exit status
check_status() {
    if [ $? -ne 0 ]; then
        echo "$1"
        exit 1
    fi
}

# Check and configure DNS
check_dns() {
    read -p "Enter Active Directory domain (e.g., example.com): " DOMAIN
    echo -e "\nChecking DNS configuration..."
    
    # Check domain controller resolution
    if ! host -t srv _ldap._tcp."$DOMAIN" >/dev/null 2>&1; then
        echo "ERROR: Failed to resolve domain controllers for $DOMAIN"
        echo "Verify DNS configuration matches these requirements:"
        echo "- Client DNS server should point to AD DNS servers"
        echo "- Forward and reverse zones should be properly configured"
        exit 1
    fi
    
    echo "DNS configuration appears valid"
}

# Check and configure time synchronization
check_time_sync() {
    echo -e "\nChecking time synchronization..."
    if ! systemctl is-active --quiet chronyd && ! systemctl is-active --quiet ntpd; then
        read -p "Time service not running. Install and configure NTP? [y/N]: " INSTALL_NTP
        if [[ "$INSTALL_NTP" =~ [yY] ]]; then
            if command -v apt &> /dev/null; then
                apt install -y chrony
                systemctl enable --now chrony
            elif command -v yum &> /dev/null; then
                yum install -y chrony
                systemctl enable --now chronyd
            fi
            sleep 2
            echo "Current time: $(date)"
            echo "NTP servers:"
            chronyc sources || ntpq -p
        else
            echo "Time synchronization is required for AD integration"
            exit 1
        fi
    fi
    
    # Verify time difference
    MAX_TIME_DIFF=300  # 5 minutes in seconds
    AD_TIME=$(host -t time "$DOMAIN" | awk '{print $6}' | tr -d '\n')
    if [ -n "$AD_TIME" ]; then
        LOCAL_TIME=$(date +%s)
        TIME_DIFF=$((AD_TIME - LOCAL_TIME))
        if [ ${TIME_DIFF#-} -gt $MAX_TIME_DIFF ]; then
            echo "ERROR: Time difference exceeds allowed threshold (5 minutes)"
            echo "Local time: $(date -d @$LOCAL_TIME)"
            echo "AD time:    $(date -d @$AD_TIME)"
            exit 1
        fi
    fi
    echo "Time synchronization verified"
}

# Install required packages
install_packages() {
    echo -e "\nInstalling required packages..."
    if command -v apt &> /dev/null; then
        apt update
        apt install -y realmd sssd sssd-tools libnss-sss libpam-sss adcli samba-common-bin krb5-user
    elif command -v yum &> /dev/null; then
        yum install -y realmd sssd adcli krb5-workstation samba-common-tools oddjob-mkhomedir
    else
        echo "Unsupported package manager"
        exit 1
    fi
    check_status "Failed to install required packages"
}

# Join domain
join_domain() {
    read -p "Enter AD admin username: " ADMIN_USER
    read -s -p "Enter AD admin password: " ADMIN_PASSWORD
    echo
    
    echo -e "\nJoining domain..."
    echo "$ADMIN_PASSWORD" | kinit "$ADMIN_USER@${DOMAIN^^}"
    check_status "Kerberos authentication failed"
    
    realm join -v "$DOMAIN"
    check_status "Failed to join domain"
}

# Configure SSSD and permissions
configure_sssd() {
    echo -e "\nConfiguring SSSD..."
    SSSD_CONF="/etc/sssd/sssd.conf"
    
    # Backup original config
    cp "$SSSD_CONF" "${SSSD_CONF}.bak"
    
    # Configure settings
    sed -i "s/use_fully_qualified_names = .*/use_fully_qualified_names = False/" "$SSSD_CONF"
    sed -i "/^\[domain\/${DOMAIN}\]/a override_homedir = /home/%u\ndefault_shell = /bin/bash" "$SSSD_CONF"
    
    # Verify permissions
    chmod 600 "$SSSD_CONF"
    if [ $(stat -c %a "$SSSD_CONF") -ne 600 ]; then
        echo "ERROR: SSSD configuration file permissions not set to 600"
        exit 1
    fi
    echo "SSSD configuration validated"
}

# Configure PAM and automatic home creation
configure_pam() {
    echo -e "\nConfiguring PAM..."
    PAM_FILE="/etc/pam.d/common-session"
    if [ ! -f "$PAM_FILE" ]; then
        PAM_FILE="/etc/pam.d/system-auth"
    fi
    
    if ! grep -q "pam_mkhomedir" "$PAM_FILE"; then
        echo "session required pam_mkhomedir.so skel=/etc/skel umask=0077" >> "$PAM_FILE"
        echo "Added home directory auto-creation to PAM config"
    else
        echo "PAM home directory configuration already exists"
    fi
}

# Configure sudo access
configure_sudo() {
    read -p "Enter AD group for sudo access (leave empty to skip): " SUDO_GROUP
    if [ -n "$SUDO_GROUP" ]; then
        SUDO_FILE="/etc/sudoers.d/ad-sudoers"
        echo "%${SUDO_GROUP}@${DOMAIN} ALL=(ALL) ALL" > "$SUDO_FILE"
        chmod 440 "$SUDO_FILE"
        if [ $(stat -c %a "$SUDO_FILE") -ne 440 ]; then
            echo "ERROR: Sudoers file permissions not set to 440"
            exit 1
        fi
        visudo -c -q || { echo "Invalid sudoers configuration"; exit 1; }
        echo "Sudo access configured for $SUDO_GROUP"
    fi
}

# Verification checks
verify_join() {
    echo -e "\nRunning verification checks..."
    
    echo -e "\n1. Checking realm list:"
    realm list
    check_status "Failed to verify domain membership"
    
    echo -e "\n2. Testing user lookup:"
    read -p "Enter AD test username: " TEST_USER
    id "$TEST_USER"
    check_status "User lookup failed"
    
    echo -e "\n3. Checking SSSD status:"
    systemctl status sssd
    check_status "SSSD service not running properly"
    
    echo -e "\nAll verification checks passed!"
}

# Main execution
check_dns
check_time_sync
install_packages
join_domain
configure_sssd
configure_pam
configure_sudo

systemctl restart sssd

verify_join

echo -e "\nDomain join completed successfully!"
echo "Users can log in with their AD credentials"






# Verify authentication: su - ad_username
# Review SSSD logs if needed: journalctl -u sssd