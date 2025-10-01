# option 1 : set up monitoring to access all other vms. (use option 2 for more automated if you can)

* Use **`monitoring` (10.101.20.201)** as the *jump host/controller*.
* Ensure it has **passwordless SSH key access** to all other VMs.
* Run a command (`touch bulk_test_file_create.txt`) in `/home/rocky` across all machines.

---
### 1. On **monitoring** generate SSH keypair (if not already done)

```bash
ssh rocky@10.101.20.201
ssh-keygen -t ed25519 -C "bulk-ops" -f ~/.ssh/id_ed25519
```

Press **Enter** for no passphrase (so automation won’t ask for password).

---

### 2. Copy public key to all VMs

From `HAproxy-1`:

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.202 10.101.20.165 10.101.20.203 \
            10.101.20.204 10.101.20.166 10.101.20.137 \
            10.101.20.205 10.101.20.147 10.101.20.206 \
            10.101.20.132 10.101.20.159 10.101.20.135 \
            10.101.20.143 10.101.20.131; do
    ssh-copy-id -i ~/.ssh/id_ed25519.pub rocky@$host
done
```

⚠️ This will prompt you for the password of `rocky` on each VM once. After that, passwordless login works.

---

### 3. Run the bulk command

Now from `monitoring`:

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.202 10.101.20.165 10.101.20.203 \
            10.101.20.204 10.101.20.166 10.101.20.137 \
            10.101.20.205 10.101.20.147 10.101.20.206 \
            10.101.20.132 10.101.20.159 10.101.20.135 \
            10.101.20.143 10.101.20.131; do
    echo "Running on $host..."
    ssh rocky@$host "cd /home/rocky && touch bulk_test_file_create.txt"
done
```

---

### 4. Optional: Verify file creation

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.202 10.101.20.165 10.101.20.203 \
            10.101.20.204 10.101.20.166 10.101.20.137 \
            10.101.20.205 10.101.20.147 10.101.20.206 \
            10.101.20.132 10.101.20.159 10.101.20.135 \
            10.101.20.143 10.101.20.131; do
    ssh rocky@$host "ls -l /home/rocky/bulk_test_file_create.txt"
done
```

# option 2 : more automated
---


By default, `ssh-copy-id` is interactive:

* First time → asks “Are you sure you want to continue connecting (yes/no)?”
* Then → asks for the password.

Since you have **the same password (`111`) on all nodes**, you can fully automate it with **`sshpass`**.

---

### 🔹 1. Install `sshpass` (on monitoring)

```bash
sudo dnf install -y sshpass
```

---

### 🔹 2. Run automated loop

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.202 10.101.20.165 10.101.20.203 \
            10.101.20.204 10.101.20.166 10.101.20.137 \
            10.101.20.205 10.101.20.147 10.101.20.206 \
            10.101.20.132; do
    echo ">>> Copying key to $host"
    sshpass -p '111' ssh-copy-id -i ~/.ssh/id_ed25519.pub -o StrictHostKeyChecking=no rocky@$host
done
```

* `sshpass -p '111'` → feeds password automatically.
* `-o StrictHostKeyChecking=no` → auto-accepts the first-time “yes/no” prompt.

---


