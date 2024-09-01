from pymongo import MongoClient, errors
from datetime import datetime, timezone

class MongoDBManager:
    def __init__(self, uri='mongodb://localhost:27017/', db_name='neurosky'):
        try:
            self.client = MongoClient(uri)
            self.db = self.client[db_name]
            self.sessions = self.db.sessions
        except errors.ConnectionError as e:
            print(f"Error de conexión con MongoDB: {e}")
            self.client = None
        except errors.ServerSelectionTimeoutError as e:
            print(f"Tiempo de espera excedido al intentar conectar con MongoDB: {e}")
            self.client = None
        except Exception as e:
            print(f"Error inesperado al conectar con MongoDB: {e}")
            self.client = None

    def start_session(self, user_id):
        if self.client is None:
            print("No se pudo iniciar la sesión debido a problemas de conexión con MongoDB.")
            return None
        session = {
            'user_id': user_id,
            'start_time': datetime.now(timezone.utc),
            'end_time': None,
            'data': []
        }
        try:
            return self.sessions.insert_one(session).inserted_id
        except errors.OperationFailure as e:
            print(f"Error al iniciar la sesión en MongoDB: {e}")
            return None
        except Exception as e:
            print(f"Error inesperado al iniciar la sesión en MongoDB: {e}")
            return None

    def end_session(self, session_id):
        if self.client is None:
            return
        try:
            self.sessions.update_one({'_id': session_id}, {'$set': {'end_time': datetime.now(timezone.utc)}})
        except errors.OperationFailure as e:
            print(f"Error al finalizar la sesión en MongoDB: {e}")
        except Exception as e:
            print(f"Error inesperado al finalizar la sesión en MongoDB: {e}")

    def save_data(self, session_id, data_point):
        if self.client is None:
            return
        try:
            self.sessions.update_one({'_id': session_id}, {'$push': {'data': data_point}})
        except errors.OperationFailure as e:
            print(f"Error al guardar datos en MongoDB: {e}")
        except Exception as e:
            print(f"Error inesperado al guardar datos en MongoDB: {e}")

    def get_user_sessions(self, user_id):
        if self.client is None:
            return []
        try:
            return self.sessions.find({'user_id': user_id})
        except errors.OperationFailure as e:
            print(f"Error al obtener sesiones del usuario: {e}")
            return []
        except Exception as e:
            print(f"Error inesperado al obtener sesiones del usuario: {e}")
            return []

    def get_session_data(self, session_id):
        if self.client is None:
            return None
        try:
            session = self.sessions.find_one({'_id': session_id})
            return session['data'] if session else None
        except errors.OperationFailure as e:
            print(f"Error al obtener datos de la sesión: {e}")
            return None
        except Exception as e:
            print(f"Error inesperado al obtener datos de la sesión: {e}")
            return None
