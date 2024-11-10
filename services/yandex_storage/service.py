"""
Модуль с методами для работы с файлами
"""

import io

import boto3

from PIL import Image, ImageOps
from flask import make_response, jsonify, Response

from configs import configs
from models import with_session
from models.models import Documents, Stories
from utils import uuid

ACCESS_ID = configs.get('yandex_store').get('access_id')
ACCESS_KEY = configs.get('yandex_store').get('access_key')
BUCKET_MEDIUM = configs.get('yandex_store').get('bucket_medium')
BUCKET_SMALL = configs.get('yandex_store').get('bucket_small')


def get_s3_session():
    """
    Создание объекта доступа к S3 харанилищу
    """

    session = boto3.session.Session(aws_access_key_id=ACCESS_ID, aws_secret_access_key=ACCESS_KEY)
    return session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )


def resize(origin, size, file_extension):
    """
    Преобразоване размеров фото
    """
    if origin.size[1] < origin.size[0]:
        new_size = (round(size * origin.size[0] / origin.size[1]), size)
    else:
        new_size = (size, round(size * origin.size[1] / origin.size[0]))

    resized = origin.resize(new_size)
    resized.save(buffer := io.BytesIO(), format=file_extension)  # без символа '.'

    return buffer.getvalue()


@with_session()
def loader_post(ses, entity_id: str, files: list) -> Response:
    file_list = []
    s_3 = get_s3_session()
    for file in files:
        origin = ImageOps.exif_transpose(Image.open(file))
        origin.load()

        new_name = f"{uuid(plain=True)[:10]}.webp"

        s_3.put_object(Bucket=BUCKET_SMALL,
                       Key=f'{entity_id}/{new_name}',
                       Body=resize(origin, 320, 'webp'))
        s_3.put_object(Bucket=BUCKET_MEDIUM,
                       Key=f'{entity_id}/{new_name}',
                       Body=resize(origin, 720, 'webp'))

        file_list.append(new_name)

        ses.add(Documents(entity_id=entity_id, filename=new_name))

    ses.commit()

    return make_response(jsonify({'files': file_list}), 200)


@with_session()
def loader_get(ses, entity_id: str) -> Response:
    files = tuple(i.filename for i in ses.query(Documents.filename).filter_by(entity_id=entity_id))

    return make_response(jsonify({'files': files}), 200)


@with_session()
def loader_delete(ses, entity_id: str, filename: str) -> Response:
    ses.query(Documents).filter_by(entity_id=entity_id, filename=filename).delete()
    ses.commit()
    s_3 = get_s3_session()
    s_3.delete_objects(Bucket=BUCKET_SMALL, Delete={'Objects': [{'Key': f'{entity_id}/{filename}'}]})
    s_3.delete_objects(Bucket=BUCKET_MEDIUM, Delete={'Objects': [{'Key': f'{entity_id}/{filename}'}]})

    return make_response(jsonify({'message': 'Файл успешно удален'}), 200)


@with_session()
def stories_get(ses, place_id: int = None) -> list:

    def transform(element):
        serialized_element = element.to_dict()
        pid = serialized_element["place_id"]

        if "common" not in (url := serialized_element["preview_url"]):
            serialized_element["preview_url"] = f'{pid}/{url}'

        for story in serialized_element["story_item"]:
            if "common" not in (url := story["storie_url"]):
                story["storie_url"] = f'{pid}/{url}'

        return serialized_element

    if place_id:
        out = ses.query(Stories).filter_by(place_id=place_id, is_active=True).one_or_none()
        data = [transform(out)] if out else []
    else:
        data = [transform(i) for i in ses.query(Stories).filter_by(is_active=True)]
    return data
