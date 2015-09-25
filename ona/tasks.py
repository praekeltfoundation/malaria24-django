from django.conf import settings

from malaria24 import celery_app

from onapie.client import Client


@celery_app.task
def ona_fetch_reported_cases():
    client = Client('https://ona.io', api_token=settings.ONAPI_ACCESS_TOKEN)
