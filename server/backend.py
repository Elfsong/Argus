# coding: utf-8
import os
import json
import redis
import signal
import logging
from psutil import Process
from flask import Flask, request, jsonify

app = Flask(__name__)

# Logging Config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('argus_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Connect to local Redis server
redis_client = redis.Redis(host='localhost', port=6379, password=os.getenv("REDIS_PASSWORD"), db=0)

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
    logger.info(f"[Post System Data] {system_data}")

    # Update system data to Redis
    redis_client.set(f"{data['sid']}_data", json.dumps(system_data))

    return jsonify({"status": "ok"}), 200

@app.route("/get_gpu_data/<sid>", methods=["GET"])
def get_gpu_data(sid):
    # TODO(Andrew): Validate data / Authorization

    if not sid:
        return jsonify({"status": "error", "message": "No SID provided"}), 400

    system_data = redis_client.get(f"{sid}_data")
    logger.info(f"[Get GPU Data] {system_data}")
    if system_data:
        return jsonify(json.loads(system_data))
    else:
        return jsonify({"status": "error", "message": "No GPU data found"}), 404
    
@app.route("/get_kill_process/<sid>", methods=["GET"])
def get_kill_process(sid):
    # TODO(Andrew): Validate data / Authorization

    if not sid:
        return jsonify({"status": "error", "message": "No SID provided"}), 400

    kill_process = {
        "sid": sid,
        "pid_list": ["1", "2", "3"]
    }

    logger.info(f"[Kill Process] {kill_process}")
    return jsonify(kill_process), 200

if __name__ == "__main__":
    # TODO(Andrew): Wrap it using gunicorn
    app.run(host="0.0.0.0", port=8000)