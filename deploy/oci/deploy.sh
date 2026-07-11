#!/usr/bin/env bash
#
# Roognis MVP — one-command deploy for OCI Always Free (Ampere A1 / Ubuntu 24.04 aarch64).
#
# Serves BOTH portals from a single FastAPI process backed by SQLite:
#     /          student portal (modular UI + inline check-questions)
#     /teacher   teacher LMS (create classrooms, upload PDFs, approve students)
#
# Runs fully offline out of the box; set GROQ_API_KEY in deploy/oci/.env for live LLM answers.
#
# Usage (on the VM, from the repo root):
#     sudo bash deploy/oci/deploy.sh
#
set -euo pipefail

PORT="${PORT:-5050}"
RUN_USER="${SUDO_USER:-$(id -un)}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="$REPO_DIR/.venv"
ENV_FILE="$REPO_DIR/deploy/oci/.env"

echo "==> Repo:  $REPO_DIR"
echo "==> User:  $RUN_USER"
echo "==> Port:  $PORT (bound to 127.0.0.1; Cloudflare Tunnel fronts it over HTTPS)"

# 1) System packages (Ubuntu 24.04 ships Python 3.12 as python3) ---------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl
echo "==> python3 = $(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"

# 2) Virtualenv + dependencies (every dep ships an aarch64 wheel) --------------
sudo -u "$RUN_USER" python3 -m venv "$VENV"
sudo -u "$RUN_USER" "$VENV/bin/pip" install --upgrade pip wheel
sudo -u "$RUN_USER" "$VENV/bin/pip" install -r "$REPO_DIR/student-portal/requirements.txt"
sudo -u "$RUN_USER" "$VENV/bin/pip" install -r "$REPO_DIR/rag-standalone/requirements.txt"

# 3) Persistent data dir (SQLite DB + uploaded PDFs live here) -----------------
sudo -u "$RUN_USER" mkdir -p "$REPO_DIR/student-portal/data"

# 4) Env file (Groq key etc.) — created once from the example ------------------
if [ ! -f "$ENV_FILE" ]; then
  cp "$REPO_DIR/deploy/oci/.env.example" "$ENV_FILE"
  chown "$RUN_USER:$RUN_USER" "$ENV_FILE"
  echo "==> Created $ENV_FILE — add GROQ_API_KEY there for live LLM answers (optional)."
fi

# 5) systemd unit — auto-restart, starts on boot, one worker (SQLite-safe) -----
cat >/etc/systemd/system/roognis-portal.service <<UNIT
[Unit]
Description=Roognis MVP — student + teacher portal (FastAPI + SQLite)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$REPO_DIR/student-portal
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/uvicorn app:app --host 127.0.0.1 --port $PORT --workers 1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now roognis-portal.service
sleep 2
systemctl --no-pager --full status roognis-portal.service | head -n 12 || true

# 6) cloudflared (Cloudflare Tunnel) ------------------------------------------
if ! command -v cloudflared >/dev/null 2>&1; then
  ARCH="$(dpkg --print-architecture)"   # arm64 on Ampere A1
  echo "==> Installing cloudflared ($ARCH)…"
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb" -o /tmp/cloudflared.deb
  apt-get install -y /tmp/cloudflared.deb
fi

echo
echo "======================================================================"
echo " App is live locally:  http://127.0.0.1:$PORT"
echo "   student  ->  /          teacher  ->  /teacher"
echo " Verify:   curl -s http://127.0.0.1:$PORT/api/curriculum | head -c 200; echo"
echo
echo " Next — put it on HTTPS with Cloudflare Tunnel:"
echo "   A) Instant, no account (URL rotates each run):"
echo "        cloudflared tunnel --url http://localhost:$PORT"
echo "   B) Stable URL (needs a domain on Cloudflare): see deploy/oci/README.md step 5B"
echo "======================================================================"
