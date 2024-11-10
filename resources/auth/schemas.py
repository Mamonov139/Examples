"""
МОдуль с описанием входных и выходных структур
"""
from datetime import timedelta
from requests import get, post
from jwt import get_unverified_header, decode

from marshmallow import Schema, fields, ValidationError, validates_schema
from werkzeug.security import check_password_hash

from configs import configs
from models.connection import get_redis_client, session
from models.models import Users
from services.auth.utils import validate_init_data, get_init_data, get_apple_client_secret


SECURITY = [{'JWT': ['token']}]
EXP = timedelta(hours=2)

# ----------------------------------------------------------------------------------------------------------------------
#                                           Input schemas
# ----------------------------------------------------------------------------------------------------------------------


class TelegramAuthData(Schema):
    # webapp case
    init_data = fields.Str(description="данные для аутентификации пользователя TG", allow_none=False)
    # ios case
    token = fields.Str(description="данные для аутентификации пользователя TG", allow_none=False)
    # widget case
    id = fields.Str(description="идентификатор телеграмм")
    first_name = fields.Str(description="Имя")
    last_name = fields.Str(description="Фамиллия")
    username = fields.Str(description="ник телеграмм")
    photo_url = fields.Str(description="ссылка на фото")
    auth_date = fields.Str(description="метка времени начала процесса аутентификации")
    hash = fields.Str(description="хэш сумма для валидации аутентификации")

    @validates_schema(skip_on_field_errors=True)
    def schema_validator(self, data, **kwargs):
        if sum(('init_data' in data, 'id' in data, 'token' in data)) != 1:
            raise ValidationError('Одновременно доступен только один способ авторизации')
        if 'init_data' in data:
            valid = validate_init_data(get_init_data(data["init_data"]))
        elif 'token' in data:
            valid = validate_init_data(get_unverified_header(data["token"] + '..'))
        else:
            valid = validate_init_data(data)

        if not valid:
            raise ValidationError('подлинность подписи не подтверждена')


class GoogleAuthData(Schema):
    credential = fields.Str(description="токен пользователя", required=True)

    @validates_schema(skip_on_field_errors=True)
    def validate_token(self, data, **kwargs):
        try:
            resp = get('https://www.googleapis.com/oauth2/v1/userinfo',
                       params={'alt': 'json',
                               'access_token': data["credential"]},
                       timeout=10)
            if resp.status_code == 401:
                raise ValidationError('wrong credential')
            if resp.status_code >= 500:
                raise ValidationError('GAPI internal error')
            data["user"] = resp.json()  # далее передаются данные о пользователе, не токен
        except Exception as error:
            raise ValidationError(f'unable to fetch user info from GAPI {str(error)}') from error


class AppleAuthCredential(Schema):
    code = fields.Str(description='код авторизации', required=True)
    id_token = fields.Str(description='токен идентификации', required=True)
    state = fields.Str(required=False)


class AppleAuthUsername(Schema):
    firstName = fields.Str(description='имя пользователя', attribute='first_name', required=True)
    lastName = fields.Str(description='фамилия пользователя', attribute='last_name', required=True)


class AppleAuthUser(Schema):
    email = fields.Str(description='адрес электронной почты пользователя', required=True)
    name = fields.Nested(AppleAuthUsername(), description='полное имя пользователя', required=True)


class AppleAuthData(Schema):
    credential = fields.Nested(AppleAuthCredential(),
                               description='данные для идентификации пользователя',
                               required=True)
    user = fields.Nested(AppleAuthUser(),
                         description='объект с информацией о пользователе',
                         required=False)

    @validates_schema(skip_on_field_errors=True)
    def validate_token(self, data, **kwargs):
        try:
            credential = data['credential']
            token = decode(credential['id_token'], options={"verify_signature": False})
            resp = post('https://appleid.apple.com/auth/token',
                        data={'client_id': token['aud'],
                              'client_secret': get_apple_client_secret(client_id=token['aud']),
                              'grant_type': 'authorization_code',
                              'code': credential['code'],
                              'redirect_uri': configs.get('apple_id').get('redirect_uri')})
            if resp.status_code == 400:
                raise ValidationError('wrong credential')
            if resp.status_code >= 500:
                raise ValidationError('AppleAPI internal error')
            data['id'] = token['sub']
        except Exception as error:
            raise ValidationError(f'unable to fetch user info from AppleAPI {str(error)}') from error


