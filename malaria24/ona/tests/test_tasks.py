from django.test import TestCase

import pkg_resources
import pytest
import responses

from malaria24.ona.models import ReportedCase
from malaria24.ona.tasks import ona_fetch_reported_cases


@pytest.mark.django_db
class OnaTest(TestCase):

    def setUp(self):
        responses.add(responses.GET, 'https://ona.io/api/v1/',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/catalog.json'))
        responses.add(responses.GET, 'https://ona.io/api/v1/data/79925',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/data.json'))

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
