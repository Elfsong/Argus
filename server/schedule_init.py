# coding: utf-8
import os
import redis
import json
from datetime import datetime, timedelta


# Connect to local Redis server
redis_client = redis.Redis(host='localhost', port=6379, password=os.getenv("REDIS_PASSWORD"), db=0)

redis_client.set("schedule", json.dumps([]))