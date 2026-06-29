#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/results/logs"
FULL_LOG="${LOG_DIR}/native_tool_setup_full.log"
COMPAT_LOG="${LOG_DIR}/native_baseline_install.log"
AUDIT_JSON="${ROOT_DIR}/results/native_tool_ready_audit.json"
AUDIT_CSV="${ROOT_DIR}/results/native_tool_ready_audit.csv"
mkdir -p "${LOG_DIR}" "${ROOT_DIR}/results"
export ROOT_DIR AUDIT_JSON AUDIT_CSV

exec > >(tee "${FULL_LOG}" "${COMPAT_LOG}") 2>&1

echo "# Native baseline setup and readiness audit"
date -Is
echo "root=${ROOT_DIR}"
echo "hostname=$(hostname)"
echo "python=$(command -v python3 || true)"
echo

python3 - <<'PY_AUDIT'
from __future__ import annotations

import csv
import importlib.metadata as metadata
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
audit_json = Path(os.environ["AUDIT_JSON"])
audit_csv = Path(os.environ["AUDIT_CSV"])
timestamp = datetime.now(timezone.utc).isoformat()


def run(command: list[str], timeout: int = 20) -> dict[str, object]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": repr(exc)}


def first_existing(candidates: list[str | None]) -> str:
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def package_version(name: str) -> str:
    if importlib.util.find_spec(name) is None:
        return ""
    try:
        return metadata.version(name)
    except Exception:
        module = __import__(name)
        return str(getattr(module, "__version__", ""))


def compact_version(probe: dict[str, object], fallback: str = "") -> str:
    text = "\n".join(str(probe.get(k, "")) for k in ["stdout", "stderr"]).strip()
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:240]
    return fallback


def mkrow(tool: str, available: bool, executable_path: str, version: str, install_method: str, probe: dict[str, object], blocker: str) -> dict[str, object]:
    return {
        "tool": tool,
        "available": bool(available),
        "executable_path": executable_path,
        "version": version,
        "install_method": install_method,
        "verification_command": " ".join(str(x) for x in probe.get("command", [])),
        "verification_stdout": str(probe.get("stdout", ""))[:4000],
        "verification_stderr": str(probe.get("stderr", ""))[:4000],
        "blocker": blocker,
        "timestamp": timestamp,
    }


java_path = shutil.which("java") or ""
java_probe = run([java_path, "-version"]) if java_path else {"command": ["java", "-version"], "stdout": "", "stderr": "java not found"}

sirius6 = "/home/zhome/opt/sirius/bin/sirius"
sirius4 = "/home/zhome/opt/sirius-4.9.15-headless/bin/sirius"
sirius_path = first_existing([shutil.which("sirius"), sirius4, sirius6])
sirius_probe = run([sirius_path, "--version"], timeout=20) if sirius_path else {"command": ["sirius", "--version"], "stdout": "", "stderr": "sirius not found"}
sirius_help_probe = run([sirius_path, "--help"], timeout=20) if sirius_path else sirius_probe
sirius_blocker = ""
if not sirius_path:
    sirius_blocker = "SIRIUS CLI was not found."
elif Path(sirius_path).resolve() == Path(sirius6).resolve():
    sirius_blocker = "SIRIUS 6.3.3 exists but requires account login for formula runs; benchmark uses SIRIUS 4.9.15 headless when available."

cfm_candidates = [
    shutil.which("cfm-id"),
    shutil.which("cfmid"),
    shutil.which("cfm-predict"),
    "/data/zhome/ec_structure_external_ms_models/envs/cfm_py36/bin/cfm-id",
    "/data/zhome/ec_structure_external_ms_models/envs/cfm_py36/bin/cfm-predict",
]
cfm_path = first_existing(cfm_candidates)
cfm_probe = run([cfm_path, "--version"], timeout=20) if cfm_path else {"command": ["cfm-id", "--version"], "stdout": "", "stderr": "CFM-ID executable not found"}
cfm_smoke_log = root / "results" / "logs" / "native_smoke" / "cfmid" / "cfmid_model_smokes.log"
cfm_blocker = "CFM-ID executable not found; no native CASMI CFM-ID inference was run."
if cfm_path:
    cfm_blocker = "CFM-ID executable is present, but available pretrained model/config smoke tests abort with Invalid Feature Configuration; no valid native CASMI CFM-ID benchmark scores are reported."
    if cfm_smoke_log.exists():
        cfm_blocker += f" Smoke log: {cfm_smoke_log}."

ms2_version = package_version("ms2deepscore")
ms2_probe = {"command": [sys.executable, "-c", "import ms2deepscore"], "returncode": 0 if ms2_version else 1, "stdout": ms2_version, "stderr": "" if ms2_version else "ms2deepscore package not installed"}
ms2_blocker = ""
if not ms2_version:
    ms2_blocker = "ms2deepscore Python package and pretrained model are not available; no native MS2DeepScore inference was run."
else:
    ms2_blocker = "ms2deepscore package is importable, but no pretrained model/embedding workflow is configured in this repository audit."

matchms_version = package_version("matchms")
matchms_probe = {"command": [sys.executable, "-c", "import matchms"], "returncode": 0 if matchms_version else 1, "stdout": matchms_version, "stderr": "" if matchms_version else "matchms package not installed"}

rows = [
    mkrow("Java", bool(java_path), java_path, compact_version(java_probe), "system_path", java_probe, "" if java_path else "Java runtime not found."),
    mkrow("SIRIUS", bool(sirius_path and Path(sirius_path).exists()), sirius_path, compact_version(sirius_probe, "SIRIUS"), "existing_user_space_headless" if sirius_path == sirius4 else "existing_path", sirius_probe, sirius_blocker),
    mkrow("SIRIUS --help", bool(sirius_path and sirius_help_probe.get("returncode") == 0), sirius_path, compact_version(sirius_help_probe, "help_checked"), "existing_user_space_headless" if sirius_path == sirius4 else "existing_path", sirius_help_probe, "" if sirius_path else "SIRIUS CLI was not found."),
    mkrow("CFM-ID", False, cfm_path, compact_version(cfm_probe), "existing_external_environment" if cfm_path else "not_installed", cfm_probe, cfm_blocker),
    mkrow("MS2DeepScore", False, "ms2deepscore" if ms2_version else "", ms2_version, "python_package" if ms2_version else "not_installed", ms2_probe, ms2_blocker),
    mkrow("matchms", bool(matchms_version), "matchms" if matchms_version else "", matchms_version, "python_package" if matchms_version else "not_installed", matchms_probe, "" if matchms_version else "matchms package not installed; MS2DeepScore preprocessing remains unavailable."),
]

payload = {
    "server": {
        "hostname": socket.gethostname(),
        "cwd": str(root),
        "platform": platform.platform(),
        "python_version": sys.version,
        "timestamp": timestamp,
    },
    "tools": rows,
}
audit_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
with audit_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(json.dumps(payload, indent=2, sort_keys=True))
PY_AUDIT

echo
echo "Native tool audit written to:"
echo "  ${AUDIT_JSON}"
echo "  ${AUDIT_CSV}"
echo "  ${FULL_LOG}"
