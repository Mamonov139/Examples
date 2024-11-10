"""
Модуль подклчения к базе данных
"""

from functools import wraps
from contextlib import contextmanager

from urllib.parse import quote

from redis import StrictRedis
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from configs import configs
from main.celery_config import broker_url

from .enums import DbName


def make_engine(db_name: DbName):
    """
    Создание движка БД

    :param db_name: название базы
    """

    pg_config = configs.get('postgres')
    password = quote(pg_config.get('password'))
    user = pg_config.get('username')
    host = pg_config.get('host')
    port = pg_config.get('port')
    hostname = f'{host}:{port}' if port else host
    engine_string = f'postgresql://{user}:{password}@{hostname}/{db_name.value}'
    engine = create_engine(engine_string)

    return engine


def make_session(db_name: DbName):
    """
    Создание класса сессии

    :param db_name: имя базы данных
    """

    return sessionmaker(bind=make_engine(db_name))()


@contextmanager
def session(db_name: DbName = DbName.REXPAT):
    """
    Контекстный менеджер для работы с сессией БД\

    :param db_name: имя базы данных
    """

    ses = make_session(db_name)
    try:
        yield ses
    finally:
        ses.close()


def with_session(db_name: DbName = DbName.REXPAT):
    """
    Декоратор с параметром для предоставления функциям объякта сессии для взаимодействия с базой данных

    :param db_name: имя базы данных для подключения
    """

    def with_session_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sql_session = make_session(db_name)
            try:
                res = func(sql_session, *args, **kwargs)
            finally:
                sql_session.close()
            return res

        return wrapper

    return with_session_decorator


def get_redis_client(db: int = None) -> StrictRedis:
    REDIS = configs.get('redis')

    return StrictRedis(host=REDIS['host'],
                       port=REDIS['port'],
                       db=db or REDIS['db'],
                       password=REDIS['password'],
                       decode_responses=True)


def get_redis_connection_url(db: int = None) -> str:
    REDIS = configs.get('redis')
    pw_string = f':{REDIS["password"]}@' if REDIS["password"] else ''
    return f'redis://{pw_string}{REDIS["host"]}:{REDIS["port"]}/{db or REDIS["db"]}'
