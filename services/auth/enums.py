"""
Перечисления для аторизации
"""

from datetime import timedelta
from enum import Enum


class Timing(Enum):
    EXP = timedelta(days=30)
    EXP_DEV = timedelta(days=30)
    REFRESH_DELTA = timedelta(days=7)
