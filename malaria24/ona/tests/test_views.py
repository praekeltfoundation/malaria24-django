import json
from StringIO import StringIO
from uuid import UUID

from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from mock import patch

from malaria24.ona.models import Facility, InboundSMS, SMS, SMSEvent
from malaria24.ona import tasks
from .base import MalariaTestCase

import responses


class FacilityTest(MalariaTestCase):

    def setUp(self):
        super(FacilityTest, self).setUp()
        user = User.objects.create_user('user', 'user@example.org', 'pass')
        user.is_staff = True
        user.save()
        self.client = Client()
        self.client.login(username='user', password='pass')

    def test_admin_import(self):
        self.assertEqual(Facility.objects.count(), 0)
        self.client.post(reverse('admin:ona_facility_upload'), {
            'upload': StringIO(json.dumps([{
                "District": "District",
                "FacCode": "123456",
                "Facility": "Facility Name",
                "Phase": "D",
                "Province": "Province",
                "Sub-District (Locality)": "Sub-District"
            }])),
            'wipe': False,
        })

        [facility] = Facility.objects.all()
        self.assertEqual(facility.facility_code, '123456')
        [message] = mail.outbox
        self.assertEqual(message.to, ['user@example.org'])
        self.assertEqual(message.subject, 'Facilities import complete.')

    def test_admin_import_idempotency(self):
        original_facility = Facility.objects.create(
            facility_code='123456',
            facility_name='The Old Name')
        self.client.post(reverse('admin:ona_facility_upload'), {
            'upload': StringIO(json.dumps([{
                "District": "District",
                "FacCode": "123456",
                "Facility": "Facility Name",
                "Phase": "D",
                "Province": "Province",
                "Sub-District (Locality)": "Sub-District"
            }])),
            'wipe': False,
        })

        [facility] = Facility.objects.all()
        self.assertEqual(facility.facility_code, '123456')
        self.assertEqual(facility.facility_name, 'Facility Name')
        self.assertEqual(facility.pk, original_facility.pk)

    def test_admin_import_wiping(self):
        original_facility = Facility.objects.create(
            facility_code='123456',
            facility_name='The Old Name')
        self.client.post(reverse('admin:ona_facility_upload'), {
            'upload': StringIO(json.dumps([{
                "District": "District",
                "FacCode": "123456",
                "Facility": "Facility Name",
                "Phase": "D",
                "Province": "Province",
                "Sub-District (Locality)": "Sub-District"
            }])),
            'wipe': True,
        })

        [facility] = Facility.objects.all()
        self.assertEqual(facility.facility_code, '123456')
        self.assertEqual(facility.facility_name, 'Facility Name')
        self.assertNotEqual(facility.pk, original_facility.pk)

    @responses.activate
    def test_admin_ehp_email(self):
        facility = Facility.objects.create(
            facility_code='123456',
            facility_name='The Old Name')
        self.mk_ehp(facility_code=facility.facility_code)
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(facility_code=facility.facility_code)
        response = self.client.get(reverse('admin:ehp_report_view', kwargs={
            'pk': case.pk,
        }))
        self.assertTemplateUsed(response, 'ona/html_email.html')

    def test_api(self):
        original_facility = Facility.objects.create(
            facility_code='123456',
            facility_name='The Old Name')
        response = self.client.get(reverse('api_v1:facility', kwargs={
            'facility_code': original_facility.facility_code,
        }))
        data = json.loads(response.content)
        self.assertEqual(data, original_facility.to_dict())

    def test_api_404(self):
        response = self.client.get(reverse('api_v1:facility', kwargs={
            'facility_code': 'foo',
        }))
        self.assertEqual(response.status_code, 404)

    def test_localities(self):
        Facility.objects.create(facility_code='123456',
                                district='District',
                                subdistrict='Subdistrict 1')
        Facility.objects.create(facility_code='654321',
                                district='District',
                                subdistrict='Subdistrict 2')
        Facility.objects.create(facility_code='000000',
                                district='District',
                                subdistrict='Subdistrict 2')
        response = self.client.get(reverse('api_v1:localities', kwargs={
            'facility_code': '123456',
        }))
        data = json.loads(response.content)
        self.assertEqual(data, ['Subdistrict 1', 'Subdistrict 2'])

    def test_localities_404(self):
        response = self.client.get(reverse('api_v1:localities', kwargs={
            'facility_code': 'foo',
        }))
        self.assertEqual(response.status_code, 404)


