# coding: utf-8
import os
import json
import redis
import signal
from psutil import Process
from flask import Flask, request, jsonify

app = Flask(__name__)

# Connect to local Redis server
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.route("/kill_process", methods=["POST"])
def kill_process():
    data = request.get_json()
    # TODO(Andrew): Validate data

    if "sid" not in data:
        return jsonify({"status": "error", "message": "No SID provided"}), 400

    if "pid" not in data:
        return jsonify({"status": "error", "message": "No PID provided"}), 400
    
    # Get Metadata  
    pid = data["pid"]
    sid = data["sid"]

    # Kill Process
    try:
        os.kill(pid, signal.SIGKILL)
        print(f"[✔] Killed PID {pid}")
        return jsonify({"status": "ok"}), 200
    except ProcessLookupError:
        return jsonify({"status": "error", "message": "PID does not exist"}), 400
    except PermissionError:
        return jsonify({"status": "error", "message": "No permission to kill PID"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to kill PID"}), 500
    

@app.route("/submit_gpu_data", methods=["POST"])
def post_gpu_data():
    data = request.get_json()
    # TODO(Andrew): Validate data
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400

    redis_client.set("gpu_data", json.dumps(data))
    return jsonify({"status": "ok"}), 200

@app.route("/get_gpu_data", methods=["GET"])
def get_gpu_data():
    data = redis_client.get("gpu_data")
    if data:
        return jsonify(json.loads(data))
    else:
        return jsonify({"status": "error", "message": "No GPU data found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

