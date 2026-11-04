#!/usr/bin/env bash
# One-shot installer for the GPU node agent. Run on the node:
#   curl -fsSL https://raw.githubusercontent.com/amai-gsu/amai-gpu-scheduler/main/agent/install.sh | sudo bash -s ada6000
# It downloads report.py, asks for a GitHub token (classic, scope public_repo), checks it,
# stores it in /opt/gpu-scheduler/config (root-only), runs one report, and registers a root cron
# job every 30 minutes. Re-running replaces the old cron line and config.
set -euo pipefail
NODE="${1:-}"
if [ -z "$NODE" ]; then echo "usage: install.sh <node id, e.g. ada6000 or lab2>"; exit 1; fi
if [ "$(id -u)" != "0" ]; then echo "please run with sudo"; exit 1; fi
DIR=/opt/gpu-scheduler
RAW=https://raw.githubusercontent.com/amai-gsu/amai-gpu-scheduler/main/agent
mkdir -p "$DIR"
curl -fsSL "$RAW/report.py" -o "$DIR/report.py"
chmod 755 "$DIR/report.py"
PY="$(command -v python3)"
command -v nvidia-smi >/dev/null || { echo "nvidia-smi not found on this machine"; exit 1; }

TOKEN=""
if [ -f "$DIR/config" ]; then . "$DIR/config"; TOKEN="${GPU_SCHED_TOKEN:-}"; fi
check() { curl -fsS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $1" https://api.github.com/user 2>/dev/null || true; }
if [ -n "$TOKEN" ] && [ "$(check "$TOKEN")" = "200" ]; then
  echo "Using the token already stored in $DIR/config"
else
  echo
  echo "Create a GitHub token (classic) with only the 'public_repo' scope here:"
  echo "  https://github.com/settings/tokens/new?scopes=public_repo&description=gpu-agent-$NODE"
  echo "then paste it below (it starts with ghp_). It is stored in $DIR/config, readable by root only."
  while :; do
    printf 'Token: '; read -r TOKEN < /dev/tty
    TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"
    case "$TOKEN" in ghp_*|github_pat_*) ;; *) echo "That does not look like a GitHub token (should start with ghp_). Try again."; continue;; esac
    if [ "$(check "$TOKEN")" = "200" ]; then break; fi
    echo "GitHub rejected that token (HTTP $(check "$TOKEN")). Check it was copied completely and try again."
  done
fi
umask 077
printf 'GPU_SCHED_TOKEN=%s\nGPU_SCHED_NODE=%s\n' "$TOKEN" "$NODE" > "$DIR/config"
chmod 600 "$DIR/config"

echo "Running one report now..."
GPU_SCHED_TOKEN="$TOKEN" "$PY" "$DIR/report.py" "$NODE"

LINE="*/30 * * * * . $DIR/config && GPU_SCHED_TOKEN=\$GPU_SCHED_TOKEN $PY $DIR/report.py $NODE >> /var/tmp/gpu-report.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'gpu-scheduler/report.py' || true; echo "$LINE" ) | crontab -
echo
echo "Installed. Cron (root) will report every 30 minutes:"
crontab -l | grep gpu-scheduler
echo "Log: /var/tmp/gpu-report.log"
