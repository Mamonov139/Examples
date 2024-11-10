"""
Пакет средств для логирования
"""

import logging

from logging import CRITICAL, FATAL, ERROR, WARNING, INFO, DEBUG, NOTSET

from logger.logger import get_logger


logging.addLevelName(logging.INFO, 'II')
logging.addLevelName(logging.ERROR, 'EE')
logging.addLevelName(logging.WARNING, 'WW')


__all__ = ('get_logger', 'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET')
