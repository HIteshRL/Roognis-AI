# Roognis MVP — Free Hosting on Oracle Cloud (OCI Always Free)

Deploys **both portals from a single FastAPI process** — no Postgres/Redis/Qdrant, no paid
services. SQLite on disk, HTTPS via Cloudflare Tunnel, optional live Groq LLM. **Total cost: $0.**

| Path | What it serves |
|------|----------------|
| `/` | Student portal — chat tutor + inline check-questions |
| `/teacher` | Teacher LMS — create classrooms, upload PDFs, approve students, review chats |
| `/api/*` | Shared backend (same origin → HTTPS "just works", no CORS) |

Everything (SQLite DB + uploaded PDFs) persists in `student-portal/data/` and survives reboots.

---

## 0. Prerequisites
- An **OCI account** (free signup; a card is used for identity only — Always Free never charges).
- For a **stable URL** (recommended for a scheduled investor demo): a domain added to a **free
  Cloudflare account**. If you skip this, you can still get an instant rotating `*.trycloudflare.com`
  URL with zero account (step 5A).
- Optional: a free **Groq** key (https://console.groq.com) for live LLM answers.

---

## 1. Create the VM (Always Free ARM)
OCI Console → **Compute → Instances → Create instance**:
- **Image:** Canonical Ubuntu **24.04** (make sure the shape below is **aarch64/Arm**)
- **Shape:** `VM.Standard.A1.Flex` → **2 OCPU, 12 GB** (all within Always Free: 4 OCPU / 24 GB)
- **SSH keys:** upload your public key
- Create, then note the **public IP**.

> **"Out of host capacity"?** A1 is popular. Try another Availability Domain, switch region, or
> retry later. As a last resort the AMD `VM.Standard.E2.1.Micro` (1 GB) also runs the offline demo.

No load balancer, no extra networking needed — Cloudflare Tunnel makes the outbound connection, so
you never open ports 80/443 or touch OCI Security Lists / iptables.

---

## 2. SSH in and clone
```bash
ssh ubuntu@<PUBLIC_IP>
sudo apt-get update -y && sudo apt-get install -y git
git clone -b feat/learner-intelligence-inline-questions https://github.com/HIteshRL/Roognis-AI.git
cd Roognis-AI
```

## 3. Deploy (one command)
```bash
sudo bash deploy/oci/deploy.sh
```
Installs Python deps into a venv, registers the app as a **systemd** service (auto-restart + starts
on boot), and installs `cloudflared`. Verify it's up locally:
```bash
curl -s http://127.0.0.1:5050/api/curriculum | head -c 200; echo
```

## 4. (Optional) Turn on live LLM answers
```bash
nano deploy/oci/.env        # set GROQ_API_KEY=gsk_...
sudo systemctl restart roognis-portal
```
Without a key it runs **offline** (answers extracted from chapter text) — still fully functional.

## 5. Put it on HTTPS with Cloudflare Tunnel

### 5A. Instant — no account (URL rotates each run)
```bash
cloudflared tunnel --url http://localhost:5050
```
Prints `https://<random>.trycloudflare.com`. Great for a quick share; run inside `tmux`/`screen`
so it stays alive. The URL changes if you restart it.

### 5B. Stable URL — recommended (needs a domain on Cloudflare)
```bash
cloudflared tunnel login                         # browser: authorize your Cloudflare domain
cloudflared tunnel create roognis                # note the Tunnel ID it prints
mkdir -p ~/.cloudflared
cp deploy/oci/cloudflared-config.example.yml ~/.cloudflared/config.yml
nano ~/.cloudflared/config.yml                   # set credentials-file (Tunnel ID) + your hostname
cloudflared tunnel route dns roognis demo.yourdomain.com

sudo cp deploy/oci/roognis-tunnel.service /etc/systemd/system/
sudo sed -i "s/__USER__/$USER/" /etc/systemd/system/roognis-tunnel.service
sudo systemctl daemon-reload && sudo systemctl enable --now roognis-tunnel
```
Now **https://demo.yourdomain.com** is live, auto-starting, and stable.

---

## 6. Demo script (for investors / clients)
1. Open **https://<your-url>/teacher** → create a classroom → add a chapter → upload a chapter PDF.
2. Open **https://<your-url>/** → pick that class → ask a question → the tutor answers from the PDF.
3. A **"Quick check"** bubble appears → type an answer → instant ✓ / ≈ / ↻ feedback.
   That feedback + confidence update *is* the Learner Intelligence engine capturing evidence.

---

## Ops cheatsheet
```bash
journalctl -u roognis-portal -f          # app logs (live)
journalctl -u roognis-tunnel -f          # tunnel logs
sudo systemctl restart roognis-portal    # restart app
git pull && sudo systemctl restart roognis-portal   # deploy an update
```
- **Data**: `student-portal/data/roognis.db` + uploaded PDFs — persist across reboots.
- **Backup**: copy that file to OCI Object Storage (10 GB free) any time.

## Why it's free (and stays free)
| Resource | Always Free allowance | This demo uses |
|----------|----------------------|----------------|
| Compute | 4 OCPU / 24 GB Ampere A1, forever | 2 OCPU / 12 GB |
| Storage | 200 GB block volumes | ~a few GB |
| Egress | 10 TB/month | negligible |
| Cloudflare Tunnel | free | HTTPS + public URL |
| Groq | free tier | live LLM (optional) |
