I'd be happy to rewrite this RabbitMQ cluster installation guide specifically for Rocky Linux 9 instead of Ubuntu. I'll go through the process step by step.

# How to Install RabbitMQ Cluster on Rocky Linux 9

## Getting Started

Before starting, you will need to update your system packages to the latest version on each node:

```bash
sudo dnf update -y
```

Next, set up the `/etc/hosts` file on each node so they can communicate with each other by hostname:

```bash
sudo vim /etc/hosts
```

Add the following lines (adjust IP addresses according to your environment):

```
192.168.0.10 node1
192.168.0.11 node2
192.168.0.12 node3
```

Save and close the file.

## Install Dependencies

First, you'll need to install the EPEL repository and required dependencies on each node:

```bash
sudo dnf install epel-release -y
sudo dnf config-manager --set-enabled crb
sudo dnf install wget socat logrotate -y
```

## Install Erlang

RabbitMQ requires Erlang to run. Let's install it on each node:

```bash
# Add Erlang repository
sudo dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
sudo dnf install -y https://github.com/rabbitmq/erlang-rpm/releases/download/v25.0.3/erlang-25.0.3-1.el9.x86_64.rpm
```

Verify Erlang installation:

```bash
erl -version
```

## Install RabbitMQ Server

Now let's install RabbitMQ server on each node:

```bash
# Download and install RabbitMQ RPM
wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.11.0/rabbitmq-server-3.11.0-1.el9.noarch.rpm
dnf install ./rabbitmq-server-3.11.0-1.el9.noarch.rpm -y
```

Start the RabbitMQ service and enable it to start at system reboot on each node:

```bash
systemctl start rabbitmq-server
systemctl enable rabbitmq-server
```

Verify the status of the RabbitMQ service:

```bash
systemctl status rabbitmq-server
```

You should see output indicating that RabbitMQ is active and running.

## Enable RabbitMQ Management Plugin

The RabbitMQ management plugin provides an HTTP-based API for monitoring and managing RabbitMQ nodes through a web browser. Enable it on each node:

```bash
rabbitmq-plugins enable rabbitmq_management
```

Restart the RabbitMQ service to apply the changes:

```bash
systemctl restart rabbitmq-server
```
```bash
sudo rabbitmqctl add_user admin "QAZzaq@123"
sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags admin administrator
```
Verify the listening port with:

```bash
ss -tunelp | grep 15672
```

You should see output showing that port 15672 is open and listening.

## Configure Firewall (Optional)

If you're using firewalld (which is common on Rocky Linux), you'll need to open the required ports:

```bash
# Open RabbitMQ ports
firewall-cmd --permanent --add-port=5672/tcp  # AMQP
firewall-cmd --permanent --add-port=15672/tcp # Management UI
firewall-cmd --permanent --add-port=25672/tcp # Inter-node communication
firewall-cmd --reload
```

## Setup RabbitMQ Cluster

By default, the `/var/lib/rabbitmq/.erlang.cookie` file should be the same on each node for clustering to work. Copy this file from node1 to other nodes:

On node1, check the cookie:

```bash
cat /var/lib/rabbitmq/.erlang.cookie
```

Make sure you note this value. Then on each of node2 and node3:

1. Stop the RabbitMQ service:
   ```bash
   systemctl stop rabbitmq-server
   ```

2. Set the same cookie value:
   ```bash
   echo "COOKIE_VALUE_FROM_NODE1" > /var/lib/rabbitmq/.erlang.cookie
   ```

3. Fix the permissions:
   ```bash
   chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
   chmod 400 /var/lib/rabbitmq/.erlang.cookie
   ```

4. Start the service again:
   ```bash
   systemctl start rabbitmq-server
   ```

Alternatively, you can copy the file directly from node1 to the other nodes using scp:

```bash
# On node1
scp /var/lib/rabbitmq/.erlang.cookie root@192.168.0.11:/var/lib/rabbitmq/
scp /var/lib/rabbitmq/.erlang.cookie root@192.168.0.12:/var/lib/rabbitmq/
```

Then on both node2 and node3, fix permissions and restart:

```bash
chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
chmod 400 /var/lib/rabbitmq/.erlang.cookie
systemctl restart rabbitmq-server
```

Now, let's set up node2 and node3 to join the cluster with node1:

On node2:
```bash
# Stop the RabbitMQ application
rabbitmqctl stop_app

# Join the cluster with node1
rabbitmqctl join_cluster rabbit@node1

# Start the RabbitMQ application
rabbitmqctl start_app
```

On node3:
```bash
# Stop the RabbitMQ application
rabbitmqctl stop_app

# Join the cluster with node1
rabbitmqctl join_cluster rabbit@node1

# Start the RabbitMQ application
rabbitmqctl start_app
```

Check the status of the cluster from node1:
```bash
rabbitmqctl cluster_status
```

You should see all three nodes listed in the output.

## Setup Administrator User

Create a new admin user and remove the default 'guest' user:

On node1:
```bash
# Add new admin user (change 'password' to a secure password)
rabbitmqctl add_user admin password

# Set administrator tag
rabbitmqctl set_user_tags admin administrator

# Grant permissions
rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"

# Delete default guest user
rabbitmqctl delete_user guest
```

Verify the user list:
```bash
rabbitmqctl list_users
```

The admin user you created on node1 will be automatically replicated to all nodes in the cluster.

## Configure Queue Mirroring

Set up high availability policies for queue mirroring:

1. Create a policy for mirroring all queues to all nodes:
```bash
rabbitmqctl set_policy ha-all ".*" '{"ha-mode":"all"}'
```

2. Create a policy for mirroring queues with names starting with "two." to exactly two nodes:
```bash
rabbitmqctl set_policy ha-two "^two\." '{"ha-mode":"exactly","ha-params":2,"ha-sync-mode":"automatic"}'
```

3. Create a policy for mirroring queues with names starting with "nodes." to specific nodes:
```bash
rabbitmqctl set_policy ha-nodes "^nodes\." '{"ha-mode":"nodes","ha-params":["rabbit@node2", "rabbit@node3"]}'
```

List all policies:
```bash
rabbitmqctl list_policies
```

## Access RabbitMQ Management Interface

You can now access the RabbitMQ web interface by typing the IP address of any node in your web browser with port 15672:
```
http://192.168.0.10:15672/
```

Log in with the admin user credentials you created earlier.

## Troubleshooting Tips for Rocky Linux 9

If you encounter issues, here are some troubleshooting steps specific to Rocky Linux:

1. Check SELinux status:
```bash
sestatus
```

If SELinux is enforcing, you may need to create appropriate policies or temporarily set it to permissive mode:
```bash
setenforce 0  # Temporary until reboot
```

For a permanent change, edit `/etc/selinux/config` and set `SELINUX=permissive`.

2. Check system logs:
```bash
journalctl -u rabbitmq-server
```

3. Verify connectivity between nodes:
```bash
ping node1  # From node2 and node3
```

4. Make sure all required ports are open:
```bash
ss -tulpn | grep -E '5672|15672|25672'
```

## Summary

You've now successfully set up a RabbitMQ cluster on Rocky Linux 9. This setup includes:

1. Installation of RabbitMQ and its dependencies
2. Configuration of a three-node cluster
3. Setup of management interfaces
4. Creation of an administrator user
5. Configuration of high availability policies for queue mirroring

Your RabbitMQ cluster is now ready for production use. Remember to secure your installation further by implementing SSL/TLS for encrypted connections if required for your environment.
