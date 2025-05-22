
import os
import json
import redis

class DataBase:
    def __init__(self, redis_host, redis_port, redis_password, redis_db):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)

    def get_user_info(self, username):
        raw_data = self.redis_client.get(f'USER_{username}')
        return json.loads(raw_data) if raw_data else None
    
    def set_user_info(self, username, user_info):
        return self.redis_client.set(f'USER_{username}', json.dumps(user_info))
    
    def user_auth(self, username, password):
        user_info = self.get_user_info(username)
        return user_info and user_info['password'] == password
    
    def server_auth(self, server_id, password):
        server_info = self.get_server_info(server_id)
        return server_info and server_info['password'] == password
    
    def set_server_info(self, server_id, server_info):
        return self.redis_client.set(f'SERVER_{server_id}', json.dumps(server_info))
    
    def get_server_info(self, server_id):
        raw_data = self.redis_client.get(f'SERVER_{server_id}')
        return json.loads(raw_data) if raw_data else None