import daemon
import signal
import os
import sys
from daemon.pidfile import PIDLockFile
from argus_client import ArgusClient

client = ArgusClient(server_url="http://35.198.224.15:8000", interval=10, sid="S22")
pid_file_path = "./argus_daemon.pid"

def stop_handler(signum, frame):
    print("Stopping daemon gracefully.")
    sys.exit(0)

context = daemon.DaemonContext(
    pidfile=PIDLockFile(pid_file_path),
    stdout=open("./argus_stdout.log", "a+"),
    stderr=open("./argus_stderr.log", "a+"),
    signal_map={signal.SIGTERM: stop_handler, signal.SIGINT: stop_handler},
    working_directory=os.getcwd()
)

if __name__ == "__main__":
    with context:
        client.telemetry_loop()
