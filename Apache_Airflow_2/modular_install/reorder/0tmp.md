sudo rm -f /usr/local/bin/etcd*

sudo rm -f /etc/systemd/system/etcd.service
sudo rm -rf /var/lib/etcd
sudo rm -rf /etc/etcd
sudo userdel etcd
sudo groupdel etcd

# On all three nodes
sudo rm -rf /var/lib/pgsql/16/data

# On all three nodes



=====================


sudo chown -R etcd:etcd /var/lib/etcd
sudo mv /var/lib/etcd /var/lib/etcd_backup
sudo mkdir /var/lib/etcd
sudo chown -R etcd:etcd /var/lib/etcd

sudo mkdir -p /var/lib/etcd
sudo chown -R etcd:etcd /var/lib/etcd

sudo systemctl status etcd.service
