from models import with_session
from models.models import StoriesShow, StoriesClick
from resources.yandex_storage.schemas import StoryActivityEnum
from utils import current_user


@with_session()
def registrate_story_activity(ses, item_id: int, activity: StoryActivityEnum):
    """
    регистрация действия с сторисами

    :param ses: сессия алхимии
    :param activity: действие
    :param item_id: идентификатор объявления
    """

    cu_id = current_user["user_id"]

    if activity is StoryActivityEnum.SHOW:
        ses.add(StoriesShow(item_id=item_id, user_id=cu_id))
    elif activity is StoryActivityEnum.CLICK:
        ses.add(StoriesClick(item_id=item_id, user_id=cu_id))

    ses.commit()
