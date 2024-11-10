"""
Пакет API ресурсов
"""
from flask_restful import Api

from resources.admin import resource_bp as admin_bp
from resources.admin.resources import CacheAPI
from resources.ads.resourses import Ads
from resources.currencies import currencies_bp
from resources.currencies.resources import CurrenciesAPI
from resources.announcement_list import resource_bp as announcement_list_bp
from resources.announcement_list.resourses import AnnouncementsList, AnnouncementCard, PreferAnnouncement
from resources.dimensions import dimension_bp
from resources.dimensions.resources import CategoryDimension, CityDimension, CountryCityDimension, PhoneDimension, \
    LanguageDimension, CurrencyDimension, TagDimension, DocumentsDimension
from resources.private_feedback import resource_bp as private_fb_bp
from resources.private_feedback.resourses import PrivateFeedback

from resources.profile_user import users_bp
from resources.profile_user.resources import UsersAPI, UsersFindAPI
from resources.yandex_storage import resource_bp as files_bp
from resources.yandex_storage.resourses import FilesApi, FilesStoriesApi
from resources.auth import auth_bp
from resources.auth.resourses import TgAuthAPI, CurrentUser, AuthGoogleAPI, Email, EmailConfirm, EmailCreatePassword, \
    AuthAppleAPI, ProfileDelete
from resources.ads import resource_bp as ads_bp
from resources.location import location_bp
from resources.location.resources import CurrentLocationAPI
from resources.feedback import feedback_bp
from resources.feedback.resources import FeedbackAPI
from resources.push import resource_bp as push_bp
from resources.push.resourses import PushTest, PushUserRegistrationToken


__all__ = ('PublicAPI',)


class PublicAPI(Api):
    """
    Наследник класса Api для сохранения ресурсов и объектов Api
    """
    API_SET = set()

    def __init__(self, *args, **kwargs):
        Api.__init__(self, *args, **kwargs)
        self.resource_list = []
        self.API_SET.add(self)

    def add_resource(self, resource, *urls, **kwargs):
        """
        Переопределение метода добавления ресурса с сохранением последнего в специальный список
        для автоматизации регистрации документации
        """
        self.resource_list.append(resource)
        Api.add_resource(self, resource, *urls, **kwargs)


# Регистрация ресурсов

# Тестовое API

# API курсов валют
api_currencies = PublicAPI(currencies_bp)
api_currencies.add_resource(CurrenciesAPI, "/api/v1/currencies")


api_announcement_list = PublicAPI(announcement_list_bp)
# API превью объявлений
api_announcement_list.add_resource(AnnouncementsList, '/api/v1/announcement')
api_announcement_list.add_resource(AnnouncementCard, '/api/v1/announcement_card')
api_announcement_list.add_resource(PreferAnnouncement, '/api/v1/announcement_prefer')

# API файлов
api_files = PublicAPI(files_bp)
api_files.add_resource(FilesApi, '/api/v1/files')
api_files.add_resource(FilesStoriesApi, '/api/v1/stories')

# API профиля и поиска профиля юзера
api_user_tg = PublicAPI(users_bp)
api_user_tg.add_resource(UsersAPI, '/api/v1/users')
api_user_tg.add_resource(UsersFindAPI, '/api/v1/usersFind')

# API справочников категорий
api_dimension = PublicAPI(dimension_bp)
api_dimension.add_resource(CategoryDimension, '/api/v1/dimensions/categories')
api_dimension.add_resource(CityDimension, '/api/v1/dimensions/cities')
api_dimension.add_resource(CountryCityDimension, '/api/v2/dimensions/cities')
api_dimension.add_resource(PhoneDimension, '/api/v1/dimensions/phones')
api_dimension.add_resource(LanguageDimension, '/api/v1/dimensions/languages')
api_dimension.add_resource(CurrencyDimension, '/api/v1/dimensions/currencies')
api_dimension.add_resource(TagDimension, '/api/v1/dimensions/tags')
api_dimension.add_resource(DocumentsDimension, '/api/v1/dimensions/documents')

# API аутентификации
api_auth = PublicAPI(auth_bp)
api_auth.add_resource(TgAuthAPI, '/api/v1/auth/tg')
api_auth.add_resource(AuthGoogleAPI, '/api/v1/auth/google')
api_auth.add_resource(AuthAppleAPI, '/api/v1/auth/apple')
api_auth.add_resource(CurrentUser, '/api/v1/auth/current_user')
api_auth.add_resource(Email, '/api/v1/auth/email/init')
api_auth.add_resource(EmailConfirm, '/api/v1/auth/email/confirm_by_email')
api_auth.add_resource(EmailCreatePassword, '/api/v1/auth/email/password')
api_auth.add_resource(ProfileDelete, '/api/v1/auth/delete_profile')

# API рекламного контента
api_ads = PublicAPI(ads_bp)
api_ads.add_resource(Ads, '/api/v1/ads')

# API приватных отзывов
api_private_feedback = PublicAPI(private_fb_bp)
api_private_feedback.add_resource(PrivateFeedback, '/api/v1/private_feedback')

# API геолокации
api_location = PublicAPI(location_bp)
api_location.add_resource(CurrentLocationAPI, '/api/v1/location/current')

# API отзывов
api_feedback = PublicAPI(feedback_bp)
api_feedback.add_resource(FeedbackAPI, '/api/v1/feedback')

# API Push уведомлений
api_push = PublicAPI(push_bp)
api_push.add_resource(PushTest, '/api/v1/test_push')
api_push.add_resource(PushUserRegistrationToken, '/api/v1/push/reg_token/user')

# API администратора
api_admin = PublicAPI(admin_bp)
api_admin.add_resource(CacheAPI, '/api/v1/admin/cache')