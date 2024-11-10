"""
Модуль с функциями для работы с почтой
"""
from random import randint


def verification_code() -> str:
    """
    Генерация 4-х знакового кода подтверждения
    """

    return ''.join(tuple(str(randint(0, 9)) for i in range(4)))
