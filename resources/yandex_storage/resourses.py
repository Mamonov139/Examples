"""
Модуль с ресурсами для работы с файлами
"""

from flask_apispec import doc, use_kwargs, marshal_with, MethodResource
from flask_restful import Resource

from resources.auth.schemas import SECURITY, Unauthorized
from resources.yandex_storage.schemas import OutputLoadServiceDict, InputLoadServiceBase, InputLoadServicePost, \
    InputLoadServiceDelete, OutputLoadServiceMessage, InputLoadServiceBaseWithOwner, InputLoadStoriesBase, StoriesList, \
    StoryActivity, StorySaveActivity
from services.auth.utils import jwt_required
from services.yandex_storage.service import loader_post, loader_get, loader_delete, stories_get
from services.yandex_storage.utils import registrate_story_activity


@doc(security=SECURITY)
@marshal_with(Unauthorized, code=401)
class FilesApi(MethodResource, Resource):
    """
    API работы с документами
    """

    method_decorators = {"post": (jwt_required(), ), "delete": (jwt_required(), )}

    @doc(description='Сохранение файла или файлов по айди объявление', tags=['Файлы'])
    @use_kwargs(InputLoadServiceBaseWithOwner, location='query')
    @use_kwargs(InputLoadServicePost, location='files')
    @marshal_with(OutputLoadServiceDict, code=200)
    def post(self, **kwargs):
        """
        Контроллер принимающий документы
        """

        return loader_post(kwargs['entity_id'], kwargs['files'])

    @doc(description='Получение файлов по айди объявление', tags=['Файлы'])
    @use_kwargs(InputLoadServiceBase, location='query')
    @marshal_with(OutputLoadServiceDict, code=200)
    def get(self, **kwargs):
        """
        Контроллер, отправляющий документы
        """

        return loader_get(kwargs['entity_id'])

    @doc(description='Удаление файла по айди объявление', tags=['Файлы'])
    @use_kwargs(InputLoadServiceBaseWithOwner, location='query')
    @use_kwargs(InputLoadServiceDelete, location='query')
    @marshal_with(OutputLoadServiceMessage, code=200)
    def delete(self, **kwargs):
        """
        Контроллер, удаляющий документы
        """

        return loader_delete(kwargs['entity_id'], kwargs['filename'])


@doc(security=SECURITY)
@marshal_with(Unauthorized, code=401)
class FilesStoriesApi(MethodResource, Resource):
    """
    API работы с материалами сторис
    """

    method_decorators = {"post": (jwt_required(), )}

    @doc(description='Сохранение файлов сторис', tags=['Сторис'])
    @use_kwargs(InputLoadServiceBaseWithOwner, location='query')
    @use_kwargs(InputLoadServicePost, location='files')
    @marshal_with(OutputLoadServiceDict, code=200)
    def post(self, **kwargs):
        """
        Контроллер принимающий документы
        """

        pass

    @doc(description='Получение файлов сторис', tags=['Сторис'])
    @use_kwargs(InputLoadStoriesBase, location='query')
    @marshal_with(StoriesList, code=200)
    def get(self, **kwargs):
        """
        Контроллер, отправляющий документы
        """

        data = stories_get(kwargs.get('place_id', 0))
        out = {"items": data}
        return out, 200

    @doc(description='Регистрация событий', tags=['Сторис'])
    @use_kwargs(StorySaveActivity, location='json')
    @marshal_with(StoryActivity, code=200)
    @jwt_required(optional=True)
    def patch(self, **kwargs):
        """
        регистрация действия с объявлением
        """

        registrate_story_activity(**kwargs)

        return {"msg": f"{kwargs['activity']} saved"}, 200
