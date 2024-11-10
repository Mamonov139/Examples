"""
Модуль с описанием входных и выходных структур
"""
from enum import Enum

from marshmallow import Schema, fields, validates, ValidationError, validates_schema

# ----------------------------------------------------------------------------------------------------------------------
#                                           Input schemas
# ----------------------------------------------------------------------------------------------------------------------
from models import session
from models.models import AD, Feedback
from services.auth.utils import jwt_required
from utils import current_user


class StoryActivityEnum(str, Enum):
    CLICK = 'click'
    SHOW = 'show'


class InputLoadServiceBase(Schema):
    entity_id = fields.Str(required=True, description="идентификатор")


class InputLoadServiceBaseWithOwner(InputLoadServiceBase):
    @validates('entity_id')
    @jwt_required()
    def validator_region(self, value):
        if current_user.get("is_admin"):
            # администратору разрешены любые действия с файлами
            return

        if 'user' in value:
            # валидация работы с аватаркой пользователя
            owner = current_user.get("user_id") == int(value.split("/")[1])
        elif 'fb' in value:
            # валидация работы с файлами отзывов
            with session() as ses:
                owner = ses.query(
                    ses.query(Feedback).filter_by(fb_id=int(value.split("/")[1]),
                                                  created_by=current_user.get("user_id")).exists()
                ).scalar()
        else:
            # валидация работы с файлами объявления
            with session() as ses:
                owner = ses.query(
                    ses.query(AD).filter_by(id=value, user_id=current_user.get("user_id")).exists()
                ).scalar()

        if not owner:
            raise ValidationError(f'Доступ запрещён')


class InputLoadServicePost(Schema):
    files = fields.Raw(type='file', description="файлы из input")


class InputLoadServiceDelete(Schema):
    filename = fields.Str(required=True, description="имя файла, который надо удалить")


class InputLoadStoriesBase(Schema):
    place_id = fields.Str(description="идентификатор сторис, если не передавть будут выданы все сторис")


class StorySaveActivity(Schema):
    item_id = fields.Int(description="идентификатор элемента истории", required=True)
    activity = fields.Enum(StoryActivityEnum,
                           by_value=False,
                           required=True,
                           description="событие")


# ----------------------------------------------------------------------------------------------------------------------
#                                           Output schemas
# ----------------------------------------------------------------------------------------------------------------------


class OutputLoadServiceMessage(Schema):
    message = fields.Str()


class OutputLoadServiceDict(Schema):
    files = fields.List(fields.Str(), description="список имен файлов")


class Activity(Schema):
    activity_label = fields.Str(description="текст активности")
    activity_url = fields.Str(description="ссылка")
    color = fields.Nested(type("Color", (Schema, ), {"color": fields.Str(description="код цвета")}))
    position = fields.Nested(type("Position", (Schema, ),
                                  {"position_right": fields.Str(description="расположение от левого края"),
                                   "position_top": fields.Str(description="расположение от верхнего края")}))
    background = fields.Nested(type("BackgroundColor", (Schema, ), {"color": fields.Str(description="код цвета")}))
    type = fields.Nested(type("Type", (Schema,), {"activity_type": fields.Str(description="тип активности"),
                                                  "height": fields.Int(description="Высота")}))


class OutputItemStories(Schema):
    storie_url = fields.Str(description="url видео")
    item_type = fields.Str(description="Тип сторис")
    item_num = fields.Int(description="порядок воспроизведения")
    activity = fields.Nested(Activity())
    timeline_theme = fields.Str(description="тема таймлайна")
    item_id = fields.Int(description="идентификатор элемента истории")
    background = fields.Nested(type("BackgroundColor", (Schema, ), {"color": fields.Str(description="код цвета")}))


class OutputLoadStoriesDict(Schema):
    place_id = fields.Int(description="Идендификатор сторис")
    storie_name = fields.Str(description="Имя сторис")
    preview_url = fields.Str(description="url обложки")
    created_by = fields.Int(description="Идендификатор создателя")
    created_date = fields.Str(description="Дата создания")
    story_item = fields.List(fields.Nested(OutputItemStories()))


class StoriesList(Schema):
    items = fields.List(fields.Nested(OutputLoadStoriesDict()), description="Список сторис")


class StoryActivity(Schema):
    msg = fields.Str(description="сообщение")
