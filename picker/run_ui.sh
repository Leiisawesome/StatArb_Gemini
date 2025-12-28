#!/bin/bash
# Launch the StatArb Symbol Picker UI

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

# Run Streamlit
$PROJECT_ROOT/ai_integration_env/bin/streamlit run $DIR/ui.py
