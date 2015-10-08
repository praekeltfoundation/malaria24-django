import pkg_resources

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail

import random

from datetime import datetime

from testfixtures import LogCapture

import responses

from malaria24.ona.models import ReportedCase, Actor, SMS, EHP


@override_settings(CELERY_ALWAYS_EAGER=True)
class ReportedCaseTest(TestCase):

    def setUp(self):
        responses.add(
            responses.PUT,
            ('http://go.vumi.org/api/v1/go/http_api_nostream/'
             'VUMI_GO_CONVERSATION_KEY/messages.json'),
            status=200, content_type='application/json',
            body=pkg_resources.resource_string(
                'malaria24', 'ona/fixtures/responses/send_sms.json'))

    def tearDown(self):
        pass

    def mk_random_date(self):
        random_year = random.choice(range(1950, timezone.now().year))
        random_month = random.choice(range(1, 13))
        random_day = random.choice(range(1, 29))
        return datetime(random_year,
                        random_month, random_day).strftime("%y%m%d")

    def mk_ehp(self, **kwargs):
        defaults = {
            'name': 'name',
            'email_address': 'email@example.org',
            'phone_number': 'phone_number',
            'facility_code': 'facility_code',
            'role': EHP
        }
        defaults.update(kwargs)
        return Actor.objects.create(**defaults)

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
            '_id': '_id',
            '_uuid': '_uuid',
            '_xform_id_string': '_xform_id_string'
        }
        defaults.update(kwargs)
        return ReportedCase.objects.create(**defaults)

    @responses.activate
    def test_capture_no_ehps(self):
        with LogCapture() as log:
            self.mk_case()
            log.check(('root',
                       'WARNING',
                       'No EHPs found for facility code facility_code.'))

    @responses.activate
    def test_capture_no_ehp_phonenumber(self):
        with LogCapture() as log:
            ehp = self.mk_ehp(phone_number='')
            case = self.mk_case(facility_code=ehp.facility_code)
            log.check(('root',
                       'WARNING',
                       ('Unable to SMS report for case %s. '
                        'Missing phone_number.') % (case.pk,)))

    @responses.activate
    def test_capture_no_ehp_email_address(self):
        with LogCapture() as log:
            ehp = self.mk_ehp(email_address='')
            case = self.mk_case(facility_code=ehp.facility_code)
            log.check(('root',
                       'WARNING',
                       ('Unable to Email report for case %s. '
                        'Missing email_address.') % (case.pk,)))

    @responses.activate
    def test_capture_no_reported_by(self):
        with LogCapture() as log:
            ehp = self.mk_ehp()
            case = self.mk_case(facility_code=ehp.facility_code,
                                reported_by='')
            log.check(('root',
                       'WARNING',
                       ('Unable to SMS case number for case %s. '
                        'Missing reported_by.') % (case.pk,)))

    @responses.activate
    def test_capture_all_ok(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp()
        self.mk_case(facility_code=ehp.facility_code)
        [ehp_sms, reporter_sms] = SMS.objects.all()
        self.assertEqual(ehp_sms.to, 'phone_number')
        self.assertEqual(ehp_sms.content,
                         'A new case has been reported, the full report will '
                         'be sent to you via email.')
        self.assertEqual(ehp_sms.message_id, 'the-message-id')
        self.assertEqual(reporter_sms.to, 'reported_by')
        self.assertEqual(reporter_sms.content,
                         'Your reported case has been assigned case number 1.')
        self.assertEqual(reporter_sms.message_id, 'the-message-id')

    @responses.activate
    def test_idempotency(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp()
        case = self.mk_case(facility_code=ehp.facility_code)
        case.save()
        self.assertEqual(SMS.objects.count(), 2)

    @responses.activate
    def test_email_sending(self):
        ehp = self.mk_ehp()
        case = self.mk_case(facility_code=ehp.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.pk,))
        self.assertEqual(message.to, [ehp.email_address])
        self.assertTrue(ehp.email_address in message.body)
        [alternative] = message.alternatives
        content, content_type = alternative
        self.assertTrue(case.facility_code in content)
        self.assertEqual('text/html', content_type)

    @responses.activate
    def test_age(self):
        case = self.mk_case(date_of_birth="820101")
        self.assertEqual(33, case.age)
