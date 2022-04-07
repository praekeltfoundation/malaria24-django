from django.core import mail
from django.db.models.signals import post_save
from django.test import override_settings
from datetime import datetime
from testfixtures import LogCapture
from mock import patch


import responses

from malaria24.ona.models import (
    ReportedCase, SMS, Digest,
    new_case_alert_ehps, new_case_alert_case_investigators,
    new_case_alert_mis, new_case_alert_jembi,
    MANAGER_DISTRICT, MIS, MANAGER_NATIONAL, DistrictDigest,
    MANAGER_PROVINCIAL, Facility, NationalDigest, ProvincialDigest)
from malaria24.ona import tasks

from .base import MalariaTestCase


class CaseInvestigatorTest(MalariaTestCase):

    def setUp(self):
        super(CaseInvestigatorTest, self).setUp()
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_jembi, sender=ReportedCase)

    def tearDown(self):
        super(CaseInvestigatorTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.connect(
            new_case_alert_jembi, sender=ReportedCase)

    @responses.activate
    def test_capture_no_case_investigators(self):
        with LogCapture() as log:
            self.mk_case()
            log.check(
                ('root',
                 'WARNING',
                 'No Case Investigators found for facility code facility_code.'))

    @responses.activate
    def test_capture_no_case_investigator_phonenumber(self):
        with LogCapture() as log:
            facility = self.mk_facility(facility_code='code')
            ci = self.mk_ci(
                phone_number='',
                facility_code=facility.facility_code)
            case = self.mk_case(facility_code=facility.facility_code)
            log.check(('root',
                       'WARNING',
                       ('Unable to SMS report for case %s to %s. '
                        'Missing phone_number.') % (
                            case.case_number, ci)))

    @responses.activate
    def test_capture_all_ok(self):
        self.assertEqual(SMS.objects.count(), 0)
        facility = self.mk_facility(
            facility_name='facility_name',
            facility_code='facility_code')
        ci = self.mk_ci(facility_code=facility.facility_code)
        case = self.mk_case(
            facility_code=facility.facility_code,
            case_number='case_number')
        [ci_sms] = SMS.objects.all()
        self.assertEqual(ci_sms.to, ci.phone_number)
        self.assertEqual(
            ci_sms.content,
            'New Case: case_number facility_name, '
            'first_name last_name, '
            'locality, landmark, landmark_description, '
            'age %d, gender, '
            'phone: msisdn' % case.age)
        self.assertEqual(ci_sms.message_id, 'the-message-id')


class MISTest(MalariaTestCase):

    def setUp(self):
        super(MISTest, self).setUp()
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_jembi, sender=ReportedCase)

    def tearDown(self):
        super(MISTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.connect(
            new_case_alert_jembi, sender=ReportedCase)

    @responses.activate
    def test_capture_no_mis(self):
        with LogCapture() as log:
            self.mk_case()
            log.check(
                ('root',
                 'WARNING',
                 'No MIS found for facility code facility_code.'))

    @responses.activate
    def test_capture_no_mis_email_address(self):
        with LogCapture() as log:
            mis = self.mk_mis(email_address='', province='The Province')
            facility = self.mk_facility(
                facility_code='code', province=mis.province)
            case = self.mk_case(facility_code=facility.facility_code)
            log.check_present(('root',
                               'WARNING',
                               (f'Unable to Email report for '
                                f'case {case.case_number} to '
                                f'{mis.name} ({mis.role}). Missing email_address.')))

    @responses.activate
    def test_email_sending(self):
        facility = Facility.objects.create(facility_code='0001',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        mis = self.mk_mis(province=facility.province)
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(facility_code=facility.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.case_number,))
        self.assertEqual(message.to, [mis.email_address])
        self.assertTrue('does not support HTML' in message.body)
        [html_alternative] = message.alternatives
        [pdf_attachment] = message.attachments
        content, content_type = html_alternative
        self.assertTrue(case.facility_code in content)
        self.assertTrue(case.sa_id_number in content)
        self.assertTrue('The District' in content)
        self.assertTrue('The Subdistrict' in content)
        self.assertTrue('The Province' in content)
        self.assertTrue('landmark' in content)
        self.assertTrue('landmark_description' in content)
        self.assertTrue(
            'http://example.com/static/ona/img/logo.png' in content)
        self.assertEqual('text/html', content_type)
        self.assertEqual(('Reported_Case_None.pdf',
                          'garbage for testing', 'application/pdf'),
                         pdf_attachment)

    @responses.activate
    def test_email_sending_when_same_actor_multiple_facilities(self):
        facility = Facility.objects.create(facility_code='0001',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        facility = Facility.objects.create(facility_code='0002',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        self.mk_mis(province=facility.province, facility_code='0001')
        self.mk_mis(province=facility.province, facility_code='0002')
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            self.mk_case(facility_code=facility.facility_code)

        self.assertEqual(len(mail.outbox), 1)


class EhpReportedCaseTest(MalariaTestCase):

    def setUp(self):
        super(EhpReportedCaseTest, self).setUp()
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_jembi, sender=ReportedCase)

    def tearDown(self):
        super(EhpReportedCaseTest, self).tearDown()
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.connect(
            new_case_alert_jembi, sender=ReportedCase)

    @responses.activate
    def test_capture_no_ehps(self):
        with LogCapture() as log:
            self.mk_case()
            log.check_present(('root',
                               'WARNING',
                               'No EHPs found for facility code facility_code.'))

    @responses.activate
    def test_capture_no_ehp_phonenumber(self):
        with LogCapture() as log:
            ehp = self.mk_ehp(phone_number='')
            case = self.mk_case(facility_code=ehp.facility_code)
            log.check_present(('root',
                               'WARNING',
                               ('Unable to SMS report for case %s to %s. '
                                'Missing phone_number.') % (
                                   case.case_number, ehp)))

    @responses.activate
    def test_capture_no_ehp_email_address(self):
        with LogCapture() as log:
            ehp = self.mk_ehp(email_address='')
            case = self.mk_case(facility_code=ehp.facility_code)
            log.check_present(('root',
                               'WARNING',
                               ('Unable to Email report for case %s to %s. '
                                'Missing email_address.') % (
                                   case.case_number, ehp)))

    @responses.activate
    def test_capture_no_reported_by(self):
        with LogCapture() as log:
            ehp = self.mk_ehp()
            with patch.object(tasks, 'make_pdf') as mock_make_pdf:
                mock_make_pdf.return_value = 'garbage for testing'
                case = self.mk_case(facility_code=ehp.facility_code,
                                    reported_by='')
            log.check_present(('root',
                               'WARNING',
                               ('Unable to SMS case number for case %s. '
                                'Missing reported_by.') % (
                                   case.case_number)))

    @responses.activate
    def test_capture_all_ok(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp()
        self.mk_facility(
            facility_name='facility_name', facility_code='facility_code')
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(
                facility_code=ehp.facility_code, case_number='case_number')

        [ehp_sms, reporter_sms] = SMS.objects.all()
        self.assertEqual(ehp_sms.to, 'phone_number')
        self.assertEqual(
            ehp_sms.content,
            'New Case: case_number facility_name, '
            'first_name last_name, '
            'locality, landmark, landmark_description, '
            'age %d, gender, '
            'phone: msisdn' % case.age)
        self.assertEqual(ehp_sms.message_id, 'the-message-id')
        self.assertEqual(reporter_sms.to, 'reported_by')
        self.assertEqual(
            reporter_sms.content,
            ('Your reported case for %s %s has been '
             'assigned case number %s.') % (
                case.first_name, case.last_name, case.case_number))
        self.assertEqual(reporter_sms.message_id, 'the-message-id')

    @responses.activate
    def test_capture_phone_number_only(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp(email_address='')
        self.mk_facility(
            facility_name='facility_name', facility_code='facility_code')
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(
                facility_code=ehp.facility_code, case_number='case_number')

        [ehp_sms, reporter_sms] = SMS.objects.all()
        self.assertEqual(ehp_sms.to, 'phone_number')
        self.assertEqual(
            ehp_sms.content,
            'New Case: case_number facility_name, '
            'first_name last_name, '
            'locality, landmark, landmark_description, '
            'age %d, gender, '
            'phone: msisdn' % case.age)
        self.assertEqual(ehp_sms.message_id, 'the-message-id')
        self.assertEqual(reporter_sms.to, 'reported_by')
        self.assertEqual(
            reporter_sms.content,
            ('Your reported case for %s %s has been '
             'assigned case number %s.') % (
                case.first_name, case.last_name, case.case_number))
        self.assertEqual(reporter_sms.message_id, 'the-message-id')

    @responses.activate
    def test_idempotency(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp()
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(facility_code=ehp.facility_code)
            case.save()
        self.assertEqual(SMS.objects.count(), 2)

    @responses.activate
    def test_email_sending(self):
        facility = Facility.objects.create(facility_code='0001',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        ehp = self.mk_ehp(facility_code=facility.facility_code)
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(facility_code=facility.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.case_number,))
        self.assertEqual(message.to, [ehp.email_address])
        self.assertTrue('does not support HTML' in message.body)
        [html_alternative] = message.alternatives
        [pdf_attachment] = message.attachments
        content, content_type = html_alternative
        self.assertTrue(case.facility_code in content)
        self.assertTrue(case.sa_id_number in content)
        self.assertTrue('The District' in content)
        self.assertTrue('The Subdistrict' in content)
        self.assertTrue('The Province' in content)
        self.assertTrue('landmark' in content)
        self.assertTrue('landmark_description' in content)
        self.assertTrue(
            'http://example.com/static/ona/img/logo.png' in content)
        self.assertEqual('text/html', content_type)
        self.assertEqual(('Reported_Case_None.pdf',
                          'garbage for testing', 'application/pdf'),
                         pdf_attachment)

    @responses.activate
    def test_email_sending_when_no_phone_number_specified(self):
        facility = Facility.objects.create(facility_code='0001',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        ehp = self.mk_ehp(
            facility_code=facility.facility_code,
            phone_number='')
        with patch.object(tasks, 'make_pdf') as mock_make_pdf:
            mock_make_pdf.return_value = 'garbage for testing'
            case = self.mk_case(facility_code=facility.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.case_number,))
        self.assertEqual(message.to, [ehp.email_address])
        self.assertTrue('does not support HTML' in message.body)
        [html_alternative] = message.alternatives
        [pdf_attachment] = message.attachments
        content, content_type = html_alternative
        self.assertTrue(case.facility_code in content)
        self.assertTrue(case.sa_id_number in content)
        self.assertTrue('The District' in content)
        self.assertTrue('The Subdistrict' in content)
        self.assertTrue('The Province' in content)
        self.assertTrue('landmark' in content)
        self.assertTrue('landmark_description' in content)
        self.assertTrue(
            'http://example.com/static/ona/img/logo.png' in content)
        self.assertEqual('text/html', content_type)
        self.assertEqual(('Reported_Case_None.pdf',
                          'garbage for testing', 'application/pdf'),
                         pdf_attachment)

    @responses.activate
    def test_age(self):
        with patch.object(ReportedCase, 'get_today') as patch_today:
            patch_today.return_value = datetime(2015, 1, 1)
            case = self.mk_case(date_of_birth="1982-01-01")
            self.assertEqual(33, case.age)

    @responses.activate
    def test_facility_name(self):
        Facility.objects.create(facility_code='0001',
                                facility_name='Facility 1')
        case1 = self.mk_case(facility_code='0001')
        case2 = self.mk_case(facility_code='0002')
        self.assertEqual(case1.facility_names, 'Facility 1')
        self.assertEqual(case2.facility_names, 'Unknown')


class JembiReportedCaseTest(MalariaTestCase):

    def setUp(self):
        super(JembiReportedCaseTest, self).setUp()
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        '''self.complete_url = ("{}?criteria=value:{}"
                             .format('http://jembi.org/malaria24'))'''

    def tearDown(self):
        super(JembiReportedCaseTest, self).tearDown()
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)

    def test_compile_data(self):
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        d = case.get_data()
        self.assertEqual(case.get_data(), d)

    @override_settings(FORWARD_TO_JEMBI=False)
    @patch('malaria24.ona.tasks.compile_and_send_jembi.delay')
    def test_setting_prevents_task_call(self, mock_task):
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        mock_task.not_called()

    @patch('malaria24.ona.tasks.compile_and_send_jembi.delay')
    def test_case_creation_triggers_task(self, mock_task):
        case = self.mk_case(first_name="John", last_name="Day", gender="male",
                            msisdn="0711111111", landmark_description="None",
                            id_type="said", case_number="20171214-123456-42",
                            abroad="No", locality="None",
                            reported_by="+27721111111",
                            sa_id_number="5608071111083",
                            landmark="School", facility_code="123456")
        case.save()
        case.digest = None
        mock_task.assert_called_with(case.pk)


class DigestTest(MalariaTestCase):

    def setUp(self):
        super(DigestTest, self).setUp()
        post_save.disconnect(new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_jembi, sender=ReportedCase)

    def tearDown(self):
        super(DigestTest, self).tearDown()
        post_save.connect(new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.connect(
            new_case_alert_jembi, sender=ReportedCase)

    def get_week(self, cases):
        test_cases = ReportedCase.objects.all().order_by("create_date_time")
        start_date = test_cases \
            .first().create_date_time.strftime(
                "%d %B %Y"
            )
        end_date = test_cases \
            .last().create_date_time.strftime(
                "%d %B %Y"
            )
        return "{0} to {1}".format(start_date, end_date)

    @responses.activate
    def test_compile_digest(self):
        manager1 = self.mk_actor(role='MIS')
        cases = [self.mk_case() for i in range(10)]
        digest = Digest.compile_digest()
        self.assertEqual([manager1],
                         list(digest.recipients.all().order_by('pk')))
        self.assertEqual([c.pk for c in cases],
                         [c.pk for c in digest.reportedcase_set.all()])

    @responses.activate
    def test_send_digest_email(self):
        Facility.objects.create(facility_code='0001',
                                facility_name='Facility 1')
        self.mk_actor(role=MANAGER_DISTRICT,
                      email_address='manager@example.org')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')
        mis = self.mk_mis(name='MIS', email_address='mis@example.org')

        for i in range(10):
            case = self.mk_case()
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()

        digest = Digest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        self.assertEqual(message.body.count('EHP1, EHP2'), 10)
        self.assertEqual(html_content.count('EHP1, EHP2'), 10)
        self.assertEqual(message.to, [mis.email_address])

    @responses.activate
    def test_send_digest_email_with_blank_emails(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_DISTRICT,
                      email_address='manager@example.org',
                      district=u'Example1', facility_code='342315'
                      )
        # first MIS
        self.mk_actor(role=MIS,
                      email_address='mis@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # second MIS to show that its collecting more than 1
        self.mk_actor(role=MIS,
                      email_address='mis2@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # None email address must be skipped
        self.mk_actor(role=MIS,
                      email_address=None,
                      facility_code='342315', district=u'Example1'
                      )
        # Blank email address must be skipped
        self.mk_actor(role=MIS,
                      email_address='',
                      facility_code='342315', district=u'Example1'
                      )

        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for _ in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = Digest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        self.assertEquals(len(message.to), 2)
        self.assertEquals(
            set(message.to),
            set(['mis2@example.com', 'mis@example.com'])
        )

    @responses.activate
    def test_district_digest_email_data(self):
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
        manager1 = self.mk_actor(role=MANAGER_DISTRICT,
                                 email_address='manager@example.org',
                                 district=u'Example1', facility_code='342315')
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

        digest = DistrictDigest.compile_digest()
        data = digest.get_digest_email_data(
            manager1.district, None)
        self.assertEqual(data['facility'][0]['females'], 10)
        self.assertEqual(data['facility'][0]['males'], 0)
        self.assertEqual(data['facility'][0]['facility'], 'Facility 1')
        self.assertEqual(data['facility'][1]['facility'], 'Facility 2')
        self.assertEqual(data['facility'][0]['under5'], 10)
        self.assertEqual(data['facility'][0]['over5'], 0)
        self.assertEqual(len(data['facility']), 2)
        self.assertEqual(
            data['week'], self.get_week(ReportedCase.objects.all()))

    @responses.activate
    def test_national_digest_email_data(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        Facility.objects.create(facility_code='343434',
                                facility_name='Facility 2',
                                province='Limpopo',
                                district=u'Example2')
        Facility.objects.create(facility_code='111111',
                                facility_name='Facility 1',
                                province='Gauteng',
                                district=u'Example4')
        Facility.objects.create(facility_code='333333',
                                facility_name='Facility 3',
                                province='The Eastern Cape',
                                district=u'Example5')
        self.mk_actor(role=MANAGER_NATIONAL,
                      email_address='manager@example.org')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')
        self.mk_mis(name='MIS', email_address='mis@example.org')

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
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

        for i in range(10):
            case = self.mk_case(gender='male', facility_code='111111')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(gender='female', facility_code='343434')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = NationalDigest.compile_digest()
        data = digest.get_digest_email_data()
        self.assertEqual(len(data['provinces']), 4)
        self.assertEqual(data['totals']['total_females'], 20)
        self.assertEqual(data['totals']['total_males'], 20)
        self.assertEqual(data['provinces'][1]['province'], 'Gauteng')
        self.assertEqual(data['provinces'][1]['under5'], 10)
        self.assertEqual(data['provinces'][1]['over5'], 0)
        self.assertEqual(
            data['week'], self.get_week(ReportedCase.objects.all()))

    @responses.activate
    def test_send_national_digest_email(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        Facility.objects.create(facility_code='222222',
                                facility_name='Facility 2',
                                province='The Eastern Cape',
                                district=u'Example2')
        self.mk_actor(role=MANAGER_NATIONAL,
                      email_address='manager@example.org')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')
        self.mk_mis(name='MIS', email_address='mis@example.org')

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

        digest = NationalDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data()
        self.assertEqual(
            data['week'], self.get_week(ReportedCase.objects.all()))
        self.assertEqual(data['provinces'][1]['females'], 10)
        self.assertEqual(data['provinces'][1]['males'], 0)
        self.assertEqual(data['provinces'][0]['males'], 10)
        self.assertEqual(data['provinces'][1]['province'], 'Limpopo')
        self.assertEqual(data['provinces'][1]['under5'], 10)
        self.assertEqual(data['provinces'][1]['over5'], 0)
        self.assertEqual(len(data['provinces']), 2)
        self.assertEqual(data['totals']['total_females'], 10)
        self.assertEqual(
            set(message.to), set(['manager@example.org', 'mis@example.org']))

    @responses.activate
    def test_send_national_digest_email_with_blank_emails(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_NATIONAL,
                      email_address='manager@example.org',
                      district=u'Example1', facility_code='342315'
                      )
        # first MIS
        self.mk_actor(role=MIS,
                      email_address='mis@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # second MIS to show that its collecting more than 1
        self.mk_actor(role=MIS,
                      email_address='mis2@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # None email address must be skipped
        self.mk_actor(role=MIS,
                      email_address=None,
                      facility_code='342315', district=u'Example1'
                      )
        # Blank email address must be skipped
        self.mk_actor(role=MIS,
                      email_address='',
                      facility_code='342315', district=u'Example1'
                      )

        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for _ in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = NationalDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        self.assertEquals(len(message.to), 3)
        self.assertEquals(
            set(message.to),
            set(['manager@example.org', 'mis2@example.com', 'mis@example.com'])
        )

    @responses.activate
    def test_send_provincial_digest_email(self):
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
        manager1 = self.mk_actor(role=MANAGER_PROVINCIAL,
                                 email_address='manager@example.org',
                                 province='Limpopo', facility_code='342315')
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

        digest = ProvincialDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data(manager1.province, None)
        self.assertEqual(
            data['week'], self.get_week(ReportedCase.objects.all()))
        self.assertEqual(data['districts'][0]['district'], u'Example1')
        self.assertEqual(data['districts'][0]['females'], 10)
        self.assertEqual(data['districts'][0]['males'], 0)
        self.assertEqual(data['districts'][0]['under5'], 10)
        self.assertEqual(data['districts'][0]['over5'], 0)
        self.assertEqual(len(data['districts']), 2)
        self.assertEqual(data['totals']['total_females'], 10)
        self.assertEqual(
            set(message.to), set(['manager@example.org', 'mis@example.org']))
        data = digest.get_digest_email_data(None, manager1.facility_code)
        self.assertEqual(data['districts'][0]['district'], u'Example1')
        self.mk_actor(
            role=MANAGER_PROVINCIAL, email_address='manager2@example.org')
        digest = ProvincialDigest.compile_digest()
        digest.send_digest_email()
        message = mail.outbox[0]
        data = digest.get_digest_email_data(None, None)
        self.assertEqual(data, {})
        self.assertEqual(
            set(message.to), set(['manager@example.org', 'mis@example.org']))

    @responses.activate
    def test_send_provincial_digest_email_with_blank_emails(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_PROVINCIAL,
                      email_address='manager@example.org',
                      district=u'Example1', facility_code='342315'
                      )
        # first MIS
        self.mk_actor(role=MIS,
                      email_address='mis@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # second MIS to show that its collecting more than 1
        self.mk_actor(role=MIS,
                      email_address='mis2@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # None email address must be skipped
        self.mk_actor(role=MIS,
                      email_address=None,
                      facility_code='342315', district=u'Example1'
                      )
        # Blank email address must be skipped
        self.mk_actor(role=MIS,
                      email_address='',
                      facility_code='342315', district=u'Example1'
                      )

        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for _ in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = ProvincialDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        self.assertEquals(len(message.to), 3)
        self.assertEquals(
            set(message.to),
            set(['manager@example.org', 'mis2@example.com', 'mis@example.com'])
        )

    @responses.activate
    def test_send_district_digest_email(self):
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
        manager1 = self.mk_actor(role=MANAGER_DISTRICT,
                                 email_address='manager@example.org',
                                 district=u'Example1', facility_code='342315')
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

        digest = DistrictDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data(
            manager1.district, None)
        self.assertEqual(
            data['week'], self.get_week(ReportedCase.objects.all()))
        self.assertEqual(data['facility'][0]['facility'], 'Facility 1')
        self.assertEqual(data['facility'][0]['females'], 10)
        self.assertEqual(data['facility'][0]['males'], 0)
        self.assertEqual(data['facility'][0]['under5'], 10)
        self.assertEqual(data['facility'][1]['facility'], 'Facility 2')
        self.assertEqual(data['facility'][1]['males'], 10)
        self.assertEqual(data['facility'][1]['under5'], 10)
        self.assertEqual(data['facility'][0]['over5'], 0)
        self.assertEqual(data['totals']['total_under5'], 20)
        self.assertEqual(len(data['facility']), 2)
        self.assertEqual(
            set(message.to), set(['manager@example.org', 'mis@example.org']))

        data = digest.get_digest_email_data(
            None, manager1.facility_code)
        self.assertEqual(data['facility'][0]['facility'], 'Facility 1')
        data = digest.get_digest_email_data(None, None)
        self.assertEqual(data, {})
        self.mk_actor(
            role=MANAGER_PROVINCIAL, email_address='manager2@example.org')
        digest = DistrictDigest.compile_digest()
        digest.send_digest_email()
        message = mail.outbox[0]
        data = digest.get_digest_email_data(None, None)
        self.assertEqual(data, {})
        self.assertEqual(
            set(message.to), set(['manager@example.org', 'mis@example.org']))

    @responses.activate
    def test_send_district_digest_email_with_blank_emails(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MANAGER_DISTRICT,
                      email_address='manager@example.org',
                      district=u'Example1', facility_code='342315'
                      )
        # first MIS
        self.mk_actor(role=MIS,
                      email_address='mis@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # second MIS to show that its collecting more than 1
        self.mk_actor(role=MIS,
                      email_address='mis2@example.com',
                      facility_code='342315', district=u'Example1'
                      )
        # None email address must be skipped
        self.mk_actor(role=MIS,
                      email_address=None,
                      facility_code='342315', district=u'Example1'
                      )
        # Blank email address must be skipped
        self.mk_actor(role=MIS,
                      email_address='',
                      facility_code='342315', district=u'Example1'
                      )

        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for _ in range(10):
            case = self.mk_case(gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = DistrictDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        self.assertEquals(len(message.to), 3)
        self.assertEquals(
            set(message.to),
            set(['manager@example.org', 'mis2@example.com', 'mis@example.com'])
        )

    @responses.activate
    def test_send_with_old_and_new_data_district(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        manager1 = self.mk_actor(role=MANAGER_DISTRICT,
                                 email_address='manager@example.org',
                                 facility_code='342315')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            digest = Digest.objects.create()
            case = self.mk_case(
                gender='female', facility_code='342315', digest=digest)
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(
                gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = DistrictDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data(
            manager1.district, manager1.facility_code)
        self.assertEqual(data['facility'][0]['females'], 10)

    @responses.activate
    def test_send_with_old_and_new_data_provincial(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        manager1 = self.mk_actor(role=MANAGER_PROVINCIAL,
                                 email_address='manager@example.org',
                                 facility_code='342315')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            digest = Digest.objects.create()
            case = self.mk_case(
                gender='female', facility_code='342315', digest=digest)
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(
                gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = ProvincialDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data(
            manager1.province, manager1.facility_code)
        self.assertEqual(data['districts'][0]['females'], 10)

    @responses.activate
    def test_send_with_old_and_new_data_national(self):
        Facility.objects.create(facility_code='342315',
                                facility_name='Facility 1',
                                province='Limpopo',
                                district=u'Example1')
        self.mk_actor(role=MIS,
                      email_address='mis@example.org',
                      facility_code='342315')
        ehp1 = self.mk_ehp(name='EHP1', email_address='ehp1@example.org')
        ehp2 = self.mk_ehp(name='EHP2', email_address='ehp2@example.org')

        for i in range(10):
            digest = Digest.objects.create()
            case = self.mk_case(
                gender='female', facility_code='342315', digest=digest)
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        for i in range(10):
            case = self.mk_case(
                gender='female', facility_code='342315')
            case.date_of_birth = datetime.today().strftime("%y%m%d")
            case.ehps.add(ehp1)
            case.ehps.add(ehp2)
            case.save()
            case.digest = None

        digest = NationalDigest.compile_digest()
        digest.send_digest_email()
        [message] = mail.outbox
        [alternative] = message.alternatives
        html_content, content_type = alternative
        data = digest.get_digest_email_data()
        self.assertEqual(data['provinces'][0]['females'], 10)
