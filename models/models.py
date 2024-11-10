"""
Модели таблиц базы данных
"""

from datetime import datetime

import sqlalchemy as db

from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_serializer import SerializerMixin

Base = declarative_base()


def get_pg_date(d_t: datetime = None) -> str:
    """
    Получить текущую или отформатировать имеющуюся дату к формату PostgreSQL

    :param d_t: дата-время
    """

    if not d_t:
        d_t = datetime.now()
    return d_t.strftime("%Y-%m-%d %H:%M:%S")

class Documents(Base, SerializerMixin):
    """
    Документы
    """

    __table_args__ = {'schema': 'main'}
    __tablename__ = 'media_file'

    def __init__(self, **kwargs):
        # Явное указание конструктора
        Base.__init__(self, **kwargs)

    entity_id = db.Column(db.String, primary_key=True, nullable=False)
    filename = db.Column(db.String(), primary_key=True, nullable=False)


class Users(Base, SerializerMixin):
    """
    Пользователи общие атрибуты
    """

    __table_args__ = (db.UniqueConstraint("user_id"),
                      {'schema': 'main'})
    __tablename__ = 'users'

    def __init__(self, **kwargs):
        # Явное указание конструктора
        Base.__init__(self, **kwargs)

    user_id = db.Column(db.Integer, primary_key=True, nullable=False)
    email = db.Column(db.String)
    username = db.Column(db.String)
    can_set_contact = db.Column(db.Boolean)
    region_id = db.Column(db.Integer, db.ForeignKey('main.region.id'))
    creation_date = db.Column(db.TIMESTAMP, default=get_pg_date)
    banned = db.Column(db.Boolean)
    phone = db.Column(db.String)
    whats_app_phone = db.Column(db.String)
    description = db.Column(db.String)
    first_name = db.Column(db.String)
    second_name = db.Column(db.String)
    middle_name = db.Column(db.String)
    photo = db.Column(db.String)
    pw_hash = db.Column(db.String)
    is_confirmed = db.Column(db.Boolean)
    is_tg_hide = db.Column(db.Boolean)
    is_email_hide = db.Column(db.Boolean)
    is_wa_hide = db.Column(db.Boolean)
    is_phone_hide = db.Column(db.Boolean)
    is_admin = db.Column(db.Boolean)
    register_type = db.Column(db.String)
    google_id = db.Column(db.String)
    apple_id = db.Column(db.String)
    telegram_id = db.Column(db.Integer)
    password_hash = db.Column(db.String)
    wa_ccc = db.Column(db.Integer)
    tg_ccc = db.Column(db.Integer)
    phone_ccc = db.Column(db.Integer)
    phone_iso_code = db.Column(db.String(16))
    wa_iso_code = db.Column(db.String(16))
    language_id = db.Column(db.String(8), db.ForeignKey("dictionary.languages.language_code"))
    online = db.Column(db.Boolean)
    delete_request = db.Column(db.Boolean)

class Languages(Base, SerializerMixin):
    """
    Справочник ISO кодов языков, поддерживаемых переводчиком
    """
    __table_args__ = {'schema': 'dictionary'}
    __tablename__ = 'languages'

    language_code = db.Column(db.String(8), primary_key=True)
    display_name = db.Column(db.String(32))
    display_name_ru = db.Column(db.String(32))
    active = db.Column(db.Boolean, default=False)


class Tags(Base, SerializerMixin):
    """
    Таблица тегов
    """
    __table_args__ = {'schema': 'dictionary'}
    __tablename__ = 'tags'

    def __init__(self, **kwargs):
        # Явное указание конструктора
        Base.__init__(self, **kwargs)

    tag_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_category_id = db.Column(db.Integer)
    tag_category = db.Column(db.String(128))
    tag_name_id = db.Column(db.Integer)
    tag_name = db.Column(db.String(128))


class Chat(Base):
    """
    Чаты
    """

    __table_args__ = {'schema': 'chat'}
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_id = db.Column(db.Integer)
    is_closed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.TIMESTAMP, default=get_pg_date)


class UserXChat(Base):
    """
    Участники чата
    """

    __table_args__ = {'schema': 'relation'}
    __tablename__ = 'user_x_chat'

    user_id = db.Column(db.Integer, db.ForeignKey("main.users.user_id"), primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.chats.id"), primary_key=True)


class UserRequest(Base):
    """
    Таблица пользовательских заявок (в т.ч. удаление профиля)
    """
    __table_args__ = {'schema': 'main'}
    __tablename__ = 'request'

    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_type = db.Column(db.String(32))
    created_by = db.Column(db.Integer)
    created_date = db.Column(db.TIMESTAMP, default=get_pg_date)
    close_date = db.Column(db.TIMESTAMP)
    comment = db.Column(db.String(512))

