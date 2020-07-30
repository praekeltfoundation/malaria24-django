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

ONAPIE_FORM_PK = environ.get('ONAPIE_FORM_PK')
ONAPIE_ACCESS_TOKEN = environ.get('ONAPIE_ACCESS_TOKEN')
ONA_API_URL = environ.get('ONA_API_URL', 'https://odk.ona.io')

RAVEN_DSN = environ.get('RAVEN_DSN')

# JUNEBUG Settings
JUNEBUG_CHANNEL_URL = environ.get('JUNEBUG_CHANNEL_URL')
JUNEBUG_USERNAME = environ.get('JUNEBUG_USERNAME')
JUNEBUG_PASSWORD = environ.get('JUNEBUG_PASSWORD')
SMS_CHANNEL = environ.get('SMS_CHANNEL')
SMS_CODE = environ.get('SMS_CODE')

RAVEN_DSN = environ.get('RAVEN_DSN')
RAVEN_CONFIG = {'dsn': RAVEN_DSN} if RAVEN_DSN else {}

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
