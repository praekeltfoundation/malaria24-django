import pkg_resources
import random
from datetime import datetime
import pytz

import responses

from django.test import TestCase, override_settings
from django.utils import timezone
from django.db import models

from malaria24.ona.models import (
    ReportedCase, Actor, EHP, CASE_INVESTIGATOR, MIS, Facility)


@override_settings(CELERY_ALWAYS_EAGER=True)
class MalariaTestCase(TestCase):

    posted = models.DateTimeField()

    def setUp(self):
        responses.add(
            responses.PUT,
            ('http://go.vumi.org/api/v1/go/http_api_nostream/'
             'VUMI_GO_CONVERSATION_KEY/messages.json'),
            status=200, content_type='application/json',
            body=pkg_resources.resource_string(
                'malaria24', 'ona/fixtures/responses/send_sms.json'))

    def mk_random_date(self):
        random_year = random.choice(range(1950, timezone.now().year))
        random_month = random.choice(range(1, 13))
        random_day = random.choice(range(1, 29))
        return datetime(random_year,
                        random_month, random_day).strftime("%y%m%d")

    def mk_actor(self, **kwargs):
        defaults = {
            'name': 'name',
            'email_address': 'email@example.org',
            'phone_number': 'phone_number',
            'facility_code': 'facility_code',
        }
        defaults.update(kwargs)
        return Actor.objects.create(**defaults)

    def mk_ehp(self, **kwargs):
        return self.mk_actor(role=EHP, **kwargs)

    def mk_ci(self, **kwargs):
        return self.mk_actor(role=CASE_INVESTIGATOR, **kwargs)

    def mk_mis(self, **kwargs):
        return self.mk_actor(role=MIS, **kwargs)

    def mk_facility(self, **kwargs):
        return Facility.objects.create(**kwargs)

    def start_randomDate(self):
        random_year = timezone.now().year

        return (datetime(random_year, 2, random.choice(range(1, 8)), 11, 30,
                         30, 0, pytz.timezone('US/Pacific'))
                .strftime('%Y-%m-%d %H:%M:%S.%f%z'))

    def mk_create_date(self):
        random_year = timezone.now().year
        e_month = random.choice(range(1, 13))
        e_day = random.choice(range(1, 29))
        e_hour = random.choice(range(0, 24))
        e_minute = random.choice(range(0, 60))
        e_second = random.choice(range(0, 60))

        return (datetime(random_year, e_month, e_day, e_hour, e_minute,
                e_second, 0, pytz.timezone('US/Pacific'))
                .strftime('%Y-%m-%d %H:%M:%S.%f%z'))

    def mk_case(self, **kwargs):
        defaults = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'locality': 'locality',
            'date_of_birth': self.mk_random_date(),
            'create_date_time': self.start_randomDate(),
            'sa_id_number': 'sa_id_number',
            'msisdn': 'msisdn',
            'id_type': 'id_type',
            'abroad': 'abroad',
            'reported_by': 'reported_by',
            'gender': 'gender',
            'facility_code': 'facility_code',
            'landmark': 'landmark',
            'landmark_description': 'landmark_description',
            '_id': '_id',
            '_uuid': '_uuid',
            '_xform_id_string': '_xform_id_string',
            'digest': None,
        }
        defaults.update(kwargs)
        return ReportedCase.objects.create(**defaults)
