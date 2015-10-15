import pkg_resources
import random
from datetime import datetime

import responses

from django.test import TestCase, override_settings
from django.utils import timezone

from malaria24.ona.models import ReportedCase, Actor, EHP


@override_settings(CELERY_ALWAYS_EAGER=True)
class MalariaTestCase(TestCase):

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

    def mk_case(self, **kwargs):
        defaults = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'locality': 'locality',
            'date_of_birth': self.mk_random_date(),
            'create_date_time': timezone.now(),
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
