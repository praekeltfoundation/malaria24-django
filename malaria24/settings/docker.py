"""Django settings for use within the docker container."""

from os.path import join

import dj_database_url

from .production import *  # noqa: F401, F403

# Disable debug mode

DEBUG = False

COMPRESS_OFFLINE = True

BROKER_URL = environ.get('BROKER_URL') or BROKER_URL

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///%s' % (join(PROJECT_ROOT, 'malaria24.sqlite3'),))}

LOCALE_PATHS = (
    join(PROJECT_ROOT, "locale"),
)

ONAPIE_FORM_PK = environ.get('ONAPIE_FORM_PK') or ""
ONAPIE_ACCESS_TOKEN = environ.get('ONAPIE_ACCESS_TOKEN') or ""

RAVEN_DSN = environ.get('RAVEN_DSN') or ""

# JUNEBUG Settings
JUNEBUG_CHANNEL_URL = environ.get('JUNEBUG_CHANNEL_URL') or ""
JUNEBUG_USERNAME = environ.get('JUNEBUG_USERNAME') or ""
JUNEBUG_PASSWORD = environ.get('JUNEBUG_PASSWORD') or ""
SMS_CHANNEL = environ.get('SMS_CHANNEL') or ""
SMS_CODE = environ.get('SMS_CODE') or ""
