#!/usr/bin/env bash
set -euo pipefail

# Reproducible user-space MS2DeepScore environment for CASMI hybrid benchmarks.
# Install CPU-only torch first so pip does not resolve torch to multi-GB CUDA
# dependency wheels from PyPI.

ENV_DIR="${1:-/home/zhome/ec_structure/external_ms_models/envs/ms2deepscore_casmi}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m venv "${ENV_DIR}"
"${ENV_DIR}/bin/python" -m pip install --upgrade pip
"${ENV_DIR}/bin/python" -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.4.1+cpu"
"${ENV_DIR}/bin/python" -m pip install --extra-index-url https://download.pytorch.org/whl/cpu "ms2deepscore==2.7.2" "matchms==0.33.1"
"${ENV_DIR}/bin/python" -c "import importlib.metadata as md, torch; print('ms2deepscore', md.version('ms2deepscore')); print('matchms', md.version('matchms')); print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
