"""
Модуль с общими функциями проекта
"""
from typing import Union, Optional
from uuid import uuid4

from flask import make_response, jsonify
from flask_jwt_extended import current_user
from telebot import TeleBot
from werkzeug import Response

from configs import configs


current_user: dict = current_user

TELEGRAM_BOT = TeleBot(configs.get("bot").get("token"))

SECONDS_PER_DAY = 86400


def resp(data: Union[str, dict, list], status: int) -> Response:
    """
    Общий ответ API

    :param data: строка или словарь
    :param status: цифровой код HTTP ответа
    """

    return make_response(jsonify(data), status)


def uuid(plain=False):
    """
    строка с уникальным идентификатором
    """
    if plain:
        return str(uuid4()).replace('-', '')

    return str(uuid4())


class ServiceError(Exception):
    default_detail = 'Internal service error'
    detail = ''

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = self.default_detail

        self.detail = detail
        self.status_code = status_code

    def __str__(self):
        return str(self.detail)

