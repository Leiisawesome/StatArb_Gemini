#!/usr/bin/env bash
set -euo pipefail

# Recreate the ai_integration_env virtual environment and install dependencies
# Usage: ./scripts/recreate_ai_env.sh

PYTHON=${PYTHON:-python3}
VENV_DIR="ai_integration_env"
REQ_FILE="requirements.txt"

if [ ! -f "$REQ_FILE" ]; then
  echo "requirements.txt not found — cannot install dependencies."
  exit 1
fi

echo "Creating virtual environment in ${VENV_DIR} using ${PYTHON}"
${PYTHON} -m venv "${VENV_DIR}"

echo "Activating virtualenv and upgrading pip"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip

echo "Installing requirements from ${REQ_FILE}"
pip install -r "${REQ_FILE}"

echo "Virtual environment created at ${VENV_DIR}. Activate with: source ${VENV_DIR}/bin/activate"
