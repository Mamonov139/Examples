from enum import Enum


class AdPlaceType(str, Enum):
    TOP = 'TOP'
    NATIVE = 'NATIVE'


class AdType(str, Enum):
    BANNER = 'BANNER'
    NATIVE = 'NATIVE'


class OrderFields(str, Enum):
    DATE = 'publish_date'
    REGION = 'region_id'
    SUBCATEGORY = 'sub_category_id'
    COUNTRY = 'country_id'
    DATE_VIEW = 'view_date'


class OrderDirection(Enum):
    ASC = 'asc'
    DESC = 'desc'


class AdActivityEnum(str, Enum):
    CLICK = 'click'
    SHOW = 'show'


class UserRequestType(str, Enum):
    DELETE = 'delete'
