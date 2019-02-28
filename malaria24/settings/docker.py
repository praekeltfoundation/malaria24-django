"""Django settings for use within the docker container."""

from os.path import join

import dj_database_url

from .production import *  # noqa: F401, F403

# Disable debug mode

DEBUG = False

COMPRESS_OFFLINE = True

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///%s' % (join(PROJECT_ROOT, 'malaria24.sqlite3'),))}

LOCALE_PATHS = (
    join(PROJECT_ROOT, "locale"),
)
