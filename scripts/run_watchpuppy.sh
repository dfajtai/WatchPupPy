
#!/bin/bash

# -----------------------------------------------------------------------------
# Script to start the WatchPupPy application.
#
# This script activates the Python environment (if present),
# and then launches the main Python GUI application.
#
# Usage:
#   ./run_watchpuppy.sh
#
# Requirements:
#   - Python 3 or Python must be installed and available in PATH.
#   - scripts/activate_env.sh must exist and properly set up the environment.
#   - start.py must exist in the project root.
# -----------------------------------------------------------------------------

# Move to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"


# Activate the Python virtual environment or other environment
if [ -f "scripts/activate_env.sh" ]; then
    # Source the environment activation script in the current shell
    cd scripts
    source activate_env.sh
    cd ..
else
    echo "Error: Environment activation script scripts/activate_env.sh not found!"
    read
    exit 1
fi


# Determine the Python command: try python3, fallback to python
PYTHON_CMD=python3
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD=python
fi

# Path to the main application start script
START_SCRIPT="start.py"

if [ ! -f "$START_SCRIPT" ]; then
    echo "Error: Start script $START_SCRIPT not found!"
    read
    exit 1
fi

# Create log directory if not exists
if [ ! -d "log" ]; then
    mkdir log
fi

# Rotate existing log file if present
LOG_FILE="log/run.log"
if [ -f "$LOG_FILE" ]; then
    i=1
    while [ -f "log/run.log.$i" ]; do
        i=$((i + 1))
    done
    mv "$LOG_FILE" "log/run.log.$i"
fi


echo "Starting WatchPupPy application..."
$PYTHON_CMD $START_SCRIPT > "$LOG_FILE" 2>&1

# Activate the Python virtual environment or other environment
if [ -f "scripts/deactivate_env.sh" ]; then
    # Source the environment activation script in the current shell
    cd scripts
    source deactivate_env.sh
    cd ..
else
    echo "Error: Environment activation script scripts/deactivate_env.sh not found!"
    read
    exit 1
fi

echo "Output saved to run.log. Press enter to exit..."
read
exit
