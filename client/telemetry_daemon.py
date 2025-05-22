#! /usr/bin/env python3

import os
import sys
import daemon
import signal
import logging
from dotenv import load_dotenv
from telemetry import Telemetry
from daemon.pidfile import PIDLockFile
from logging.handlers import RotatingFileHandler

LOG_PATH = "./telemetry_client.log"
PID_PATH = "./telemetry_client.pid"

def setup_logger():
    logger = logging.getLogger("telemetry_client")
    logger.handlers.clear()
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def run(master_url, server_password, server_id, interval):
    setup_logger()
    client = Telemetry(master_url=master_url, server_password=server_password, server_id=server_id, interval=interval)
    client.telemetry_loop()

context = daemon.DaemonContext(
    pidfile=PIDLockFile(PID_PATH),
    signal_map={signal.SIGTERM: lambda s, f: sys.exit(0)},
    working_directory=os.getcwd(),
)

if __name__ == "__main__":
    load_dotenv()
    with context:
        run(master_url=os.getenv("MASTER_URL"), server_password=os.getenv("SERVER_PASSWORD"), server_id=os.getenv("SERVER_ID"), interval=os.getenv("INTERVAL"))
