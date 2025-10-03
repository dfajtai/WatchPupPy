#!/bin/bash
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
    echo "Virtual environment deactivated."
else
    echo "No active virtual environment to deactivate."
fi