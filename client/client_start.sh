#! /bin/bash

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "argus_venv" ]; then  
    python3 -m venv argus_venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source argus_venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install requests psutil flask python-daemon

# Start the daemon
echo "Starting the daemon..."
python argus_daemon.py
echo "Daemon started successfully."