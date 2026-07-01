#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STATE_DIR="results/casmi_full_completion_audit_v1"
LOG_DIR="$STATE_DIR/logs"
PID_FILE="$STATE_DIR/cfmid_full_supported_until_complete.pid"
LOG_PATH_FILE="$STATE_DIR/cfmid_full_supported_until_complete.log_path"
mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "$old_pid" ]] && ps -p "$old_pid" >/dev/null 2>&1; then
    echo "already_running pid=$old_pid"
    cat "$LOG_PATH_FILE" 2>/dev/null || true
    exit 0
  fi
fi

ts="$(date +%Y%m%d_%H%M%S)"
log="$LOG_DIR/cfmid_full_supported_until_complete.${ts}.log"
nohup bash scripts/run_cfmid_full_supported_until_complete.sh > "$log" 2>&1 &
pid="$!"
echo "$pid" > "$PID_FILE"
echo "$log" > "$LOG_PATH_FILE"
echo "started pid=$pid"
echo "log=$log"
