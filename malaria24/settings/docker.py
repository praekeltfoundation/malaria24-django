"""Django settings for use within the docker container."""

from django.core.exceptions import ImproperlyConfigured

from os import environ
from os.path import abspath, dirname, join

import dj_database_url

from .production import *  # noqa: F401, F403


if SECRET_KEY == DEFAULT_SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured('SECRET_KEY is set to default value')

# Disable debug mode

DEBUG = False

PROJECT_ROOT = (
    environ.get('PROJECT_ROOT') or dirname(dirname(abspath(__file__))))

COMPRESS_OFFLINE = True

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///%s' % (join(PROJECT_ROOT, 'gemmolo.db'),))}

MEDIA_ROOT = join(PROJECT_ROOT, 'media')

STATIC_ROOT = join(PROJECT_ROOT, 'static')

LOCALE_PATHS = (
    join(PROJECT_ROOT, "locale"),
)
