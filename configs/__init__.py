"""
Пакет для чтения конфигурационного файла в формате yaml
"""
import os

from yaml import load, Loader


CONFIG_FILE = 'config.yaml'

cp = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(cp, CONFIG_FILE), 'r', encoding='utf-8') as f:
        configs = load(f, Loader)
except FileNotFoundError as e:
    raise FileNotFoundError(f'Конфигурационный файл {os.path.join(cp, CONFIG_FILE)} не найден системой') from e
