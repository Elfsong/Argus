# coding: utf-8
import os
import pwd
import json
import time
import redis
import signal
import logging
import requests
import subprocess
from psutil import Process
from flask import Flask, request, jsonify

app = Flask(__name__)

# Logging Config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_username(pid):
    try:
        return pwd.getpwuid(os.stat(f'/proc/{pid}').st_uid).pw_name
    except Exception:
        return "unknown"
    
def get_gpu_usage():
    gpu_usage = []
    try:
        # Query GPU info
        gpu_info_output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,utilization.gpu','--format=csv,noheader,nounits'],
            encoding='utf-8'
        )

        # Query GPU UUID to match with process usage
        uuid_output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=index,uuid',
             '--format=csv,noheader,nounits'],
            encoding='utf-8'
        )
        index_to_uuid = {}
        for line in uuid_output.strip().split('\n'):
            idx, uuid = [x.strip() for x in line.split(',')]
            index_to_uuid[int(idx)] = uuid

        # Query per-process usage
        process_info_output = subprocess.check_output(
            ['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,process_name,used_memory', '--format=csv,noheader,nounits'],
            encoding='utf-8'
        )

        # Map processes to GPUs
        process_usage = {}
        for line in process_info_output.strip().split('\n'):
            if not line.strip(): continue
            gpu_uuid, pid, pname, mem = [x.strip() for x in line.split(',')]
            pid = int(pid)
            process_usage.setdefault(gpu_uuid, []).append({
                'pid': pid,
                'user': get_username(pid),
                'process_name': pname,
                'used_memory_MB': int(mem)
            })

        # Combine everything
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
        print("Error running nvidia-smi:", e)
    except FileNotFoundError:
        print("nvidia-smi not found.")
    finally:
        return gpu_usage

def kill_process(pid):
    # TODO(Andrew): Kill process
    pass

def submit_system_data(server_url):
    try:
        system_data = get_gpu_usage()
        response = requests.post(f"{server_url}/post_system_data", json={"sid": "S22", "system_data": system_data})
        logger.info(f"[System Data] Data: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"[System Data] Error: {e}")
        return None

def kill_process(server_url):
    try:
        response = requests.get(f"{server_url}/get_kill_process")
        logger.info(f"[Kill Process] Data: {response.json()}")

        # TODO(Andrew): Kill process
        for process in response.json()["processes"]:
            kill_process(process["pid"])
        
        return response.json()
    except Exception as e:
        logger.error(f"[Kill Process] Error: {e}")
        return None

def telemetry_loop(server_url="http://35.198.224.15:8000", interval=10):
    while True:
        try:
            system_data_response = submit_system_data(server_url)
            kill_process_response = kill_process(server_url)
        except Exception as e:
            logger.error(f"[Telemetry Loop] Error: {e}")
        finally:
            time.sleep(interval)

if __name__ == "__main__":
    telemetry_loop()