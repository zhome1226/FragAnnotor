#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/results/logs"
LOG_FILE="${LOG_DIR}/native_baseline_install.log"
mkdir -p "${LOG_DIR}"

{
  echo "# Native baseline setup audit"
  date -Is
  echo "root=${ROOT_DIR}"
  echo

  echo "## Existing executables"
  for exe in cfmid cfm-predict cfm-id sirius java git python3 pip3 conda mamba; do
    printf "%-16s" "${exe}"
    command -v "${exe}" || true
  done
  echo

  echo "## Python packages"
  python3 - <<'PY' || true
import importlib.util
for pkg in ["rdkit", "ms2deepscore", "matchms", "torch", "numpy", "pandas", "matplotlib", "yaml"]:
    print(f"{pkg}: {bool(importlib.util.find_spec(pkg))}")
PY
  echo

  cat <<'EOF'
## Installation policy
This repository does not vendor native CFM-ID, SIRIUS, or MS2DeepScore model
artifacts. If conda/mamba is available, install tools into a named environment
and rerun scripts/run_benchmark.py. If a tool requires manual download, license
acceptance, or pretrained weights, this script records the blocker instead of
bypassing it.

Suggested reproducible commands where permitted:
  mamba create -n fragannotor-benchmark -c conda-forge python=3.10 rdkit matchms
  pip install ms2deepscore

SIRIUS CLI must be downloaded from the vendor distribution when not available
through the package manager. CFM-ID installation is platform-specific; expose
cfm-predict, cfm-id, or cfmid on PATH before requesting native CASMI baseline
inference.
EOF
} 2>&1 | tee "${LOG_FILE}"

