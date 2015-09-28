from django.test import TestCase

import pkg_resources
import pytest
import responses


@pytest.mark.django_db
@responses.activate
class OnaTest(TestCase):

    def setUp(self):
        responses.add(responses.GET, 'https://ona.io/api/v1/',
                      status=200, content_type='application/json',
                      body=pkg_resources.resource_string(
                          'malaria24', 'ona/fixtures/responses/catalog.json'))

    def tearDown(self):
        pass

    def test_ona_fetch_reported_cases_task(self):
        pass
