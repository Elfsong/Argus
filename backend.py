from flask import Flask, request, jsonify
import redis
import json

app = Flask(__name__)

# Connect to local Redis server
r = redis.Redis(host='localhost', port=6379, db=0)

@app.route("/submit_gpu_data", methods=["POST"])
def submit():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400

    r.set("gpu_data", json.dumps(data))
    return jsonify({"status": "ok"}), 200

@app.route("/get_gpu_data", methods=["GET"])
def get_gpu_data():
    data = r.get("gpu_data")
    if data:
        return jsonify(json.loads(data))
    else:
        return jsonify({"status": "error", "message": "No GPU data found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

