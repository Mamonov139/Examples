from enum import Enum
from typing import Tuple

from google.cloud import translate_v2 as translate
from sqlalchemy import func, and_
from sqlalchemy.orm import aliased

from models.models import ChatMessage, Users, AD, Currency, ChatMessageTranslated, UserXChat, Chat as ChatTable


UserXChat2: UserXChat = aliased(UserXChat)


class Actions(str, Enum):
    TYPING = "typing"
    STOP_TYPING = "stop_typing"
    ONLINE = "online"
    OFFLINE = "offline"
    INIT_CHAT = "init_chat"
    VIEWED = "viewed"
    DELIVERED = "delivered"
    NOT_DELIVERED = "not_delivered"
    LOAD_CHATS = "load_chats"
    LOAD_CHAT_MSG = "load_chat_msg"


class MessageType(str, Enum):
    MESSAGE = "message"
    ACTION = "action"


def translate_text(text: str, target: str, source: str = None) -> Tuple[str, str]:
    """
    Перевод текста на указанный язык с автоматическим определением исходного

    :param text: исходный текст
    :param target: целевой язык в виде ISO 639-1 кода
    :param source: исходный язык в виде ISO 639-1 кода, если не указан - детектируется автоматически

    :return: кортеж из переведённого текста и ISO кода детектированного языка исходного сообщения
    """

    translate_client = translate.Client()

    result = translate_client.translate(text, target_language=target, source_language=source)

    return result["translatedText"], source or result["detectedSourceLanguage"]


def get_chats_query(ses, user_id: int, chat_id: int = None):
    """

    Здесь должно быть получения чатов пользователя, оно завязано на бизнес логику поэтому тут не приведено

    """
    chats_list = []

    return chats_list
