#!/usr/bin/env bash
set -euo pipefail

# run_server_training.sh
# Server-ready script to prepare environment, install dependencies, run training and evaluation.
# Usage: bash run_server_training.sh [--epochs N] [--batch-size B] [--output-dir /path/to/out] [--skip-system-install]
# Notes:
# - Runs from the repository root's `backend` folder. Script will cd there automatically when executed from repo root.
# - By default this installs system packages (APT/YUM) required for building Python native extensions and Rust toolchain.
# - If you have GPU and want a specific torch wheel, set TORCH_WHEEL env var to a pip-installable wheel URL before running.

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BACKEND_DIR="$REPO_ROOT/backend"

EPOCHS=3
BATCH_SIZE=16
OUTPUT_DIR="$REPO_ROOT/backend/app/nlu/checkpoints/results"
SKIP_SYSTEM_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --epochs) EPOCHS="$2"; shift 2;;
    --batch-size) BATCH_SIZE="$2"; shift 2;;
    --output-dir) OUTPUT_DIR="$2"; shift 2;;
    --skip-system-install) SKIP_SYSTEM_INSTALL=1; shift 1;;
    -h|--help) echo "Usage: $0 [--epochs N] [--batch-size B] [--output-dir DIR] [--skip-system-install]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "Repository root: $REPO_ROOT"
echo "Backend dir: $BACKEND_DIR"
echo "Epochs: $EPOCHS  Batch size: $BATCH_SIZE"
echo "Output dir: $OUTPUT_DIR"

cd "$BACKEND_DIR"

if [ "$SKIP_SYSTEM_INSTALL" -eq 0 ]; then
  echo "Checking for system package manager and installing build tools (may require sudo)..."
  if command -v apt-get >/dev/null 2>&1; then
    echo "Detected apt-get. Installing build-essential, python3-venv, python3-dev, curl, pkg-config, libssl-dev"
    sudo apt-get update && sudo apt-get install -y build-essential python3-venv python3-dev curl pkg-config libssl-dev libffi-dev
  elif command -v yum >/dev/null 2>&1; then
    echo "Detected yum. Installing Development Tools and required packages"
    sudo yum groupinstall -y 'Development Tools' || true
    sudo yum install -y python3-devel python3-venv curl openssl-devel libffi-devel
  else
    echo "No supported system package manager detected. Please ensure build tools and Python dev headers are installed." >&2
  fi
fi

# Ensure rust is available (tokenizers may require Rust to build from source). If rustc not present, install rustup non-interactively.
if ! command -v rustc >/dev/null 2>&1; then
  echo "Rust not found — installing rustup (will install to ~/.cargo)." 
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rustup-init.sh
  sh rustup-init.sh -y --no-modify-path --profile minimal
  export PATH="$HOME/.cargo/bin:$PATH"
  rm -f rustup-init.sh
fi

# Create / activate venv inside backend/.venv
VENV="$BACKEND_DIR/.venv"
if [ ! -d "$VENV" ]; then
  echo "Creating virtualenv at $VENV"
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

python -m pip install --upgrade pip setuptools wheel

# If user provided TORCH_WHEEL env var, install that wheel for GPU support; otherwise fall back to requirements.txt
if [ -n "${TORCH_WHEEL-}" ]; then
  echo "Installing torch from TORCH_WHEEL: $TORCH_WHEEL"
  pip install --no-cache-dir "$TORCH_WHEEL"
fi

echo "Installing Python requirements from repository requirements.txt"
pip install --no-cache-dir -r "$REPO_ROOT/requirements.txt"

# Export short-run overrides and call training
export EPOCHS="$EPOCHS"
export BATCH_SIZE="$BATCH_SIZE"

mkdir -p "$OUTPUT_DIR"

echo "Starting training (this may take time). Logs will stream to stdout."
python -u app/nlu/train.py 2>&1 | tee "$OUTPUT_DIR/train.log"

echo "Training finished. Running evaluation..."
python -u app/nlu/evaluate.py 2>&1 | tee "$OUTPUT_DIR/evaluate.log"

echo "Copying artifacts to output dir: $OUTPUT_DIR"
cp -v app/nlu/checkpoints/best_model.pt "$OUTPUT_DIR/" || true
cp -v app/nlu/checkpoints/meta.json "$OUTPUT_DIR/" || true

echo "Evaluation artifacts written to:"
ls -la "$OUTPUT_DIR"

echo "Done. To run longer experiments, re-run this script with --epochs N or edit app/nlu/train.py CONFIG." 
