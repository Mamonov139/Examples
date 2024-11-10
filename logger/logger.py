"""
модуль с функцие получения логировщика
"""

import logging
from os import path

from logging.handlers import TimedRotatingFileHandler


ff = logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def get_logger(name: str, file_name: str, level: int = logging.INFO):
    """
    Функция формирует объект логировщика для записи данных о работе приложения в файл

    :param name: имя логировщика
    :param file_name: имя файла, в который будут записываться логи
    :param level: уровень записи информации
    :return: объект логировщика
    """
    logs_path = path.join(path.split(path.dirname(path.abspath(__file__)))[0], 'logs', file_name + '.log')
    handler = TimedRotatingFileHandler(logs_path,
                                       when='D',
                                       interval=1,
                                       backupCount=30,
                                       encoding='utf-8',
                                       delay=True)
    handler.setLevel(level)
    handler.setFormatter(ff)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
