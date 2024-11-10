"""
Запуск проекта
"""
from gevent import monkey
monkey.patch_all()

import sentry_sdk

from configs import configs
from main.app import create_app, socket_io


if env := configs.get("sentry").get("env"):
    sentry_sdk.init(
        dsn=configs.get("sentry").get("dsn"),
        environment=env,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )


application = create_app()


if __name__ == '__main__':
    flask_cfg = configs.get('flask')
    PORT = flask_cfg.get('port')
    HOST = flask_cfg.get('host')
    DEBUG = flask_cfg.get('debug')

    # application.run(port=PORT, host=HOST, debug=DEBUG)
    socket_io.run(application, host=HOST, port=PORT, debug=DEBUG, allow_unsafe_werkzeug=True)
