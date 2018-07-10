from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.conf import settings
from datetime import datetime
from base64 import b64encode
import json
import pkg_resources
import responses
import requests

from rest_framework.authtoken.models import Token

from malaria24.ona.models import (
    ReportedCase, new_case_alert_ehps, MIS, MANAGER_DISTRICT, MANAGER_NATIONAL,
    MANAGER_PROVINCIAL, OnaForm, Facility, SMS, DistrictDigest,
    NationalDigest, ProvincialDigest)
from malaria24.ona.tasks import (
    ona_fetch_reported_cases, compile_and_send_digest_email, compile_and_send_jembi,
    ona_fetch_forms, send_sms)

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
        responses.add(responses.GET, 'https://ona.io/api/v1/forms',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/forms.json'))
        post_save.disconnect(new_case_alert_ehps, sender=ReportedCase)
        self.complete_url = settings.JEMBI_URL
        self.username = settings.JEMBI_USERNAME
        self.password = settings.JEMBI_PASSWORD

    def tearDown(self):
        super(OnaTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)

    @responses.activate
    def test_ona_fetch_reported_cases_task(self):
        self.assertEqual(ReportedCase.objects.count(), 0)
        form = OnaForm.objects.create(uuid='uuuid', form_id='79925',
                                      active=True)
        uuids = ona_fetch_reported_cases()
        self.assertEqual(len(uuids[form.form_id]), 2)
        self.assertEqual(ReportedCase.objects.count(), 2)
        self.assertEqual(form.reportedcase_set.count(), 2)

    @responses.activate
    def test_ona_fetch_reported_cases_task_idempotency(self):
        self.assertEqual(ReportedCase.objects.count(), 0)
        form = OnaForm.objects.create(uuid='uuuid', form_id='79925',
                                      active=True)
        self.assertEqual(len(ona_fetch_reported_cases()[form.form_id]), 2)
        self.assertEqual(len(ona_fetch_reported_cases()[form.form_id]), 0)
        self.assertEqual(ReportedCase.objects.count(), 2)
        self.assertEqual(form.reportedcase_set.count(), 2)

    @responses.activate
    def test_ona_fetch_reported_cases_task_data_capture(self):
        form = OnaForm.objects.create(uuid='uuuid', form_id='79925',
                                      active=True)
        self.assertEqual(len(ona_fetch_reported_cases()[form.form_id]), 2)
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
        self.assertEqual(case.landmark_description, 'Quite pretty')
        self.assertEqual(case._id, '3615221')
        self.assertEqual(case._uuid, '03a970b25c2740ea96a6cb517118bbef')
        self.assertEqual(case._xform_id_string, 'reported_case')
        self.assertEqual(case.form, form)

    @responses.activate
    def test_ona_fetch_reported_cases_task_data_capture_null_locality(self):
        form = OnaForm.objects.create(uuid='uuuid', form_id='79925',
                                      active=True)
        self.assertEqual(len(ona_fetch_reported_cases()[form.form_id]), 2)
        case = ReportedCase.objects.get(
            _uuid='4c4799a9212245fcb564aa448444c3e0')
        self.assertEqual(case.first_name, 'GHI')
        self.assertEqual(case.last_name, 'KLM')
        self.assertEqual(case.locality, '_other')
        self.assertEqual(case.date_of_birth, '870910')
        self.assertEqual(case.create_date_time.year, 2015)
        self.assertEqual(case.create_date_time.month, 9)
        self.assertEqual(case.create_date_time.day, 20)
        self.assertEqual(case.sa_id_number, '0000000000000')
        self.assertEqual(case.msisdn, '+27012345678')
        self.assertEqual(case.id_type, 'No_SA_ID_Year_Entry')
        self.assertEqual(case.abroad, '1')
        self.assertEqual(case.reported_by, '+27123456789')
        self.assertEqual(case.gender, 'male')
        self.assertEqual(case.facility_code, '154342')
        self.assertEqual(case.landmark, 'School')
        self.assertEqual(case.landmark_description, 'Quite pretty')
        self.assertEqual(case._id, '3608910')
        self.assertEqual(case._uuid, '4c4799a9212245fcb564aa448444c3e0')
        self.assertEqual(case._xform_id_string, 'reported_case')
        self.assertEqual(case.form, form)

    @responses.activate
    def test_compile_and_send_digest_email_noop(self):
        self.assertEqual(None, compile_and_send_digest_email())
        self.assertEqual([], mail.outbox)

    @responses.activate
    def test_compile_and_send_digest_email(self):
        mis = self.mk_actor(role=MIS,
                            email_address='manager@example.org')
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_DISTRICT,
                      email_address='manager@example.org',
                      facility_code='342315')
        self.mk_actor(role=MANAGER_PROVINCIAL,
                      email_address='m2@example.org',
                      facility_code='342315')
        self.mk_actor(role=MANAGER_NATIONAL,
                      email_address='m3@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='222222')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='333333')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None
        self.mk_case()
        compile_and_send_digest_email()
        message = list(mail.outbox)[1]
        self.assertEqual(set(message.to), set([
            'm2@example.org',
            mis.email_address]))
        self.assertEqual(len(mail.outbox), 4)

    @responses.activate
    def test_national_digest_week_variable(self):
        self.mk_actor(role=MIS,
                      email_address='manager@example.org')
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_DISTRICT,
                      email_address='manager@example.org',
                      facility_code='342315')
        self.mk_actor(role=MANAGER_PROVINCIAL,
                      email_address='m2@example.org',
                      facility_code='342315')
        self.mk_actor(role=MANAGER_NATIONAL,
                      email_address='m3@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='222222')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='333333')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        self.mk_case()
        compile_and_send_digest_email()
        NationalDigest.compile_digest().send_digest_email()

    @responses.activate
    def test_provincial_digest_week_variable(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        Facility.objects.create(facility_code='222222',
                                facility_name='Facility 2',
                                province='Limpopo',
                                district=u'Example2')
        Facility.objects.create(facility_code='333333',
                                facility_name='Facility 2',
                                province='The Eastern Cape',
                                district=u'Example2')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='222222')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='333333')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        self.mk_case()
        compile_and_send_digest_email()
        ProvincialDigest.compile_digest().send_digest_email()

    @responses.activate
    def test_district_digest_week_variable(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        Facility.objects.create(facility_code='222222',
                                facility_name='Facility 2',
                                province='Limpopo',
                                district=u'Example1')
        Facility.objects.create(facility_code='333333',
                                facility_name='Facility 3',
                                province='The Eastern Cape',
                                district=u'Example3')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='342315', district=u'Example1')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='222222', district=u'Example1')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='222222')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='333333')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        self.mk_case()
        compile_and_send_digest_email()
        DistrictDigest.compile_digest().send_digest_email()

    @responses.activate
    def test_ona_fetch_forms(self):
        self.assertEqual(OnaForm.objects.count(), 0)
        ona_fetch_forms()
        ona_fetch_forms()  # should be idempotent
        [form] = OnaForm.objects.all()
        self.assertEqual(form.uuid, 'the-uuid')
        self.assertEqual(form.id_string, 'the-form-id-string')
        self.assertEqual(form.title, 'the-form-title')
        self.assertEqual(form.form_id, '12345')
        self.assertEqual(form.active, False)

    @responses.activate
    def test_sms_vumi_go_if_channel_empty(self):
        """
        Checks vumi go is the default channel
        """
        send_sms(to='+27111111111', content='test message')

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url,
                         "http://go.vumi.org/api/v1/go/http_api_nostream"
                         "/VUMI_GO_CONVERSATION_KEY/messages.json")
        [sms] = SMS.objects.all()
        self.assertEqual(sms.content, "test message")

    @responses.activate
    @override_settings(
        SMS_CHANNEL='VUMI_GO')
    def test_sms_vumi_go_if_set(self):
        """
        Checks sms sent via vumi go if that's what the setting specifies
        """
        send_sms(to='+27111111111', content='test message')

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url,
                         "http://go.vumi.org/api/v1/go/http_api_nostream"
                         "/VUMI_GO_CONVERSATION_KEY/messages.json")
        [sms] = SMS.objects.all()
        self.assertEqual(sms.content, "test message")

    @responses.activate
    @override_settings(
        SMS_CHANNEL='JUNEBUG')
    def test_sms_junebug_fails_if_settings_missing(self):
        """
        Checks sending via Junebug requires extra settings
        """
        with self.assertRaises(AttributeError):
            send_sms(to='+27111111111', content='test message')

        with self.settings(
                JUNEBUG_CHANNEL_URL='http://junebug.qa.malariaconnect.org'):
            with self.assertRaises(AttributeError):
                send_sms(to='+27111111111', content='test message')

    @responses.activate
    @override_settings(
        SMS_CHANNEL='JUNEBUG',
        JUNEBUG_CHANNEL_URL='https://example.com/junebug/CHANNEL_ID',
        SMS_CODE='*11111')
    def test_sms_junebug_if_set(self):
        """
        Checks sms sent via Junebug if that's what the setting specifies
        """

        jb_user = User.objects.create_user('junebug')
        jb_token = Token.objects.create(user=jb_user)

        responses.add(
            responses.POST,
            ('https://example.com/junebug/CHANNEL_ID/messages/'),
            status=201, content_type='application/json',
            body=json.dumps({
                "status": 201,
                "code": "Created",
                "description": "message submitted",
                "result": {
                    "channel_data": {},
                    "from": None,
                    "channel_id": "9c1ffad2-257b-4915-9fff-762fe9018b8c",
                    "timestamp": "2017-12-07 15:31:28.783794",
                    "content": "test message",
                    "to": "+27111111111",
                    "reply_to": None,
                    "group": None,
                    "message_id": "the-message-id"
                }
            })
        )

        send_sms(to='+27111111111', content='test message')

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url,
            "https://example.com/junebug/CHANNEL_ID/messages/")
        data = json.loads(responses.calls[0].request.body)
        self.assertEqual(data['event_url'], 'http://example.com/api/v1/event/')
        self.assertEqual(data['event_auth_token'], jb_token.key)
        [sms] = SMS.objects.all()
        self.assertEqual(sms.content, "test message")

    @responses.activate
    def test_compile_Jembi(self):
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        responses.add(
            responses.POST,
            settings.JEMBI_URL,
            status=201, content_type='application/json',
            body=json.dumps(
                case.get_data()
            )
        )
        auth_headers = ('Basic ' +
                        b64encode("{0}:{1}".format(settings.JEMBI_USERNAME,
                                                   settings.JEMBI_PASSWORD)))
        self.assertEqual(
            responses.calls[0].request.headers['Authorization'],
            auth_headers)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url,
            settings.JEMBI_URL)

        data = json.loads(responses.calls[0].request.body)
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Day')
        self.assertEqual(data['gender'], 'male')
        self.assertEqual(data['msisdn'], '0711111111')
        self.assertEqual(data['case_number'], '20171214-123456-42')
        self.assertEqual(data['sa_id_number'], '5608071111083')
        self.assertEqual(data['reported_by'], '+27721111111')
        self.assertEqual(data['id_type'], 'said')
        self.assertEqual(data['abroad'], 'No')
        self.assertEqual(data['landmark_description'], 'None')
        self.assertEqual(data['locality'], 'None')
        self.assertEqual(data['landmark'], 'School')
        self.assertEqual(data['facility_code'], '123456')

    @responses.activate
    def test_send_Jembi(self):
        """
        Checks to see if status raised for errors
        """
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        case_dictionary = case.get_data()
        responses.add(
            responses.POST,
            settings.JEMBI_URL,
            status=404, content_type='application/json',
            body=json.dumps(
                case.get_data()
            )
        )
        with self.assertRaises(requests.HTTPError):
            compile_and_send_jembi(case.pk)
