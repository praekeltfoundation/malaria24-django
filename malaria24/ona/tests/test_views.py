import json
from StringIO import StringIO

from django.core import mail
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from mock import patch

from malaria24.ona.models import Facility
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
