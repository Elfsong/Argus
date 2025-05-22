#! /bin/bash

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "telemetry_venv" ]; then  
    python3 -m venv telemetry_venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source telemetry_venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install requests psutil flask python-daemon python-dotenv

# Start the daemon
echo "Starting the daemon for $1..."
sudo /home/ids_admin/Argus/client/telemetry_venv/bin/python telemetry.py
echo "Daemon started successfully."