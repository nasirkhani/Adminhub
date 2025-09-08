To change your static IP address on Red Hat 9 in a VMware virtual machine, you need to edit the NetworkManager configuration file for your network interface.

### Steps to Change the IP Address

1.  **Identify your network interface.**
    Your network interface is **ens160**, as shown in the output of the `ip a` command.

2.  **Edit the NetworkManager configuration file.**
    You'll need root privileges to edit this file. Use a text editor like `vi` or `nano`. The file path is typically `/etc/NetworkManager/system-connections/`. The specific filename will be something like `ens160.nmconnection`.
    First, find the exact filename:

    ```bash
    [rocky@postgresql-1 ~]$ ls /etc/NetworkManager/system-connections/
    ```

    Once you have the filename, open it for editing. For this example, let's assume the filename is `ens160.nmconnection`.

    ```bash
    [rocky@postgresql-1 ~]$ sudo vi /etc/NetworkManager/system-connections/ens160.nmconnection
    ```

    Enter your password when prompted.

3.  **Modify the configuration.**
    In the file, find the `[ipv4]` section. You'll need to change the method from `auto` (which uses DHCP) to `manual` and then add the new address.

    Change this line:

    ```
    method=auto
    ```

    to this:

    ```
    method=manual
    ```

    Next, add the new IP address, gateway, and DNS server information. Below the `method=manual` line, add these three lines:

    ```
    address1=192.168.230.133/24,192.168.230.2
    dns=8.8.8.8;8.8.4.4;
    ```

    **Note:** The gateway IP address for a VMware NAT network is typically the host's IP address on the virtual network. In your case, it's likely **192.168.230.2**. You can confirm this by checking the **VMware Virtual Ethernet Adapter for VMnet8 (NAT)** settings on your host machine. The `/24` after the IP address specifies the subnet mask (255.255.255.0).

4.  **Save and close the file.**
    If you're using `vi`, press `Esc`, then type `:wq` and press `Enter`.

5.  **Restart the NetworkManager service.**
    After saving the changes, you need to restart the NetworkManager service to apply the new configuration.

    ```bash
    [rocky@postgresql-1 ~]$ sudo systemctl restart NetworkManager
    ```

6.  **Verify the new IP address.**
    Finally, check your IP address again using the `ip a` command to confirm that it has been updated to **192.168.230.133**.

    ```bash
    [rocky@postgresql-1 ~]$ ip a
    ```

    The output for `ens160` should now show your new static IP address.




    =============================================================================================

    The reason you still have both IP addresses is that NetworkManager's configuration for the **ens160** interface is likely stored in two places: the file you edited and an alternative file with the same interface name. This often happens because NetworkManager keeps a connection file for the original DHCP setup, and creating a new static configuration doesn't automatically remove the old one.

To remove the old IP address, you need to either disable the old connection profile or ensure only the static configuration is active. The most straightforward method is to delete or move the old connection file.

1.  **Stop the NetworkManager service.**
    Before making changes, it's a good practice to stop the service.

    ```bash
    [rocky@postgresql-1 ~]$ sudo systemctl stop NetworkManager
    ```

2.  **Delete or rename the old connection profile.**
    Your previous configuration, which was likely managed by NetworkManager, is still active. There might be another file with a different UUID, or the current file has some lingering settings. A simple way to ensure a clean slate is to remove or rename the connection file you're using and then recreate it.

    First, **back up your current configuration file**:

    ```bash
    [rocky@postgresql-1 ~]$ sudo mv /etc/NetworkManager/system-connections/ens160.nmconnection /etc/NetworkManager/system-connections/ens160.nmconnection.bak
    ```

    Then, create a new file with the clean configuration. Use a text editor like `vi` or `nano`:

    ```bash
    [rocky@postgresql-1 ~]$ sudo vi /etc/NetworkManager/system-connections/ens160.nmconnection
    ```

    Add the following content to this new file:

    ```ini
    [connection]
    id=ens160
    type=ethernet
    interface-name=ens160

    [ethernet]

    [ipv4]
    method=manual
    address1=192.168.230.133/24,192.168.230.2

    [ipv6]
    addr-gen-mode=eui64
    method=auto

    [proxy]
    ```

    Save and close the file.

3.  **Set the correct permissions.**
    NetworkManager connection files must be readable by the root user only.

    ```bash
    [rocky@postgresql-1 ~]$ sudo chmod 600 /etc/NetworkManager/system-connections/ens160.nmconnection
    ```

4.  **Restart the NetworkManager service.**

    ```bash
    [rocky@postgresql-1 ~]$ sudo systemctl start NetworkManager
    ```

5.  **Verify the new IP address.**
    Check the IP address again. The old IP address should now be gone.

    ```bash
    [rocky@postgresql-1 ~]$ ip a
    ```

    This process ensures that NetworkManager is using a single, clean configuration file, preventing the old DHCP-assigned IP from being re-added.



    
