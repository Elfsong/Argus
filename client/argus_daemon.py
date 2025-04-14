import daemon
import signal
import os
import sys
import logging
from daemon.pidfile import PIDLockFile
from argus_client import ArgusClient

LOG_PATH = "./argus_client.log"
PID_PATH = "./argus_client.pid"
STDOUT_PATH = "./argus_client_stdout.log"
STDERR_PATH = "./argus_client_stderr.log"

def setup_logger():
    logger = logging.getLogger("argus_client")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_PATH)
    stream_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def run():
    setup_logger()
    client = ArgusClient(server_url="http://35.198.224.15:8000", interval=10, sid="S22")
    client.telemetry_loop()

context = daemon.DaemonContext(
    pidfile=PIDLockFile(PID_PATH),
    signal_map={signal.SIGTERM: lambda s, f: sys.exit(0)},
    working_directory=os.getcwd(),
)

if __name__ == "__main__":
    with context:
        run()
