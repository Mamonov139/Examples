"""
Модуль создания экземпляра приложения
"""
from datetime import datetime
from os import path

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Flask, request
from flask_apispec import FlaskApiSpec
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt, create_access_token, set_access_cookies
from flask_restful import abort
from marshmallow import fields

from webargs.flaskparser import parser

from configs import configs
from main.cache import CACHE
from resources import PublicAPI
from resources.chat import socket_io
from services.auth.enums import Timing
from services.auth.utils import REDIS_BLOCK_LIST, get_user_from_token_sub, jwt_required
from utils import SECONDS_PER_DAY


MM_PLUGIN = MarshmallowPlugin()


def create_app():
    """
    Создание объекта приложения
    """
    app = Flask(__name__)
    jwt = JWTManager(app)

    app.config['SECRET_KEY'] = configs.get('flask').get('secret')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['JSON_AS_ASCII'] = False
    app.config['JWT_SECRET_KEY'] = configs.get('flask').get('secret')
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']  # порядок определяет приоритет
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_COOKIE_SAMESITE'] = "Strict"
    app.config['JWT_COOKIE_DOMAIN'] = configs.get('domain').get('domain')
    app.config['JWT_HEADER_TYPE'] = ''
    app.config['JWT_ALGORITHM'] = 'RS256'
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_HOST'] = configs.get('redis').get('host')
    app.config['CACHE_REDIS_PORT'] = configs.get('redis').get('port')
    app.config['CACHE_REDIS_PASSWORD'] = configs.get('redis').get('password')
    app.config['CACHE_REDIS_DB'] = configs.get('redis').get('cache_db')
    app.config['CACHE_DEFAULT_TIMEOUT'] = SECONDS_PER_DAY

    CACHE.init_app(app)
    CACHE.clear()

    # доступ к API при локальной разработке
    CORS(app,
         resourses={r"/api*": {"origin": configs.get('cors').get('origins')}},
         supports_credentials=True)

    if configs.get('mode') != 'release':
        # документация доступна только в среде разработки
        app.config['APISPEC_SWAGGER_URL'] = '/docs'
        app.config['APISPEC_SWAGGER_UI_URL'] = '/docs-ui'

    with open(path.join('.', 'main', 'rs256.pem'), mode='rb') as private:
        app.config['JWT_PRIVATE_KEY'] = private.read()
    with open(path.join('.', 'main', 'rs256.pub'), mode='rb') as public:
        app.config['JWT_PUBLIC_KEY'] = public.read()

    docs = None

    if configs.get('mode') != 'release':
        # документация доступна только в среде разработки
        with open(path.join('.', 'main', 'api_description.html'), 'r', encoding='utf-8') as file:
            description = file.read()

        app.config['APISPEC_SPEC'] = APISpec(
            title='Rexpat API',
            version='1.0.0',
            plugins=[MM_PLUGIN],
            openapi_version='2.0',
            info={"description": description}
        )

        api_key_scheme = {"type": "apiKey", "in": "header", "name": "Authorization"}
        app.config['APISPEC_SPEC'].components.security_scheme("JWT", api_key_scheme)

        docs = FlaskApiSpec(app)

    # регистрация схем и ресурсов для документации
    for api in PublicAPI.API_SET:
        app.register_blueprint(api.blueprint)
        if configs.get('mode') != 'release':
            for resource in api.resource_list:
                docs.register(resource, blueprint=api.blueprint.name)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        user_id = jwt_data['sub']
        user = get_user_from_token_sub(user_id)
        return user

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token_in_redis = REDIS_BLOCK_LIST.get(jti)
        return token_in_redis is not None

    @app.after_request
    @jwt_required(optional=True)
    def refresh_token(response):
        if request.method == 'OPTIONS' or configs.get('mode') == 'dev':
            # Работа с токеном выполняется тольок на тестовм и прод контурах для всех запросов кроме OPTIONS
            return response

        if request.method == 'DELETE' and request.path == '/api/v1/auth/tg':
            # Послу отклонения токена не должна возникнуть возможность его обновления
            return response

        token_data = get_jwt()
        now = datetime.timestamp(datetime.now())
        if token_data and 0 < token_data['exp'] - now <= Timing.REFRESH_DELTA.value.total_seconds():
            # обновление токена за REFRESH_DELTA до окончания его срока жизни
            cookie = create_access_token(identity=token_data['sub'], expires_delta=Timing.EXP.value)
            set_access_cookies(response, cookie, max_age=Timing.EXP.value)

        return response

    @parser.error_handler
    def handle_request_parsing_error(err,
                                     req,  # pylint: disable=unused-argument
                                     schema,  # pylint: disable=unused-argument
                                     *,
                                     error_status_code,
                                     error_headers):  # pylint: disable=unused-argument
        abort(error_status_code or 400, errors=err.messages)

    # Для нашего проекта это вынужденная мера
    # Документация будет содержать input с 1 файлом,
    # но API будет поддерживать работу с несколькими файлами в одном input
    parser.KNOWN_MULTI_FIELDS.append(fields.Raw)

    socket_io.init_app(app) #добавить для регистрации сокета

    return app
