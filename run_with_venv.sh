#!/bin/bash
# Script to run commands with the virtual environment activated

# Activate virtual environment
source venv/bin/activate

# Run the command passed as arguments
"$@"
