#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STATE_DIR="results/casmi_full_completion_audit_v1"
PID_FILE="$STATE_DIR/cfmid_full_supported_until_complete.pid"
LOG_PATH_FILE="$STATE_DIR/cfmid_full_supported_until_complete.log_path"

if [[ ! -f "$PID_FILE" ]]; then
  echo "not_started"
  exit 0
fi

pid="$(cat "$PID_FILE")"
log="$(cat "$LOG_PATH_FILE" 2>/dev/null || true)"
if ps -p "$pid" >/dev/null 2>&1; then
  echo "running pid=$pid"
  ps -p "$pid" -o pid,etime,cmd
else
  echo "not_running pid=$pid"
fi

if [[ -n "$log" ]]; then
  echo "log=$log"
  if [[ -f "$log" ]]; then
    tail -40 "$log"
  else
    echo "log_missing"
  fi
fi
