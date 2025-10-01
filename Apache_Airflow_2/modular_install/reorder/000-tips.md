* Use **`HAproxy-1` (10.101.20.202)** as the *jump host/controller*.
* Ensure it has **passwordless SSH key access** to all other VMs.
* Run a command (`touch bulk_test_file_create.txt`) in `/home/rocky` across all machines.

---

### 1. On **HAproxy-1** generate SSH keypair (if not already done)

```bash
ssh rocky@10.101.20.202
ssh-keygen -t ed25519 -C "bulk-ops" -f ~/.ssh/id_ed25519
```

Press **Enter** for no passphrase (so automation won’t ask for password).

---

### 2. Copy public key to all VMs

From `HAproxy-1`:

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.201 10.101.20.165 10.101.20.203 \
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

Now from `HAproxy-1`:

```bash
for host in 10.101.20.199 10.101.20.200 10.101.20.164 10.101.20.146 \
            10.101.20.201 10.101.20.165 10.101.20.203 \
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
            10.101.20.201 10.101.20.165 10.101.20.203 \
            10.101.20.204 10.101.20.166 10.101.20.137 \
            10.101.20.205 10.101.20.147 10.101.20.206 \
            10.101.20.132 10.101.20.159 10.101.20.135 \
            10.101.20.143 10.101.20.131; do
    ssh rocky@$host "ls -l /home/rocky/bulk_test_file_create.txt"
done
```

---

