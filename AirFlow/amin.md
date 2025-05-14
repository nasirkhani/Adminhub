Excellent question — and this is a subtle but important distinction.

Let’s clear it up:

---

## 🔍 You're asking:

> “If these are system-wide services, why do they all depend on the `rocky` user’s home directory? Shouldn’t a system-wide service be user-independent?”

---

## ✅ Short Answer:

**Yes, it's perfectly OK.**
Your services **are system-wide** because `systemd` manages them globally, **but they are configured to run under a specific user (`rocky`)** and use that user’s environment (home directory, paths, etc.).

This is common and **not a problem** — many system-wide services are run by specific, non-root users (e.g., `postgres`, `nginx`, `airflow`).

---

## 📌 To be crystal clear:

| Characteristic              | Your setup                                                 |
| --------------------------- | ---------------------------------------------------------- |
| Managed by systemd globally | ✅ Yes (`/etc/systemd/system/*.service`)                    |
| Autostarts on boot          | ✅ Yes (`systemctl enable`)                                 |
| Uses specific user          | ✅ Yes (`User=rocky`)                                       |
| Airflow installed globally  | ❌ No — it's installed for `rocky` via `pip install --user` |
| Problem?                    | ❌ No — totally valid                                       |

---

## 🧠 Bonus: Could I install Airflow *system-wide*?

Yes, you **could** do a truly "global" install with:

```bash
sudo pip3 install apache-airflow
```

But:

* This pollutes the system Python environment.
* Is harder to manage across users or isolate per project.
* Often considered bad practice unless containerizing or tightly controlled.

---

## ✅ Recommended Approach (What you're doing now):

* Install Airflow **per-user** (safer, cleaner).
* Run services **as that user**.
* Use `systemd` for full lifecycle and boot integration.

You’ve done it **correctly** and this pattern is commonly used in real-world Airflow deployments on bare-metal or VM setups.

---

Let me know if you'd like:

* To migrate Airflow to a virtualenv or global path
* To isolate config/logs under `/opt/airflow` instead of `~/airflow`
* A security hardening guide for this setup

You're on solid ground — great job asking the right questions!
