from datetime import timedelta, datetime
from hashlib import sha256
import hmac
from time import time, mktime
from urllib.parse import parse_qsl, unquote

from flask import Response, g
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required as jwt_required_extended, \
    current_user
from flask_jwt_extended.exceptions import RevokedTokenError, NoAuthorizationError
from jwt import ExpiredSignatureError, DecodeError, encode
from werkzeug.datastructures import ImmutableDict

from configs import configs
from models import with_session
from models.connection import get_redis_client
from models.models import Users, Region
from services.auth.enums import Timing
from utils import resp


REDIS_BLOCK_LIST = get_redis_client(configs.get('redis').get('token_db'))


def get_init_data(init_data: str) -> dict:
    """
    Распаковка WebAppInitData

    :param init_data: данные от TG в виде параметров строки запроса
    """
    data = dict(parse_qsl(init_data))

    return data


def validate_init_data(init_data: dict) -> bool:
    """
    Проверка подписи

    :param init_data: данные от ТГ в разобранном виде
    """

    original_hash = init_data.pop('hash', None)

    data_check_string = unquote('\n'.join((f'{k}={v}' for k, v in sorted(init_data.items(), key=lambda x: x[0]))))

    if 'user' in init_data:
        # webapp case
        secret_key = hmac.new(
            bytes("WebAppData", 'utf-8'),
            msg=bytes(configs.get('bot').get('token'), 'utf-8'),
            digestmod=sha256
        ).digest()
    else:
        # widget case
        secret_key = sha256(bytes(configs.get('bot').get('token'), 'utf-8')).digest()

    new_hash = hmac.new(
        secret_key,
        msg=bytes(data_check_string, 'utf-8'),
        digestmod=sha256
    ).hexdigest()

    return new_hash == original_hash


@with_session()
def get_user_from_token_sub(ses, user_id):
    """
    Получение пользователя из токена по TG_ID
    """
    user = ses.query(Users).get(user_id)
    user_dict = user.to_dict(rules=('-ads', '-region', '-password_hash'))
    country_id = ses.query(Region.country_id).filter(Region.id == user_dict.get("region_id", None)).scalar()
    user_dict.update({'country_id': country_id})
    return user_dict


def get_anonymous_user():
    """
    Данный объект будет возвращён для эндпоинтов с опциональным токеном
    """
    return ImmutableDict({"user_id": 0})


def prepare_token_response(user_id: int) -> Response:
    """
    Генерация ответа с токеном

    :param user_id: идентификатор пользователя
    """

    if configs.get('mode') == 'dev':
        # в пежиме разработки ключ не имеет время жизни
        expires = False
    elif configs.get('mode') == 'test':
        expires = Timing.EXP_DEV.value
    else:
        expires = Timing.EXP.value

    token = create_access_token(identity=user_id, expires_delta=expires)

    data = {
        'expired_at': expires.total_seconds() if expires is not False else -1,
        'jwt': token
    }

    response = resp(data, 200)

    if configs.get('mode') != 'dev':
        # работа с cookie только на тестовом и прод контурах
        set_access_cookies(response, token, max_age=expires)

    return response


def jwt_required(optional=False):
    """
    Декоратор авторизации с более широким пониманием атрибута optional. Если использовать этот
    декоратор, optional не проверяет токен на истечение срока жизни, на нахождение в списке
    откланённых токенов и на валидность. При этом в таком эндпоинте объект CU будет представлять из себя пустой
    неизменяемый словарь, сохраняя интерфейс взаимодействия

    Если использовать этот декоратор без optional, то ошибки валидации токена приведут к 401 ответу

    :param optional: Опциональное применение (сохраняет контекст при отсутсвии или при наличии невалидного токена)
    """

    def wrapper(func):
        def decorator(*args, **kwargs):
            try:
                res = jwt_required_extended()(func)(*args, **kwargs)
            except (RevokedTokenError, ExpiredSignatureError, DecodeError, NoAuthorizationError) as error:
                if optional:
                    g._jwt_extended_jwt = {}
                    g._jwt_extended_jwt_user = {"loaded_user": get_anonymous_user()}
                    res = func(*args, **kwargs)
                else:
                    if isinstance(error, RevokedTokenError):
                        msg = "has been revoked"  # откланён
                    elif isinstance(error, ExpiredSignatureError):
                        msg = "has expired"  # истёк
                    elif isinstance(error, DecodeError):
                        msg = "invalid"  # некорректный
                    elif isinstance(error, NoAuthorizationError):
                        msg = "missing"  # отсутсвует
                    else:
                        msg = ""
                    res = resp({"msg": f"token {msg}"}, 401)
            return res
        return decorator
    return wrapper


def admin_required():
    def check_admin():
        if not current_user.get('is_admin'):
            return resp({'msg': 'admin required'}, 403)

    def wrapper(func):
        def decorator(*args, **kwargs):
            res = jwt_required()(check_admin)()
            if res:
                return res
            return func(*args, **kwargs)
        return decorator
    return wrapper
