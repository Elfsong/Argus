# coding: utf-8

import pytz
import time
import uuid
import yaml
import requests
import streamlit as st
from datetime import datetime
from yaml.loader import SafeLoader
from streamlit_calendar import calendar
import streamlit_authenticator as stauth

# Get current time in Singapore
sg_tz = pytz.timezone("Asia/Singapore")
now = datetime.now(sg_tz)
now_iso = now.isoformat()
scroll_time = now.strftime("%H:%M:%S")

st.title("**Argus**")

with open('argus_auth.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

try:
    authenticator.login()
except Exception as e:
    st.error(e)

if st.session_state.get('authentication_status'):
    authenticator.logout(button_name=f'Logout as *{st.session_state.get("name")}*')
elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')
    st.stop()
elif st.session_state.get('authentication_status') is None:
    st.stop()
    
# Initialize session state
if "calendar_events" not in st.session_state:
    response = requests.get("http://35.198.224.15:8000/get_schedule")
    st.session_state.calendar_events = response.json()

calendar_options = {
    "editable": True,
    "selectable": True,
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "resourceTimelineDay resourceTimelineWeek",
    },
    "slotMinTime": "00:00:00",
    "slotMaxTime": "24:00:00",
    "initialView": "resourceTimelineDay",
    "resourceGroupField": "Server",
    "timeZone": "Asia/Singapore",
    "scrollTime": scroll_time,
    "now": now_iso,
    "resources": [
        {"id": "s22_gpu0", "title": "GPU 0", "Server": "S22"},
        {"id": "s22_gpu1", "title": "GPU 1", "Server": "S22"},
        {"id": "s22_gpu2", "title": "GPU 2", "Server": "S22"},
        {"id": "s22_gpu3", "title": "GPU 3", "Server": "S22"},
        {"id": "s1_gpu0", "title": "GPU 0", "Server": "S1"},
        {"id": "s1_gpu1", "title": "GPU 1", "Server": "S1"},
        {"id": "s2_gpu0", "title": "GPU 0", "Server": "S2"},
        {"id": "s2_gpu1", "title": "GPU 1", "Server": "S2"},
    ],
}

custom_css = """
    .fc-event-past {
        opacity: 0.8;
    }
    .fc-event-time {
        font-style: italic;
    }
    .fc-event-title {
        font-weight: 700;
    }
    .fc-toolbar-title {
        font-size: 2rem;
    }
"""

def generate_short_uuid(length=4):
    full_uuid = uuid.uuid4()
    short_id = full_uuid.hex[:length]
    return short_id

@st.dialog("Booking Confirmation")
def booking_confirmation(user_name, start_time, end_time, resource_id):
    st.write(f"**User:** {user_name}")
    st.write(f"**Start Time:** {start_time}")
    st.write(f"**End Time:** {end_time}")
    st.write(f"**Resource:** {resource_id}")
    
    if st.button("Confirm"):
        new_event = {
            "title": f"{user_name}-{generate_short_uuid()}",
            "start": start_time,
            "end": end_time,
            "resourceId": resource_id,
        }
        updated_events = st.session_state.calendar_events + [new_event]
        response = requests.post("http://35.198.224.15:8000/post_schedule", json={"schedule": updated_events})
        if response.status_code == 200:
            st.success("Schedule updated successfully")
            st.session_state.calendar_events = updated_events
        else:
            st.error(f"Failed to update schedule.")

@st.dialog("Cancel Confirmation")
def cancel_confirmation(title, start_time, end_time, resource_id):
    st.write(f"**Title:** {title}")
    st.write(f"**Start Time:** {start_time}")
    st.write(f"**End Time:** {end_time}")
    st.write(f"**Resource:** {resource_id}")
    
    if st.button("Confirm"):
        updated_events = list()
        found_event = False
        for event in st.session_state.calendar_events:
            if title != event["title"]:
                updated_events.append(event)
            else:
                found_event = True
                
        if found_event:
            response = requests.post("http://35.198.224.15:8000/post_schedule", json={"schedule": updated_events})
            if response.status_code == 200:
                st.session_state.calendar_events = updated_events
                st.success("Schedule cancelled successfully")
            else:
                st.error("Failed to cancel schedule. Try again later.")
        else:
            st.error("Event not found.")

event = calendar(
    events=st.session_state.calendar_events,
    options=calendar_options,
    custom_css=custom_css,
    key='calendar',
)

callback = event.get("callback", None)
if callback == "select":
    start_time = event['select']['start']
    end_time = event['select']['end']
    resource_id = event['select']['resource']['id']
    booking_confirmation(st.session_state.get("username"), start_time, end_time, resource_id)
elif callback == "eventClick":
    title = event['eventClick']['event']['title']
    start_time = event['eventClick']['event']['start']
    end_time = event['eventClick']['event']['end']
    resource_id = event['eventClick']['event']['resourceId']
    cancel_confirmation(title, start_time, end_time, resource_id)
