# coding: utf-8
import os
import json
import redis
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Logging Config
log_handler = RotatingFileHandler('argus_server.log', maxBytes=5*1024*1024)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logging.basicConfig(level=logging.INFO, handlers=[log_handler,logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Connect to local Redis server
redis_client = redis.Redis(host='localhost', port=6379, password=os.getenv("REDIS_PASSWORD"), db=0)

# Server List
SERVER_LIST = ["S22"]

@app.route("/post_system_data", methods=["POST"])
def post_system_data():
    data = request.get_json()
    # TODO(Andrew): Validate data / Authorization

    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    if "sid" not in data:
        return jsonify({"status": "error", "message": "No SID provided"}), 400
    if "system_data" not in data:
        return jsonify({"status": "error", "message": "No GPU data provided"}), 400
    
    system_data = data["system_data"]
    logger.info(f"[Post System Data] <- {system_data}")

    # Update system data to Redis
    redis_client.set(f"{data['sid']}_data", json.dumps(system_data))

    return jsonify({"status": "ok"}), 200

@app.route("/get_system_data/<sid>", methods=["GET"])
def get_system_data(sid):
    # TODO(Andrew): Validate data / Authorization

    if not sid:
        return jsonify({"status": "error", "message": "No SID provided"}), 400

    system_data = redis_client.get(f"{sid}_data")
    logger.info(f"[Get GPU Data] {system_data}")
    if system_data:
        return jsonify(json.loads(system_data))
    else:
        return jsonify({"status": "error", "message": "No GPU data found"}), 404

@app.route("/get_schedule", methods=["GET"])
def get_schedule():
    # TODO(Andrew): Validate data / Authorization

    schedule = redis_client.get("schedule")
    logger.info(f"[Get Schedule] -> {schedule}")

    return schedule, 200
    
@app.route("/post_schedule", methods=["POST"])
def post_schedule():
    # TODO(Andrew): Validate data / Authorization
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    if "schedule" not in data:
        return jsonify({"status": "error", "message": "No schedule provided"}), 400
        
    redis_client.set("schedule", json.dumps(data["schedule"]))
    logger.info(f"[Post Schedule] <- {data['schedule']}")

    return jsonify({"status": "ok"}), 200

@app.route("/get_resource_list", methods=["GET"])
def get_resource_list():
    resource_list = []
    for sid in SERVER_LIST:
        system_data = redis_client.get(f"{sid}_data")
        system_data = json.loads(system_data)
        for gpu_info in system_data:
            resource_list.append({
                "id": f"{sid}_gpu{gpu_info['index']}",
                "title": f"{gpu_info['name']}-{gpu_info['index']} [{gpu_info['memory_used_MB']}/{gpu_info['memory_total_MB']}]",
                "server": sid
            })
    logger.info(f"[Get Resource List] -> {resource_list}")
    return resource_list, 200
 
@app.route("/get_kill_process/<sid>", methods=["GET"])
def get_kill_process(sid):
    # TODO(Andrew): Validate data / Authorization

    if not sid:
        return jsonify({"status": "error", "message": "No SID provided"}), 400

    pid_list = redis_client.get(f"{sid}_pid_list")
    pid_list = json.loads(pid_list) if pid_list else []

    kill_process = {
        "sid": sid,
        "pid_list": pid_list
    }

    logger.info(f"[Kill Process] -> {kill_process}")
    return jsonify(kill_process), 200

if __name__ == "__main__":
    # TODO(Andrew): Wrap it using gunicorn
    app.run(host="0.0.0.0", port=8000)