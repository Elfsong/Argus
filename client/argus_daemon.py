#! /usr/bin/env python3

import os
import sys
import daemon
import signal
import logging
import argparse
from argus_client import ArgusClient
from daemon.pidfile import PIDLockFile
from logging.handlers import RotatingFileHandler

LOG_PATH = "./argus_client.log"
PID_PATH = "./argus_client.pid"
STDOUT_PATH = "./argus_client_stdout.log"
STDERR_PATH = "./argus_client_stderr.log"

def setup_logger():
    logger = logging.getLogger("argus_client")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024)
    stream_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def run(server_url, sid, interval):
    setup_logger()
    client = ArgusClient(server_url=server_url, interval=interval, sid=sid)
    client.telemetry_loop()

context = daemon.DaemonContext(
    pidfile=PIDLockFile(PID_PATH),
    signal_map={signal.SIGTERM: lambda s, f: sys.exit(0)},
    working_directory=os.getcwd(),
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_url", type=str, default="http://35.198.224.15:8000")
    parser.add_argument("--sid", type=str, required=True)
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()

    with context:
        run(server_url=args.server_url, sid=args.sid, interval=args.interval)
