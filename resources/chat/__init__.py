from flask_socketio import SocketIO

# from models.connection import get_redis_connection_url
from .actions import Chat
# from configs import configs

socket_io = SocketIO(cors_allowed_origins="*")


# регистрация обработчиков
socket_io.on_namespace(Chat())
