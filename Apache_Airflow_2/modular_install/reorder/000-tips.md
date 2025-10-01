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

**automated SSH host key checking** 

By default, SSH asks you to confirm the first time you connect to a new host (to prevent MITM attacks).
If you want automation to **always accept and skip the prompt**, you need:

---

### 🔹 Method 1: One-shot (command line option)

Add:

```bash
-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
```

Example:

```bash
ssh -i ~/.ssh/id_ed25519_monitoring \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    rocky@rabbit-1
```

* `StrictHostKeyChecking=no` → auto-accepts new host keys.
* `UserKnownHostsFile=/dev/null` → prevents writing host keys into `~/.ssh/known_hosts` (so you don’t get duplicate/warning messages).

---

### 🔹 Method 2: Permanent (in `~/.ssh/config`)

Edit/create `~/.ssh/config` on your control node (monitoring or haproxy-1):

```ssh-config
Host *
    User rocky
    IdentityFile ~/.ssh/id_ed25519_monitoring
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

Now you can just run:

```bash
ssh rabbit-1
```

And it will **never prompt** again.

---

⚠️ Note: this disables host key verification → good for automation in a trusted private network, but risky if machines are exposed to the internet.

---

Got it ✅ — here’s a clear, self-contained explanation you can put in your booklet:

---


# Problem: SSH Host Key Prompts

When connecting to a new server with SSH for the first time, you often see a message like:

```
The authenticity of host 'postgresql-1 (10.101.20.204)' can't be established.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

This happens because SSH does not recognize the server’s **host key** yet. Once you answer `yes`, the server’s key is stored in `~/.ssh/known_hosts`. On later connections, SSH checks this file to verify the server’s identity.

The issue:

* If you only have **IPs** in `known_hosts`, connecting via **hostname** (e.g. `ssh postgresql-1`) will still ask for confirmation.
* If you only have **hostnames**, connecting via raw **IP** (e.g. `ssh 10.101.20.204`) will still ask.

---

### Solution: Preload Host Keys for Both Hostnames and IPs

You can automatically gather host keys with `ssh-keyscan` and store them in your `known_hosts`. To cover both ways of connecting, you must scan **both hostnames and IP addresses**.

Example:

```bash
ssh-keyscan -t ed25519 \
  postgresql-1 10.101.20.204 \
  postgresql-2 10.101.20.166 \
  postgresql-3 10.101.20.137 \
  rabbit-1     10.101.20.205 \
  rabbit-2     10.101.20.147 \
  rabbit-3     10.101.20.206 \
  haproxy-1    10.101.20.202 \
  haproxy-2    10.101.20.146 \
  celery-1     10.101.20.199 \
  celery-2     10.101.20.200 \
  nfs-1        10.101.20.165 \
  nfs-2        10.101.20.203 \
  scheduler-1  10.101.20.132 \
  monitoring   10.101.20.201 \
  ftp          10.101.20.164 \
  informix     10.101.20.159 \
  ibmmq        10.101.20.135 \
  tcp          10.101.20.143 \
  sw           10.101.20.131 \
  > ~/.ssh/known_hosts
```

---

### Result

* `ssh postgresql-1` → works without prompt.
* `ssh 10.101.20.204` → also works without prompt.
* No more “Are you sure you want to continue connecting?” messages across your cluster.

---

👉 This method is ideal for automation (scripts, Ansible, bulk operations), because it **pre-trusts** all your servers by collecting their keys in advance.

---




