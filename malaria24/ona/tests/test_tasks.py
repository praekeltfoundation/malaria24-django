from django.db.models.signals import post_save
from django.core import mail

import pkg_resources
import responses

from malaria24.ona.models import ReportedCase, alert_new_case, MANAGER_DISTRICT
from malaria24.ona.tasks import (
    ona_fetch_reported_cases, compile_and_send_digest_email)

from .base import MalariaTestCase


class OnaTest(MalariaTestCase):

    def setUp(self):
        super(OnaTest, self).setUp()
        responses.add(responses.GET, 'https://ona.io/api/v1/',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/catalog.json'))
        responses.add(responses.GET, 'https://ona.io/api/v1/data/79925',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/data.json'))
        post_save.disconnect(alert_new_case, sender=ReportedCase)

    def tearDown(self):
        super(OnaTest, self).tearDown()
        post_save.connect(alert_new_case, sender=ReportedCase)

    @responses.activate
    def test_ona_fetch_reported_cases_task(self):
        self.assertEqual(ReportedCase.objects.count(), 0)
        uuids = ona_fetch_reported_cases(79925)
        self.assertEqual(len(uuids), 2)
        self.assertEqual(ReportedCase.objects.count(), 2)

    @responses.activate
    def test_ona_fetch_reported_cases_task_idempotency(self):
        self.assertEqual(ReportedCase.objects.count(), 0)
        self.assertEqual(len(ona_fetch_reported_cases(79925)), 2)
        self.assertEqual(len(ona_fetch_reported_cases(79925)), 0)
        self.assertEqual(ReportedCase.objects.count(), 2)

    @responses.activate
    def test_ona_fetch_reported_cases_task_data_capture(self):
        self.assertEqual(len(ona_fetch_reported_cases(79925)), 2)
        case = ReportedCase.objects.get(
            _uuid='03a970b25c2740ea96a6cb517118bbef')
        self.assertEqual(case.first_name, 'XXX')
        self.assertEqual(case.last_name, 'ABC')
        self.assertEqual(case.locality, 'DEF')
        self.assertEqual(case.date_of_birth, '920827')
        self.assertEqual(case.create_date_time.year, 2015)
        self.assertEqual(case.create_date_time.month, 9)
        self.assertEqual(case.create_date_time.day, 21)
        self.assertEqual(case.sa_id_number, '0000000000000')
        self.assertEqual(case.msisdn, 'none')
        self.assertEqual(case.id_type, 'No_SA_ID_Year_Entry')
        self.assertEqual(case.abroad, '1')
        self.assertEqual(case.reported_by, '+27123456789')
        self.assertEqual(case.gender, 'male')
        self.assertEqual(case.facility_code, '154342')
        self.assertEqual(case.landmark, 'Laundromat')
        self.assertEqual(case._id, '3615221')
        self.assertEqual(case._uuid, '03a970b25c2740ea96a6cb517118bbef')
        self.assertEqual(case._xform_id_string, 'reported_case')

    @responses.activate
    def test_compile_and_send_digest_email_noop(self):
        self.assertEqual(None, compile_and_send_digest_email())
        self.assertEqual([], mail.outbox)

    @responses.activate
    def test_compile_and_send_digest_email(self):
        manager = self.mk_actor(role=MANAGER_DISTRICT,
                                email_address='manager@example.org')
        self.mk_case()
        compile_and_send_digest_email()
        [message] = mail.outbox
        self.assertEqual(message.to, [manager.email_address])
