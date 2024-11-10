"""
Модуль с общим функционалом пакета API ресурсов
"""
from json import loads, dumps

from configs import configs
from models.connection import get_redis_client


class RedisDict(dict):
    """
    Адаптер для редиса
    """

    def __init__(self, db: int = configs.get('redis').get('socket_db')):
        dict.__init__(self)
        self.__redis = get_redis_client(db)

    def __getitem__(self, key):
        res: str = self.__redis.get(key)

        if not res:
            raise KeyError(key)

        return loads(res)

    def __setitem__(self, key, value):
        self.__redis.set(key, dumps(value))

    def get(self, key, default=None):
        res: str = self.__redis.get(key)
        return loads(res) if res else default
