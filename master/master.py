# coding: utf-8

# Author: Du Mingzhe (mingzhe@nus.edu.sg)
# Date: 2025-05-21

import os
import time
import pytz
import logging
from database import DataBase
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# load the environment variables
load_dotenv()

# Flask Config
app = Flask(__name__)
app.logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('argus.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.db = DataBase(redis_host='localhost', redis_port=6379, redis_password=os.environ["REDIS_PASSWORD"], redis_db=0)
sgt_timezone = pytz.timezone('Asia/Singapore')

# before request
@app.before_request
def before_request():
    if request.endpoint in ['server_status', 'user_status', 'server_detail', 'server_kill', 'server_book', 'server_unbook', 'server_list', 'index']:
        if not session.get('instance_id'):
            return redirect(url_for('user_login'))

@app.route('/')
def index():
    user_info = app.db.get_user_info(session['instance_id'])
    return render_template('index.html', instance_id=session['instance_id'], credit=user_info['credit'], server_list=user_info['server_list'])

@app.route('/server/detail', methods=['GET'])
def server_detail():
    request_server_id = request.args.get('server_id')
    server_info = app.db.get_server_info(request_server_id)
    
    free_slots = {gpu: [] for gpu in server_info['book_event'].keys()}
    current_hour_timestamp = int(time.time()) - int(time.time()) % 3600
    for gpu in server_info['book_event']:
        book_event = server_info['book_event'][gpu]
        for i in range(48):
            current_slot_utc_timestamp = current_hour_timestamp + i * 3600
            utc_dt = datetime.fromtimestamp(current_slot_utc_timestamp, pytz.utc)
            sgt_dt = utc_dt.astimezone(sgt_timezone)
            display_time_sgt = sgt_dt.strftime('%m-%d %H:%M')
            free_slots[gpu].append(
                {
                    "current_timestamp": current_slot_utc_timestamp,
                    "display_time": display_time_sgt,
                    "booked_by": book_event[str(current_slot_utc_timestamp)] if str(current_slot_utc_timestamp) in book_event else ""
                }
            )

    return render_template('detail.html', server_id=request_server_id, data=server_info['server_status'], free_slots=free_slots)

@app.route('/server/status', methods=['GET', 'POST'])
def server_status():
    request_server_id = request.args.get('server_id')
    if request.method == 'POST':
        server_status_data = request.get_json()
        if request_server_id != session['instance_id']:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        
        server_info = app.db.get_server_info(request_server_id)
        server_info['server_status'] = server_status_data['server_status']
        server_info['timestamp'] = server_status_data['timestamp']
        app.db.set_server_info(request_server_id, server_info)
        
        # log the server status
        app.logger.info(f"[Server Status] -> {request_server_id} {server_status_data['server_status']} {server_status_data['timestamp']}")
        
        return jsonify({'status': 'success'}), 200
    elif request.method == 'GET':
        user_info = app.db.get_user_info(session['instance_id'])
        if request_server_id in user_info['server_list']:
            server_info = app.db.get_server_info(request_server_id)
            return jsonify({'status': 'success', 'server_id': request_server_id, 'server_status': server_info['server_status']}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

@app.route('/server/book', methods=['GET'])
def server_book():
    request_server_id = request.args.get('server_id')
    request_gpu_id = request.args.get('gpu_id')
    request_timestamp = request.args.get('timestamp')
    
    # log the book event
    app.logger.info(f"[Server Book] -> {session['instance_id']} {request_server_id} {request_gpu_id} {request_timestamp}")
    
    # check if the user is authorized to accessthis server
    user_info = app.db.get_user_info(session['instance_id'])
    if request_server_id not in user_info['server_list']:
        app.logger.info(f"[Server Book] -> {session['instance_id']} {request_server_id} {request_gpu_id} {request_timestamp} Unauthorized")
        flash('Unauthorized. You are not authorized to access this server.', 'danger')
        return redirect(url_for('server_detail', server_id=request_server_id))
    
    # check if the slot is already booked
    server_info = app.db.get_server_info(request_server_id)
    if request_timestamp in server_info['book_event'][request_gpu_id]:
        app.logger.info(f"[Server Book] -> {session['instance_id']} {request_server_id} {request_gpu_id} {request_timestamp} Slot already booked")
        flash('Slot already booked. Please check the timestamp.', 'danger')
        return redirect(url_for('server_detail', server_id=request_server_id))
    
    # charge the user credit
    if user_info['credit'] < 1:
        app.logger.info(f"[Server Book] -> {session['instance_id']} {request_server_id} {request_gpu_id} {request_timestamp} Insufficient credit")
        flash('Insufficient credit. Please check your credit.', 'danger')
        return redirect(url_for('server_detail', server_id=request_server_id))
    
    user_info['credit'] -= 1
    app.db.set_user_info(session['instance_id'], user_info)
    
    # book the slot
    server_info['book_event'][str(request_gpu_id)][str(request_timestamp)] = {
        'username': session['instance_id']
    }
    app.db.set_server_info(request_server_id, server_info)
    
    flash('Booked successfully!', 'success')
    return redirect(url_for('server_detail', server_id=request_server_id))

@app.route('/server/unbook', methods=['GET'])
def server_unbook():
    request_server_id = request.args.get('server_id')
    request_gpu_id = request.args.get('gpu_id')
    request_timestamp = request.args.get('timestamp')
    
    # log the unbook event
    app.logger.info(f"[Server Unbook] -> {session['instance_id']} {request_server_id} {request_gpu_id} {request_timestamp}")
    
    # check if the user is authorized to this server
    user_info = app.db.get_user_info(session['instance_id'])
    if request_server_id not in user_info['server_list']:
        return jsonify({'status': 'error', 'message': 'Unauthorized. You are not authorized to access this server.'}), 401
    
    # check if the booking event exists
    server_info = app.db.get_server_info(request_server_id)
    if request_timestamp not in server_info['book_event'][request_gpu_id]:
        return jsonify({'status': 'error', 'message': 'Slot not booked. Please check the timestamp.'}), 400
    
    # check if the booking event is booked by the user
    booked_event = server_info['book_event'][str(request_gpu_id)][str(request_timestamp)]
    if booked_event['username'] != session['instance_id']:
        return jsonify({'status': 'error', 'message': 'Unauthorized. Only the booker can unbook the slot.'}), 401
    
    # return the credit to the user
    user_info['credit'] += 1
    app.db.set_user_info(session['instance_id'], user_info)
    
    # unbook the slot
    server_info['book_event'][str(request_gpu_id)].pop(str(request_timestamp))
    app.db.set_server_info(request_server_id, server_info)
    
    flash('Unbooked successfully!', 'success')
    return redirect(url_for('server_detail', server_id=request_server_id))
    
@app.route('/server/kill', methods=['GET'])
def server_kill():
    request_server_id = request.args.get('server_id')
    
    # check if the user is authorized to kill this server
    if request_server_id != session['instance_id']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_info = app.db.get_server_info(request_server_id)
    current_hour_timestamp = str(int(time.time()) - int(time.time()) % 3600)
    
    exclusive_gpus = list()
    for gpu in server_info['book_event']:
        if current_hour_timestamp in server_info['book_event'][gpu]:
            exclusive_gpus.append(gpu)

    killing_pid_list = list()
    for gpu in server_info['server_status']:
        if str(gpu['gpu_id']) in exclusive_gpus:
            killing_pid_list.extend([process['pid'] for process in gpu['processes']])
    
    # log the kill event
    app.logger.info(f"[Server Kill] -> {request_server_id} {killing_pid_list}")
            
    return jsonify({'status': 'success', 'killing_pid_list': killing_pid_list}), 200

@app.route('/server/list', methods=['GET'])
def server_list():
    user_info = app.db.get_user_info(session['instance_id'])
    server_list = user_info['server_list']
    return jsonify({'status': 'success', 'server_list': server_list})

@app.route('/user/status', methods=['GET'])
def user_status():
    request_username = request.args.get('username')
    if request_username != session['username'] and session['username'] != 'ids_admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    user_info = app.db.get_user_info(request_username)
    if user_info:
        return jsonify({'status': 'success', 'user_info': user_info})
    else:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
@app.route('/server/login', methods=['POST'])
def server_login():
    server_id = request.form['server_id']
    password = request.form['password']
    if app.db.server_auth(server_id, password):
        session['instance_id'] = server_id
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if app.db.user_auth(username, password):
            session['instance_id'] = username
            # log the user login event
            app.logger.info(f"[User Login] -> [success] {username} {password}")
            flash('Login successful!', 'success')
            return redirect(url_for('index')), 200
        else:
            # log the user login event
            app.logger.info(f"[User Login] -> [failed] {username} {password}")
            flash('Invalid username or password.', 'danger')
            return render_template('login.html'), 401

    return render_template('login.html'), 200

@app.route('/user/logout')
def user_logout():
    # log the user logout event
    app.logger.info(f"[User Logout] -> {session['instance_id']}")
    
    session.pop('instance_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index')), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)