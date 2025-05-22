# coding: utf-8

# Author: Du Mingzhe (mingzhe@nus.edu.sg)
# Date: 2025-05-21

import os
import time
import psutil 
import logging
import requests
import subprocess
from dotenv import load_dotenv

class Telemetry:        
    def __init__(self, server_id, server_password, master_url, interval):
        self.server_id = server_id
        self.server_password = server_password
        self.master_url = master_url
        self.interval = interval
        self.logger = logging.getLogger("telemetry_client")

    def kill_process_psutil(self, pid: int, force: bool = False, timeout: int = 5) -> bool:
        try:
            proc = psutil.Process(pid)

            if force:
                proc.kill()
                self.logger.info(f"[psutil] Force kill signal sent to process {pid}.")
                time.sleep(1)
                return not psutil.pid_exists(pid)

            # Attempt graceful termination
            self.logger.info(f"[psutil] Attempting graceful termination of process {pid} (PID: {proc.pid})...")
            proc.terminate() # Sends SIGTERM on POSIX, TerminateProcess on Windows

            # Wait for the process to terminate
            try:
                self.logger.info(f"[psutil] Waiting up to {timeout} seconds for process {pid} to terminate...")
                # wait() returns the exit status or None. Raises TimeoutExpired if it doesn't die.
                proc.wait(timeout=timeout)
                self.logger.info(f"[psutil] Process {pid} terminated gracefully.")
                return True
            except psutil.TimeoutExpired:
                self.logger.info(f"[psutil] Process {pid} did not terminate gracefully after {timeout} seconds. Force killing...")
                proc.kill() # Sends SIGKILL on POSIX, TerminateProcess on Windows (forcefully)
                time.sleep(0.1) # Brief pause
                if not psutil.pid_exists(pid):
                    self.logger.info(f"[psutil] Process {pid} killed forcefully after timeout.")
                    return True
                else:
                    self.logger.info(f"[psutil] Process {pid} may still be running after forceful kill attempt.")
                    return False
            except psutil.NoSuchProcess: # Process might have terminated very quickly
                self.logger.info(f"[psutil] Process {pid} terminated gracefully (or was already gone).")
                return True

        except psutil.NoSuchProcess:
            self.logger.info(f"[psutil] Process {pid} not found (already terminated or never existed).")
            return True # Considered success as the process is not running
        except psutil.AccessDenied:
            self.logger.info(f"[psutil] Access denied. Insufficient permissions to kill process {pid}.")
            return False
        except Exception as e:
            self.logger.info(f"[psutil] An error occurred while trying to kill process {pid}: {e}")
            return False

    def get_server_info(self):
        gpus_data = []
        gpus_details_by_id = {}
        uuid_to_gpu_id_map = {}

        try:
            gpu_query_cmd = [
                'nvidia-smi',
                '--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu,temperature.gpu',
                '--format=csv,noheader,nounits'
            ]
            gpu_process = subprocess.run(gpu_query_cmd, capture_output=True, text=True, check=True)
            
            gpu_lines = gpu_process.stdout.strip().split('\n')
            if not gpu_lines or not gpu_lines[0]:
                self.logger.error("[Client Get] No GPU data returned from nvidia-smi.")
                return []

            for line in gpu_lines:
                raw_parts = line.split(',') 
                if len(raw_parts) < 6: # index, uuid, mem.used, mem.total, util, temp
                    self.logger.warning(f"[Client Get] Skipping malformed GPU line (not enough parts): {line}")
                    continue
                
                parts = [p.strip() for p in raw_parts]

                try:
                    gpu_id = int(parts[0])
                    gpu_uuid = parts[1]
                    mem_used = int(parts[2])
                    mem_total = int(parts[3])
                except ValueError:
                    self.logger.warning(f"[Client Get] Skipping GPU line due to unparsable critical fields (ID, UUID, Memory): {line}")
                    continue

                util_str = parts[4]
                try:
                    utilization_display = f"{int(util_str)}%"
                except ValueError:
                    utilization_display = util_str 

                temp_str = parts[5]
                try:
                    temperature_display = f"{int(temp_str)}°C"
                except ValueError:
                    temperature_display = temp_str 
                
                gpus_details_by_id[gpu_id] = {
                    "gpu_id": gpu_id,
                    "uuid": gpu_uuid,
                    "memory_usage_mib": mem_used,
                    "memory_total_mib": mem_total,
                    "memory_percent": f"{(mem_used / mem_total * 100):.1f}%" if mem_total > 0 else "N/A",
                    "utilization_percent": utilization_display,
                    "temperature_celsius": temperature_display,
                    "processes": []
                }
                uuid_to_gpu_id_map[gpu_uuid] = gpu_id


            # 2. Get GPU process stats
            # Query fields: gpu_uuid, pid, process_name, used_gpu_memory
            process_query_cmd = [
                'nvidia-smi',
                '--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory', # Added used_gpu_memory
                '--format=csv,noheader,nounits'
            ]
            process_process = subprocess.run(process_query_cmd, capture_output=True, text=True, check=True)

            process_lines = process_process.stdout.strip().split('\n')
            if process_lines and process_lines[0]: 
                for line in process_lines:
                    raw_parts = line.split(',') 
                    if len(raw_parts) < 4: # gpu_uuid, pid, process_name, used_gpu_memory
                        self.logger.warning(f"[Client Get] Skipping malformed process line (not enough parts): {line}")
                        continue
                    
                    parts = [p.strip() for p in raw_parts]
                    
                    gpu_uuid_for_process = parts[0]
                    process_name = parts[2] # Get process name before potential pid parsing error
                    
                    try:
                        pid = int(parts[1])
                    except ValueError:
                        self.logger.warning(f"[Client Get] Skipping process line due to unparsable PID: '{parts[1]}' for process name '{process_name}' on GPU {gpu_uuid_for_process}")
                        continue
                    
                    try:
                        # Assuming 'nounits' makes used_gpu_memory an integer (MiB)
                        # If it still has " MiB", this int() will fail without further stripping.
                        # For robustness, strip non-numeric if necessary, or handle ValueError.
                        val_str = parts[3].replace(" MiB", "") # Attempt to remove " MiB" if present
                        process_mem_used_mib = int(val_str)
                    except ValueError:
                        process_mem_used_mib = "N/A" 
                        self.logger.warning(f"[Client Get] Could not parse used_gpu_memory for PID {pid} (value: '{parts[3]}'). Setting to N/A.")

                    username = "N/A" 

                    try:
                        p = psutil.Process(pid)
                        username = p.username()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass 
                    except Exception as e:
                        self.logger.warning(f"[Client Get] Could not get user for PID {pid}: {e}")

                    if gpu_uuid_for_process in uuid_to_gpu_id_map:
                        target_gpu_id = uuid_to_gpu_id_map[gpu_uuid_for_process]
                        if target_gpu_id in gpus_details_by_id:
                            gpus_details_by_id[target_gpu_id]["processes"].append({
                                "pid": pid,
                                "user": username,
                                "process_name": process_name,
                                "used_gpu_memory_mib": process_mem_used_mib # Added process GPU memory
                            })
                        else: 
                            self.logger.warning(f"[Client Get] Process PID {pid} (GPU UUID: {gpu_uuid_for_process}) maps to GPU ID {target_gpu_id}, which was not found.")
                    else:
                        self.logger.warning(f"[Client Get] Process PID {pid} is on GPU UUID {gpu_uuid_for_process}, but this UUID was not found in the initial GPU scan.")
            
            gpus_data = sorted(gpus_details_by_id.values(), key=lambda x: x["gpu_id"])

        except FileNotFoundError:
            self.logger.error("[Client Get] Error: nvidia-smi command not found. Make sure NVIDIA drivers are installed and nvidia-smi is in your PATH.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[Client Get] Error executing nvidia-smi: {e}")
            if e.stderr:
                self.logger.error(f"[Client Get] nvidia-smi stderr: {e.stderr.strip()}")
        except ImportError:
            self.logger.error("[Client Get] Error: psutil library not found. Please install it using 'pip install psutil'.")
        except ValueError as e: 
            self.logger.error(f"[Client Get] Error parsing data (possibly unexpected format or critical field unparsable): {e}")
        except Exception as e:
            self.logger.error(f"[Client Get] An unexpected error occurred: {e}")
        return gpus_data

    def post_server_info(self):
        server_status = self.get_server_info()
        if server_status:
            response = self.session.post(
                url = f"{MASTER_URL}/server/status?server_id={SERVER_ID}", 
                json = {"server_status": server_status, "timestamp": time.time()}
            )
            if response.status_code == 200:
                self.logger.info(f"[Client Post] Server info posted successfully.")
            else:
                self.logger.error(f"[Client Post] Failed to post server info. Status code: {response.status_code}")
        else:
            self.logger.error(f"[Client Post] No GPU data available to post.")

    def get_server_kill(self):
        response = self.session.get(url = f"{MASTER_URL}/server/kill?server_id={SERVER_ID}")
        response_json = response.json()
        if response_json['killing_pid_list']:
            for pid in response_json['killing_pid_list']:
                status = self.kill_process_psutil(pid)
                if status:
                    self.logger.info(f"[Client Kill] Server PID {pid} Killed")
                else:
                    self.logger.error(f"[Client Kill] Server PID {pid} Kill Failed")
        else:
            self.logger.info(f"[Client Kill] No Server PID to Kill")

    def client_login(self):
        self.session = requests.Session()
        response = self.session.post(f"{MASTER_URL}/server/login", data={'server_id': SERVER_ID, 'password': SERVER_PASSWORD})
        if response.status_code == 200:
            self.logger.info(f"[Client Login] Successfully logged in to the master server.")
            return True
        else:
            self.logger.error(f"[Client Login] Failed to log in to the master server. Status code: {response.status_code}")
            return False

    def telemetry_loop(self):
        self.client_login()
        while True:
            try:
                self.post_server_info(self.session)
                self.get_server_kill(self.session)
            except Exception as e:
                self.logger.error(f"[Telemetry Loop] Error: {e}")
            time.sleep(self.interval)
            
if __name__ == "__main__":
    load_dotenv()
    client = Telemetry(server_id=os.getenv("SERVER_ID"), server_password=os.getenv("SERVER_PASSWORD"), master_url=os.getenv("MASTER_URL"), interval=os.getenv("INTERVAL"))
    client.telemetry_loop()
        
        


