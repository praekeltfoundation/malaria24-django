from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models.signals import post_save
from django.test import override_settings
from mock import patch

from malaria24.ona.models import (
    ReportedCase,
    new_case_alert_ehps,
    new_case_alert_mis, new_case_alert_jembi)

from .base import MalariaTestCase


class ReportedCaseAdminTest(MalariaTestCase):
    def setUp(self):
        super(ReportedCaseAdminTest, self).setUp()
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_jembi, sender=ReportedCase)
        User.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.login(username='test', password='test')

    def tearDown(self):
        super(ReportedCaseAdminTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.connect(
            new_case_alert_jembi, sender=ReportedCase)

    @override_settings(FORWARD_TO_JEMBI=False)
    @patch('malaria24.ona.tasks.compile_and_send_jembi.delay')
    def test_setting_disables_send_to_jembi(self, mock_task):
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        data = {
            'action': 'send_jembi_alert',
            '_selected_action': [case.pk]
        }
        list_url = reverse('admin:ona_reportedcase_changelist')
        response = self.client.post(list_url, data, follow=True)
        self.assertFalse(mock_task.called)
        self.assertContains(response, "Sending to Jembi currently disabled.")

    @patch('malaria24.ona.tasks.compile_and_send_jembi.delay')
    def test_only_unsent_cases_sent_to_jembi(self, mock_task):
        case1 = self.mk_case(first_name="John", last_name="Day", gender="male",
                             msisdn="0711111111", landmark_description="None",
                             id_type="said", case_number="20171214-123456-42",
                             abroad="No", locality="None",
                             reported_by="+27721111111",
                             sa_id_number="5608071111083",
                             landmark="School", facility_code="123456",
                             jembi_alert_sent=True)
        case2 = self.mk_case(first_name="Mark", last_name="Day", gender="male",
                             msisdn="0711111112", landmark_description="None",
                             id_type="said", case_number="20171214-123456-56",
                             abroad="No", locality="None",
                             reported_by="+27721111112",
                             sa_id_number="5610031111083",
                             landmark="School", facility_code="123456")
        case1.save()
        case2.save()
        data = {
            'action': 'send_jembi_alert',
            '_selected_action': [case1.pk, case2.pk]
        }
        list_url = reverse('admin:ona_reportedcase_changelist')
        response = self.client.post(list_url, data, follow=True)
        mock_task.assert_called_with(case2.pk)
        self.assertContains(response,
                            "Forwarding all unsent cases to Jembi (total 1).")

    @patch('malaria24.ona.tasks.compile_and_send_jembi.delay')
    def test_task_called_for_each_selected_unsent_case(self, mock_task):
        case1 = self.mk_case(first_name="John", last_name="Day", gender="male",
                             msisdn="0711111111", landmark_description="None",
                             id_type="said", case_number="20171214-123456-42",
                             abroad="No", locality="None",
                             reported_by="+27721111111",
                             sa_id_number="5608071111083",
                             landmark="School", facility_code="123456")
        case2 = self.mk_case(first_name="Mark", last_name="Day", gender="male",
                             msisdn="0711111112", landmark_description="None",
                             id_type="said", case_number="20171214-123456-56",
                             abroad="No", locality="None",
                             reported_by="+27721111112",
                             sa_id_number="5610031111083",
                             landmark="School", facility_code="123456")
        case3 = self.mk_case(first_name="Luke", last_name="Day", gender="male",
                             msisdn="0711111113", landmark_description="None",
                             id_type="said", case_number="20171214-123456-64",
                             abroad="No", locality="None",
                             reported_by="+27721111113",
                             sa_id_number="8112051111083",
                             landmark="School", facility_code="123456")
        case1.save()
        case2.save()
        case3.save()
        data = {
            'action': 'send_jembi_alert',
            '_selected_action': [case1.pk, case2.pk]
        }
        list_url = reverse('admin:ona_reportedcase_changelist')
        response = self.client.post(list_url, data, follow=True)
        mock_task.assert_any_call(case1.pk)
        mock_task.assert_any_call(case2.pk)
        self.assertContains(response,
                            "Forwarding all unsent cases to Jembi (total 2).")
