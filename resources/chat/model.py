"""
Объектные модели для чата
"""
from abc import ABC, abstractmethod
from traceback import format_exc
from typing import Tuple

from firebase_admin import messaging
from firebase_admin.messaging import Notification
from flask import session as flask_session
from flask_socketio import emit
from sqlalchemy import func

from configs import configs
from logger import get_logger
from models.connection import session
from models.models import Users, ChatMessage, ChatMessageTranslated, UserXChat, Chat as ChatTable, get_pg_date
from resources.chat.utils import Actions, MessageType, get_chats_query, translate_text
from resources.utils import RedisDict
from services.utils import get_cached_service_element


LOGGER = get_logger("ChatsLog", "ChatsLog")


class DictInterface(ABC):
    """
    Интерфейс сериалдизации
    """

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class Client(DictInterface):
    """Модель клиента"""

    def __init__(self, user_id):
        redis = RedisDict()
        self.user_id = user_id
        self._sid_list = redis.get(user_id, {}).values()
        self._language = None
        self.fcm_tokens = redis.get(f'{self.user_id}_fcm_token_set', default=[])

    @property
    def language(self):
        if self._language:
            return self._language

        with session() as ses:
            user: Users = ses.query(Users).filter_by(user_id=self.user_id).one()
            self._language = user.language_id

        return self._language

    @property
    def sids(self):
        return self._sid_list

    def to_dict(self):
        return {"user_id": self.user_id, "language": self.language}

    def chats(self) -> Tuple[list, int]:
        """
        список чатов клиента

        :return: список чатов и число непрочитанных сообщений пользователя
        """
        with session() as ses:
            chats_list = get_chats_query(ses, self.user_id)

        res = [chat._asdict() for chat in chats_list]

        counter = 0
        if res:
            counter = sum((r["unseen_counter"] for r in res))

        return res, counter


class Chat(DictInterface):
    """Модель чата"""

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.messages = None
        self.subject = None

    def load_messages(self):
        with session() as ses:
            """
            
            Здесь должно быть получение по chat_id из БД
            
            """

            res = []

            self.messages = [r._asdict() for r in res]

        return self

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "chat_id": self.chat_id,
            "type": "init",
            "messages": self.messages
        }


class Message(DictInterface):
    """Модель сообщения"""

    def __init__(self, data: dict):
        self._from = Client(flask_session["from"])
        self._to = Client(data.get("to")) if "to" in data else None
        self.type = None
        self.subject = data.get("subject")
        self.chat_id = data.get("chat_id")
        self.message_id = data.get("message_id")
        self.broadcast = False
        self.timestamp = data.get("timestamp")
        self.time = data.get("time")

    @property
    def sender(self):
        return self._from

    @property
    def recipient(self):
        if self._to:
            return self._to

        if self.chat_id:
            # заполнение получателя по таблице связи чата и пользователей
            with session() as ses:
                user_id = ses.query(UserXChat.user_id). \
                    filter(UserXChat.chat_id == self.chat_id,
                           UserXChat.user_id != flask_session["from"]). \
                    scalar()

            self._to = Client(user_id)

            return self.recipient

    def to_dict(self) -> dict:
        """базовое преобразование, в наследниках дополняются детали"""
        msg = {
            "sender": self.sender.user_id if self.sender else None,
            "subject": self.subject,
            "chat_id": self.chat_id,
            "type": self.type,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "time": self.time
        }

        msg = {k: v for k, v in msg.items() if v is not None}

        return msg

    def send(self):
        if not self.type:
            raise NotImplementedError("Unresolved message type")

        if self.broadcast:
            emit(self.type, self.to_dict(), broadcast=True)
            return self

        if not self.recipient:
            return self

        for sid in self.recipient.sids:
            # отправка на все устройства получателя
            emit(self.type, self.to_dict(), to=sid)

        if self.sender:
            for sid in self.sender.sids:
                # отправка на другие устройства отправителя, если они у него есть
                if sid != flask_session["sid"]:
                    emit(self.type, self.to_dict(), to=sid)

        return self

    def reverse_recipients(self):
        """
        изменить направление пересылки
        """
        self._from, self._to = self._to, self._from

        return self

    def clear_from(self):
        self._from = None
        return self