class EmailAuthData(Schema):
    email = fields.Str(description="email нового пользователя или существующего (для входа на сайт)", required=True)
    password = fields.Str(description="пароль пользователя (для входа на сайт)", required=False, allow_none=False)
    forgot_flag = fields.Boolean(description="флаг восстановления пароля",
                                 required=False,
                                 allow_none=False,
                                 load_default=False)

    @validates_schema(skip_on_field_errors=True)
    def validate_token(self, data, **kwargs):
        # валидация пароля
        with session() as ses:
            user = ses.query(Users).filter_by(email=data["email"].lower()).one_or_none()

        if 'password' in data and not data["forgot_flag"]:
            # Вход по логину/паролю
            if user is None:
                raise ValidationError({'email': 'Пользователь не найден'})
            elif not check_password_hash(user.password_hash or '', data['password']):
                raise ValidationError({'password': 'Неправильный пароль'})
            data["user_id"] = user.user_id
        elif 'password' not in data and data["forgot_flag"]:
            # Восстановление пароля
            if user is None:
                raise ValidationError({'email': 'Пользователь не найден'})
        elif 'password' not in data and not data["forgot_flag"]:
            # Регистрация
            if user is not None and user.password_hash is not None:
                raise ValidationError({'email': 'Пользователь с таким email уже зарегистрирован'})
        else:
            raise ValidationError("Некорректный запрос")


class EmailConfirmAuthData(Schema):
    email = fields.Str(description="email", required=True)
    code = fields.Str(description="код подтверждения", required=True)

    @validates_schema(skip_on_field_errors=True)
    def validate_token(self, data, **kwargs):
        redis = get_redis_client(configs.get('redis').get('verification_db'))
        if (code := redis.get(data['email'])) is None:
            raise ValidationError({'code': 'Код устарел'})
        if code != data['code']:
            raise ValidationError({'code': 'Неправильный код'})


class EmailPassword(Schema):
    email = fields.Str(description="email", required=True)
    password = fields.Str(description="пароль", required=True)
    nonce = fields.Str(description="одноразовый код валидации", required=True)

    @validates_schema(skip_on_field_errors=True)
    def validate_token(self, data, **kwargs):
        redis = get_redis_client(configs.get('redis').get('verification_db'))
        if (nonce := redis.get(data['email'])) is None:
            raise ValidationError({'nonce': 'время сессии истекло'})
        if nonce != data['nonce']:
            raise ValidationError('некорректный одноразовый код')


class TokenCookie(Schema):
    access_token_cookie = fields.Str(description="токен авторизации", attribute="jwt_cookie")


class TokenHeader(Schema):
    authorization = fields.Str(description="токен авторизации", attribute="jwt_header")


# ----------------------------------------------------------------------------------------------------------------------
#                                           Output schemas
# ----------------------------------------------------------------------------------------------------------------------


class AuthorizationToken(Schema):
    expired_at = fields.Int(description="Время жизни токена (-1 для безлимитного)")
    jwt = fields.Str(description="Токен доступа")


class Unauthorized(Schema):
    msg = fields.Str()


class Forbidden(Schema):
    msg = fields.Str()


class Revoked(Schema):
    msg = fields.Str()


class EmailResponse(Schema):
    msg = fields.Str(description="сообщение")


class Nonce(Schema):
    nonce = fields.Str(description="одноразовый код валидации")


class ProfileDeleteData(Schema):
    comment = fields.Str(description="комментарий к заявке на удаление профиля")


class ProfileDeleteResponse(Schema):
    msg = fields.Str()
