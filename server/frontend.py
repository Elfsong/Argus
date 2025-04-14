# coding: utf-8

import os
import redis
import requests
import streamlit as st

# Initialize Redis Client
redis_client = redis.Redis(host='localhost', port=6379, password=os.getenv("REDIS_PASSWORD"), db=0)

st.title("Argus")

# Get GPU Data
response = requests.get("http://localhost:8000/get_gpu_data")
st.write(response.json())