class InboundSMSTest(TestCase):
    def setUp(self):
        User.objects.create_user('user', 'user@example.org', 'pass')
        self.client.login(username='user', password='pass')

    def test_inbound_view_requires_authentication(self):
        self.client.logout()

        response = self.client.post('/api/v1/inbound/', json.dumps({
            "channel_data": {}, "from": "+27111111111",
            "channel_id": "test_channel",
            "timestamp": "2017-12-05 12:32:15.899992",
            "content": "test message", "to": "+27222222222",
            "reply_to": None, "group": None,
            "message_id": "c2c5a129da554bd2b799e391883d893d"}),
            content_type='application/json')

        self.assertEqual(response.status_code, 403)

    def test_inbound_sms_created(self):
        self.assertEqual(InboundSMS.objects.all().count(), 0)

        response = self.client.post('/api/v1/inbound/', json.dumps({
            "channel_data": {}, "from": "+27111111111",
            "channel_id": "test_channel",
            "timestamp": "2017-12-05 12:00:00.000000",
            "content": "test message", "to": "+27222222222",
            "reply_to": None, "group": None,
            "message_id": "c2c5a129da554bd2b799e391883d893d"}),
            content_type='application/json')

        self.assertEqual(response.status_code, 201)

        inbounds = InboundSMS.objects.all()
        self.assertEqual(inbounds.count(), 1)
        self.assertEqual(inbounds[0].sender, "+27111111111")
        self.assertEqual(inbounds[0].message_id,
                         UUID("c2c5a129da554bd2b799e391883d893d"))
        self.assertEqual(inbounds[0].content, "test message")
        self.assertEqual(inbounds[0].timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                         "2017-12-05 12:00:00")

    def test_inbound_view_accepts_blank_content(self):
        self.assertEqual(InboundSMS.objects.all().count(), 0)
        data = {"channel_data": {}, "from": "+27111111111",
                "channel_id": "test_channel",
                "timestamp": "2017-12-05 12:32:15.899992",
                "to": "+27222222222",
                "reply_to": None, "group": None,
                "message_id": "c2c5a129da554bd2b799e391883d893d"}

        response = self.client.post('/api/v1/inbound/', json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InboundSMS.objects.latest('created_at').content, "")

        data['content'] = ""
        data['message_id'] = "d2c5a129da554bd2b799e391883d893d"
        response = self.client.post('/api/v1/inbound/', json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InboundSMS.objects.latest('created_at').content, "")

        data['content'] = None
        data['message_id'] = "e2c5a129da554bd2b799e391883d893d"
        response = self.client.post('/api/v1/inbound/', json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InboundSMS.objects.latest('created_at').content, "")

    def test_inbound_view_finds_reply_to(self):
        sms = SMS.objects.create(to='+27111111111', content='test message',
                                 message_id="b2b5a129da554bd2b799e391883d893d")

        response = self.client.post('/api/v1/inbound/', json.dumps({
            "channel_data": {}, "from": "+27111111111",
            "channel_id": "test_channel",
            "timestamp": "2017-12-05 12:32:15.899992",
            "to": "+27222222222", "content": "test response",
            "reply_to": "b2b5a129da554bd2b799e391883d893d", "group": None,
            "message_id": "c2c5a129da554bd2b799e391883d893d"}),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InboundSMS.objects.all()[0].reply_to, sms)

    def test_inbound_view_throws_error(self):
        self.assertEqual(InboundSMS.objects.all().count(), 0)

        response = self.client.post('/api/v1/inbound/', json.dumps({
            "channel_data": {}, "from": "+27111111111",
            "channel_id": "test_channel",
            "timestamp": "2017-12-05 12:32:15.899992",
            "to": "+27222222222",
            "reply_to": None, "group": None}),
            content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         {"message_id": ["This field is required."]})
        self.assertEqual(InboundSMS.objects.all().count(), 0)


class SMSEventTest(TestCase):
    def setUp(self):
        User.objects.create_user('user', 'user@example.org', 'pass')
        self.client.login(username='user', password='pass')

    def test_event_view_requires_authentication(self):
        self.client.logout()

        response = self.client.post('/api/v1/event/', json.dumps({
            "channel_id": "9c1ffad2-257b-4915-9fff-762fe9018b8c",
            "event_type": "submitted", "event_details": {},
            "timestamp": "2017-12-06 12:34:38.456727",
            "message_id": "1c0aea5e68cc4e1b9e054d2f1bda1ad7"}),
            content_type='application/json')

        self.assertEqual(response.status_code, 403)

    def test_sms_event_created(self):
        sms = SMS.objects.create(to='+27111111111', content='test message',
                                 message_id="b2b5a129da554bd2b799e391883d893d")
        self.assertEqual(SMSEvent.objects.all().count(), 0)

        response = self.client.post('/api/v1/event/', json.dumps({
            "channel_id": "9c1ffad2-257b-4915-9fff-762fe9018b8c",
            "event_type": "submitted", "event_details": {},
            "timestamp": "2017-12-05 12:00:00.000000",
            "message_id": "b2b5a129da554bd2b799e391883d893d"}),
            content_type='application/json')

        self.assertEqual(response.status_code, 201)

        events = SMSEvent.objects.all()
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].event_type, "submitted")
        self.assertEqual(events[0].timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                         "2017-12-05 12:00:00")
        self.assertEqual(events[0].sms, sms)

    def test_event_view_throws_error(self):
        SMS.objects.create(to='+27111111111', content='test message',
                           message_id="b2b5a129da554bd2b799e391883d893d")
        self.assertEqual(InboundSMS.objects.all().count(), 0)

        response = self.client.post('/api/v1/event/', json.dumps({
            "channel_id": "9c1ffad2-257b-4915-9fff-762fe9018b8c",
            "event_details": {}, "timestamp": "2017-12-06 12:34:38.456727",
            "message_id": "b2b5a129da554bd2b799e391883d893d"}),
            content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         {"event_type": ["This field is required."]})
        self.assertEqual(InboundSMS.objects.all().count(), 0)

    def test_event_view_requires_message_id(self):
        self.assertEqual(InboundSMS.objects.all().count(), 0)

        data = {"channel_id": "9c1ffad2-257b-4915-9fff-762fe9018b8c",
                "event_type": "submitted", "event_details": {},
                "timestamp": "2017-12-06 12:34:38.456727",
                "message_id": ""}
        response = self.client.post('/api/v1/event/', json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         {'message_id': [u'This field may not be blank.']})

        data['messsage_id'] = None
        response = self.client.post('/api/v1/event/', json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         {'message_id': [u'This field may not be blank.']})

        del data['messsage_id']
        response = self.client.post('/api/v1/event/', json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data,
                         {'message_id': [u'This field may not be blank.']})
