#!/bin/bash
# Quick IBKR Paper Trading Account Balance Check
# Usage: ./check_balance.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
python utils/ibkr_paper_funding.py --check