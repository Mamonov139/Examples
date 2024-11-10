"""
Менеджер работы с почтой
"""

import smtplib

from os import path
from ssl import create_default_context
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import certifi
from jinja2 import Environment, FileSystemLoader

from configs import configs
from utils import ServiceError
from .utils import verification_code


class SmtpManager:

    def __init__(self):
        self.__template_dir = path.join(path.dirname(__file__), r'templates')
        self.__configs = configs.get('smtp')

        if not self.__configs:
            raise ServiceError("Не пуказаны настройки SMTP")

    def send_verification_email(self, TO: str) -> str:
        """
        Отправка email с кодом подтверждения
        """
        code = verification_code()
        self.__send_mail("verification_code.html", {"code": code}, TO)
        return code

    def __send_mail(self, template, data: dict, TO: str) -> int:
        """
        Отправка сообзения

        :param template: шаблон письма
        :param data: данные, которые заполняют шаблон
        :param TO: адрес получателя
        """
        HOST = self.__configs['host']
        PORT = self.__configs['port']
        FROM = self.__configs['from']
        USERNAME = self.__configs['username']
        PASSWORD = self.__configs['password']

        emailContent = self.__render_template(template, data=data)

        message = MIMEMultipart("Alternative")
        message["Subject"] = "verification letter"
        message["From"] = FROM
        message["To"] = TO
        message.attach(MIMEText(emailContent, "html"))

        context = create_default_context(cafile=certifi.where())
        with smtplib.SMTP_SSL(HOST, PORT, context=context) as server:
            responseCode, _ = server.ehlo(HOST)
            if responseCode == 250:
                server.login(USERNAME, PASSWORD)
                server.sendmail(FROM, TO, message.as_string())
                return 0

        return -1

    def __render_template(self, template: str, data: dict) -> str:
        """
        заполнение шаблона
        """

        env = Environment()
        env.loader = FileSystemLoader(self.__template_dir)
        _template = env.get_template(template)
        return _template.render(data=data)
