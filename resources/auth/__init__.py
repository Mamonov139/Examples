"""
Пакет ресурса аутентификации и авторизации
"""
from flask import Blueprint


__all__ = ('auth_bp', )


auth_bp = Blueprint('auth', __name__)
