# coding: utf-8

import os
import redis
import requests
import streamlit as st


st.title("Argus")

# Get GPU Data
sid = st.text_input("SID", value="S22")
response = requests.get(f"http://localhost:8000/get_gpu_data/{sid}")
response = response.json()
st.write(response)