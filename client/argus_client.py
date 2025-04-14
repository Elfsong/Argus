# coding: utf-8
import os
import pwd
import json
import time
import signal
import requests
import subprocess
from psutil import Process
import logging

logger = logging.getLogger("argus_client")

class ArgusClient:
    def __init__(self, server_url="http://35.198.224.15:8000", interval=10, sid="Unknown"):
        self.server_url = server_url
        self.interval = interval
        self.sid = sid
        logger.info(f"[Argus Client] Initialized with SID: {self.sid}")

    @staticmethod
    def get_username(pid):
        try:
            return pwd.getpwuid(os.stat(f'/proc/{pid}').st_uid).pw_name
        except Exception:
            return "unknown"

    @staticmethod
    def get_gpu_usage():
        gpu_usage = []
        try:
            gpu_info_output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,utilization.gpu','--format=csv,noheader,nounits'],
                encoding='utf-8'
            )
            uuid_output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=index,uuid','--format=csv,noheader,nounits'],
                encoding='utf-8'
            )
            index_to_uuid = {
                int(idx): uuid for idx, uuid in
                (line.split(',') for line in uuid_output.strip().split('\n'))
            }

            process_info_output = subprocess.check_output(
                ['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,process_name,used_memory', '--format=csv,noheader,nounits'],
                encoding='utf-8'
            )

            process_usage = {}
            for line in process_info_output.strip().split('\n'):
                if not line.strip(): continue
                gpu_uuid, pid, pname, mem = [x.strip() for x in line.split(',')]
                pid = int(pid)
                process_usage.setdefault(gpu_uuid, []).append({
                    'pid': pid,
                    'user': ArgusClient.get_username(pid),
                    'process_name': pname,
                    'used_memory_MB': int(mem)
                })

            for line in gpu_info_output.strip().split('\n'):
                index, name, mem_total, mem_used, util = [x.strip() for x in line.split(',')]
                gpu_index = int(index)
                uuid = index_to_uuid.get(gpu_index)
                gpu_usage.append({
                    'index': gpu_index,
                    'name': name,
                    'memory_total_MB': int(mem_total),
                    'memory_used_MB': int(mem_used),
                    'utilization_percent': int(util),
                    'processes': process_usage.get(uuid, [])
                })

        except subprocess.CalledProcessError as e:
            logger.error(f"[GPU Usage] subprocess error: {e}")
        except FileNotFoundError:
            logger.error("[GPU Usage] nvidia-smi not found.")
        finally:
            return gpu_usage

    @staticmethod
    def kill_process(pid):
        try:
            p = Process(pid)
            p.terminate()
            logger.info(f"[Kill] Successfully killed PID {pid}")
        except Exception as e:
            logger.warning(f"[Kill] Failed to kill PID {pid}: {e}")

    def post_system_data(self):
        try:
            system_data = self.get_gpu_usage()
            response = requests.post(f"{self.server_url}/post_system_data", json={
                "sid": self.sid,
                "system_data": system_data
            })
            logger.info(f"[System Data] system_data: {system_data}")
        except Exception as e:
            logger.error(f"[System Data] Error: {e}")

    def get_kill_process(self):
        try:
            response = requests.get(f"{self.server_url}/get_kill_process/{self.sid}").json()
            logger.info(f"[Kill Process] pid_list: {response.get('pid_list', [])}")

            if response.get("sid") != self.sid: return
            for pid in response.get("pid_list", []):
                logger.info(f"[Kill Process] Killing process: [{pid}]")
                ArgusClient.kill_process(int(pid))

        except Exception as e:
            logger.error(f"[Kill Process] Error: {e}")

    def telemetry_loop(self):
        while True:
            try:
                self.post_system_data()
                self.get_kill_process()
            except Exception as e:
                logger.error(f"[Telemetry Loop] Error: {e}")
            time.sleep(self.interval)
