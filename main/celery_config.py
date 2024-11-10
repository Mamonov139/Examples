"""
Настройки Celery
"""

from configs import configs


RC = configs.get("redis")
pw_string = f':{RC.get("password")}@' if RC.get("password") else ''

broker_url = f'redis://{pw_string}{RC.get("host")}:{RC.get("port")}/{RC.get("db")}'

result_backend = broker_url

timezone = 'Europe/Moscow'  # pylint: disable=invalid-name

imports = ("services.currencies.tasks", "services.announcement.tasks")

# пути к задачам
task_routes = {
    'services.currencies.tasks.update_currencies_task': {
        'queue': f'beat_queue{"_release" if configs.get("mode") == "release" else ""}'
    },
    'services.announcement.tasks.add_to_archive': {
        'queue': f'beat_queue{"_release" if configs.get("mode") == "release" else ""}'
    },
}
