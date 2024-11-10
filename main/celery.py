"""
Инициализация Celery
"""
import sentry_sdk
from celery import Celery, signals
from celery.schedules import crontab
from sentry_sdk.integrations.celery import CeleryIntegration

from configs import configs

celery_app = Celery('main')


@signals.celeryd_init.connect
def init_sentry(**_kwargs):
    if env := configs.get("sentry").get("env"):
        sentry_sdk.init(
            dsn=configs.get("sentry").get("dsn"),
            environment=env,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            debug=True,
            integrations=[
                CeleryIntegration(monitor_beat_tasks=True)
            ]
        )


celery_app.config_from_object('main.celery_config')

# настройки планировщика
celery_app.conf.beat_schedule = {
    'update currencies': {
        'task': 'services.currencies.tasks.update_currencies_task',
        'schedule': 60 * 60 * 6,
    },
    'add_to_archive': {
        'task': 'services.announcement.tasks.add_to_archive',
        'schedule': crontab(hour=3, minute=0)
    }
}
