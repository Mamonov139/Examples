"""
Модуль с ресурсами аутентификации и авторизации
"""
from datetime import datetime, timedelta
from json import loads
from secrets import token_urlsafe

from flask_apispec import marshal_with, doc, use_kwargs
from flask_apispec.views import MethodResource
from flask_jwt_extended import get_jwt, unset_access_cookies
from flask_restful import Resource
from jwt import get_unverified_header

from configs import configs
from models.connection import get_redis_client
from resources.auth.schemas import TelegramAuthData, AuthorizationToken, SECURITY, Unauthorized, Revoked, \
    GoogleAuthData, EmailAuthData, EmailConfirmAuthData, EmailResponse, Nonce, EmailPassword, AppleAuthData, \
    TokenCookie, ProfileDeleteData, ProfileDeleteResponse, TokenHeader
from services.auth.utils import get_init_data, REDIS_BLOCK_LIST, prepare_token_response, jwt_required
from services.profile_user.service import user_tg_processing, user_google_processing, user_email_processing, \
    user_apple_processing, user_delete_request_processing
from utils import resp, current_user


class TgAuthAPI(MethodResource, Resource):
    """
    API аутентификации
    """

    @doc(description='аутентификация через телеграм', tags=['Аутентификация'])
    @use_kwargs(TelegramAuthData, location='query')
    @marshal_with(AuthorizationToken, code=200)
    def get(self, **kwargs):
        """
        получение токена в обмен на валидные данные о пользователе от TG
        """
        if "init_data" in kwargs:
            # webapp case
            user_data = loads(get_init_data(kwargs['init_data']).get("user"))
        elif "token" in kwargs:
            # ios case
            user_data = get_unverified_header(kwargs["token"] + '..')
        else:
            # widget case
            user_data = kwargs

        user_id = user_tg_processing(user_data)

        response = prepare_token_response(user_id)

        return response

    @doc(description='отклонение токена', tags=['Аутентификация'], security=SECURITY)
    @marshal_with(Revoked, code=200)
    @marshal_with(Unauthorized, code=401)
    @jwt_required()
    def delete(self):
        jwt = get_jwt()
        if 'exp' in jwt:
            exp = timedelta(seconds=jwt['exp'] - int(datetime.timestamp(datetime.now())))
        else:
            exp = None

        REDIS_BLOCK_LIST.set(jwt["jti"], "", ex=exp)
        data = {
            'msg': 'token revoked'
        }
        response = resp(data, 200)
        unset_access_cookies(response)

        return response


class AuthGoogleAPI(MethodResource, Resource):
    """
    API аутентификации через Google
    """

    @doc(description='аутентификация через google', tags=['Аутентификация'])
    @use_kwargs(GoogleAuthData, location='json')
    @marshal_with(Unauthorized, code=401)
    def post(self, **kwargs):
        """
        Верификация одноразового токена от Google ID и выдача нашего токена для доступа к приложению
        """

        user_id = user_google_processing(kwargs['user'])

        response = prepare_token_response(user_id)

        return response


class AuthAppleAPI(MethodResource, Resource):
    """
    API аутентификации через Apple ID
    """

    @doc(description="аутентификация через apple ID", tags=['Аутентификация'])
    @use_kwargs(AppleAuthData, location='json')
    @marshal_with(Unauthorized, code=401)
    def post(self, **kwargs):
        """
        Верификация одноразового токена от Apple ID и выдача нашего токена для доступа к приложению
        """

        user_id = user_apple_processing(kwargs)

        response = prepare_token_response(user_id)

        return response


class CurrentUser(MethodResource, Resource):
    """
    API текущего пользователя
    """

    @doc(description='данные пользователя', tags=['Текущий пользователь'], security=SECURITY)
    @marshal_with(Unauthorized, code=401)
    @use_kwargs(TokenCookie, location='cookies')
    @use_kwargs(TokenHeader, location='headers')
    @jwt_required()
    def get(self, **kwargs):
        jwt = kwargs.get("jwt_cookie", kwargs.get("jwt_header", ""))
        return resp(current_user._get_current_object() | {"jwt": jwt}, 200)


class Email(MethodResource, Resource):

    @doc(description='регистрация email', tags=['Аутентификация'])
    @use_kwargs(EmailAuthData, location='json')
    @marshal_with(EmailResponse, code=200)
    def post(self, **kwargs):

        if "password" in kwargs:
            # вход пользователя
            response = prepare_token_response(kwargs["user_id"])
            return response

        # Регистрация и восстановление пароля
        _, code = user_email_processing(kwargs)
        redis = get_redis_client(configs.get('redis').get('verification_db'))
        redis.set(kwargs["email"], code, ex=300)
        return {"msg": "отправлен код подтверждения"}, 200


class EmailConfirm(MethodResource, Resource):

    @doc(description='проверка атворизационного кода', tags=['Аутентификация'])
    @use_kwargs(EmailConfirmAuthData, location='query')
    @marshal_with(Nonce, code=200)
    def post(self, **kwargs):
        redis = get_redis_client(configs.get('redis').get('verification_db'))
        redis.set(kwargs["email"], nonce := token_urlsafe(), ex=300)
        return {"nonce": nonce}, 200


class EmailCreatePassword(MethodResource, Resource):

    @doc(description='регистрация/восстановление пароля', tags=['Аутентификация'])
    @use_kwargs(EmailPassword, location='json')
    def post(self, **kwargs):
        user_id, _ = user_email_processing(kwargs)
        response = prepare_token_response(user_id)
        redis = get_redis_client(configs.get('redis').get('verification_db'))
        redis.delete(kwargs["email"])
        return response


class ProfileDelete(MethodResource, Resource):

    @doc(description='регистрация заявки на удаление профиля', tags=['Текущий пользователь'])
    @use_kwargs(ProfileDeleteData, location='json')
    @marshal_with(ProfileDeleteResponse, code=200)
    @marshal_with(Unauthorized, code=401)
    @jwt_required()
    def post(self, **kwargs):
        response = user_delete_request_processing(user_id=current_user['user_id'], comment=kwargs['comment'])
        return response
