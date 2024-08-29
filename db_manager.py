from pymongo import MongoClient
from datetime import datetime, timezone

class MongoDBManager:
    def __init__(self, uri='mongodb://localhost:27017/', db_name='neurosky'):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.sessions = self.db.sessions

    def start_session(self, user_id):
        session = {
            'user_id': user_id,
            'start_time': datetime.now(timezone.utc),
            'end_time': None,
            'data': []
        }
        return self.sessions.insert_one(session).inserted_id

    def end_session(self, session_id):
        self.sessions.update_one({'_id': session_id}, {'$set': {'end_time': datetime.now(timezone.utc)}})

    def save_data(self, session_id, data_point):
        self.sessions.update_one({'_id': session_id}, {'$push': {'data': data_point}})

    def get_user_sessions(self, user_id):
        return self.sessions.find({'user_id': user_id})

    def get_session_data(self, session_id):
        session = self.sessions.find_one({'_id': session_id})
        return session['data'] if session else None
