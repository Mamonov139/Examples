from traceback import format_exc
from typing import Optional
from collections import namedtuple

from flask_jwt_extended import decode_token
from flask_socketio import Namespace, disconnect
from flask import request, session as flask_session

from logger import get_logger
from models.connection import session
from models.models import Users
from resources.utils import RedisDict
from resources.chat.model import TextMessage, ActionMessage
from resources.chat.utils import Actions

UserSession = namedtuple("UserSession", ("sid", "user_id", "client_id"))


class Connection(Namespace):
    __slots__ = ("_LOGGER", "__REDIS")

    def __init__(self, namespace=None):
        Namespace.__init__(self, namespace=namespace)
        self._LOGGER = get_logger("InitConnection", "SocketIO-InitConnection")
        self.__REDIS = RedisDict()

    @property
    def logger(self):
        return self._LOGGER

    def __verify_session(self) -> Optional[UserSession]:
        """
        Верификация пользовательской сессии
        """
        token = getattr(request.authorization, "token", None)
        client_id = request.headers.get("client")

        if not token:
            self.logger.error(f"Failed to established connection no authorization token in request")
            disconnect()
            return None

        try:
            user_id = decode_token(token)["sub"]
        except Exception as error:
            self.logger.error(f"Failed to establish connection: %s: %s \n %s",
                              error.__class__.__name__, error, format_exc())
            return None

        with session() as ses:
            user_ok = ses.query(
                ses.query(Users).filter(Users.user_id == user_id, Users.banned.isnot(True)).exists()
            ).scalar()

        if not user_ok:
            self.logger.error(f"Failed to establish connection user not found or banned")
            return None

        sid = getattr(request, "sid", None)

        if not sid:
            self.logger.error(f"Failed to establish connection no sid in request")
            return None

        flask_session["from"] = user_id
        flask_session["sid"] = sid

        return UserSession(sid, user_id, client_id)

    def on_connect(self):
        """
        Подключение нового клиента
        """
        user_session = self.__verify_session()

        if not user_session:
            disconnect()
            return

        # добавляем новую сессию пользователя в хранилище
        sids: dict = self.__REDIS.get(user_session.user_id, default={})
        sids[user_session.client_id] = user_session.sid
        self.__REDIS[user_session.user_id] = sids

    def on_disconnect(self):
        """
        Отключение клиента
        """
        user_session = self.__verify_session()

        if not user_session:
            return

        # удаляем сессию пользователя из хранилища
        sids: dict = self.__REDIS[user_session.user_id]
        sids.pop(user_session.client_id, None)
        self.__REDIS[user_session.user_id] = sids


class Chat(Connection):
    """
    действия с чатом
    """

    def on_message(self, data):
        msg = TextMessage(data)
        try:
            msg.save_to_db()
        except Exception as e:
            self.logger.error(f"Не удалось отправить сообщение: {str(e)}\n{format_exc()}")
            # обратное уведомление об ошибке
            action_data = {"action": Actions.NOT_DELIVERED.value}
        else:
            # обратное уведомление о доставке сообщения
            action_data = {"action": Actions.DELIVERED.value}

        action_data.update({
            "message_id": msg.message_id,
            "extKey": msg.ext_key,
            "time": msg.time,
            "timestamp": msg.timestamp,
            "chat_id": msg.chat_id,
        })

        ActionMessage(action_data).reverse_recipients().do_action().clear_from().send()

        msg.translate().send().push()

    def on_action(self, data):
        msg = ActionMessage(data)
        try:
            msg.do_action().send()
        except Exception as e:
            self.logger.error(f"Не удалось отправить активность: {str(e)}\n{format_exc()}")