class TextMessage(Message):
    """Сообщение с данными"""

    def __init__(self, data: dict):
        Message.__init__(self, data)
        self.type = MessageType.MESSAGE
        self.text = data.get("text")
        self.ext_key = data.get("extKey")
        self.translated = None

    def translate(self):
        """
        Перевести сообщение. Выполнить это действие можно только после сохранения в БД
        """
        if self.sender.language != self.recipient.language and self.message_id:
            try:
                self.translated, _ = translate_text(self.text, self.recipient.language, self.sender.language)
            except Exception as err:
                self.translated = self.text
                LOGGER.error(f"Не удалось перевести сообщение {self.message_id}: {str(err)}\n{format_exc()}")
            else:
                with session() as ses:
                    ses.add(ChatMessageTranslated(message_id=self.message_id,
                                                  language=self.recipient.language,
                                                  translated=self.translated))
                    ses.commit()

        return self

    def save_to_db(self):
        """
        запись сообщени в БД
        """
        with session() as ses:
            ses.add(msg := ChatMessage(chat_id=self.chat_id,
                                       sender=self.sender.user_id,
                                       receiver=self.recipient.user_id,
                                       text=self.text))
            ses.flush()

            self.timestamp = msg.timestamp
            self.time = msg.timestamp.split(" ")[1].rsplit(":", 1)[0]

            if self.translated:
                # запись переведенного сообщения
                ses.add(ChatMessageTranslated(message_id=msg.id,
                                              language=self.recipient.language,
                                              translated=self.translated))

            self.message_id = msg.id

            ses.commit()

        return self

    def to_dict(self) -> dict:
        res = super().to_dict()
        res.update({
            "text": self.text,
            "translated": self.translated
        })

        return res

    def push(self):
        """
        Отправка Push уведомления об отправленном пользователю сообщении
        """
        title_translate = get_cached_service_element(element_code='chat_push',
                                                     translate_code=self.recipient.language)
        if not title_translate:
            title_translate = get_cached_service_element(element_code='chat_push',
                                                         translate_code='en')
        message = messaging.Message(data={'time': get_pg_date(),
                                          'chat_id': self.chat_id,
                                          'url': f"{configs['domain']['url']}/chats/{self.chat_id}"},
                                    notification=Notification(title=title_translate.get('element_name'),
                                                              body=self.translated or self.text,
                                                              image='/img/Logo.svg'))
        for token in self.recipient.fcm_tokens:
            try:
                message.token = token
                messaging.send(message)
            except Exception as err:
                LOGGER.error(f"Не удалось доставить push уведомление пользователю (token: {token} "
                             f"{self.recipient.user_id}: {str(err)}\n{format_exc()}")

        return self


class ActionMessage(Message):
    """Сообщение с действием пользователя"""

    def __init__(self, data: dict, action: Actions = None):
        Message.__init__(self, data)
        self.type = MessageType.ACTION
        self.action: Actions = action or data.get("action")

        self.__chat_id = data.get("chat_id")
        self.__ext_key = data.get("extKey")
        self.__chats = None
        self.__chat = None
        self.__unseen_counter = None
        self.__chat_messages = None

    def do_action(self):
        # подготовка данных для активностей, исполнение активностей
        if self.action in (Actions.VIEWED, Actions.DELIVERED):
            with session() as ses:
                ses.query(ChatMessage).filter_by(id=self.message_id).update({self.action: True})
                ses.commit()

        if self.action == Actions.LOAD_CHATS:
            self.__chats, self.__unseen_counter = self.sender.chats()
            self.reverse_recipients()

        if self.action == Actions.LOAD_CHAT_MSG and self.__chat_id:
            self.__chat_messages = Chat(self.__chat_id).load_messages().messages
            self.reverse_recipients()

        if self.action == Actions.ONLINE or self.action == Actions.OFFLINE:
            with session() as ses:
                ses.query(Users).\
                    filter_by(user_id=self.sender.user_id).\
                    update({"online": self.action == Actions.ONLINE})
                ses.commit()
            self.broadcast = True

        if self.action == Actions.INIT_CHAT:
            with session() as ses:
                ses.add(chat := ChatTable(entity_id=self.subject))
                ses.flush()
                ses.add(UserXChat(user_id=self.sender.user_id, chat_id=chat.id))
                ses.add(UserXChat(user_id=self.recipient.user_id, chat_id=chat.id))
                ses.commit()
                self.__chat = get_chats_query(ses, self.sender.user_id, chat.id).one()._asdict()
            self.reverse_recipients()

        return self

    def to_dict(self) -> dict:
        res = super().to_dict()
        res["action"] = self.action

        if self.__chats is not None:
            res["chats"] = self.__chats
            res["unseen_counter"] = self.__unseen_counter

        if self.__chat:
            res["chat"] = self.__chat

        if self.__chat_messages is not None:
            res["chat_messages"] = self.__chat_messages

        if self.__ext_key:
            res["extKey"] = self.__ext_key

        return res
