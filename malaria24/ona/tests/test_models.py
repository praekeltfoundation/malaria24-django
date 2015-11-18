from django.core import mail
from django.db.models.signals import post_save

from testfixtures import LogCapture

import responses

from malaria24.ona.models import (
    ReportedCase, SMS, Digest,
    new_case_alert_ehps, new_case_alert_case_investigators,
    new_case_alert_mis,
    MANAGER_DISTRICT, Facility)

from .base import MalariaTestCase


class CaseInvestigatorTest(MalariaTestCase):

    def setUp(self):
        super(CaseInvestigatorTest, self).setUp()
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)

    def tearDown(self):
        super(CaseInvestigatorTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)

    @responses.activate
    def test_capture_no_case_investigators(self):
        with LogCapture() as log:
            self.mk_case()
            log.check(
                ('root',
                 'WARNING',
                 'No Case Investigators found for facility code '
                 'facility_code.'))

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
        self.mk_case(facility_code=facility.facility_code,
                     case_number='case_number')
        [ci_sms] = SMS.objects.all()
        self.assertEqual(ci_sms.to, ci.phone_number)
        self.assertEqual(
            ci_sms.content,
            'Hello. A new malaria case has been reported at facility_name '
            'with Case no: case_number. Contact your EHP for more details. '
            'Thank you')
        self.assertEqual(ci_sms.message_id, 'the-message-id')


class MISTest(MalariaTestCase):

    def setUp(self):
        super(MISTest, self).setUp()
        post_save.disconnect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)

    def tearDown(self):
        super(MISTest, self).tearDown()
        post_save.connect(
            new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)

    @responses.activate
    def test_capture_no_mis(self):
        with LogCapture() as log:
            self.mk_case()
            log.check(
                ('root',
                 'WARNING',
                 'No MIS found for facility code '
                 'facility_code.'))

    @responses.activate
    def test_capture_no_mis_email_address(self):
        with LogCapture() as log:
            mis = self.mk_mis(email_address='', province='The Province')
            facility = self.mk_facility(
                facility_code='code', province=mis.province)
            case = self.mk_case(facility_code=facility.facility_code)
            log.check(('root',
                       'WARNING',
                       ('Unable to Email report for case %s to %s. '
                        'Missing email_address.') % (
                            case.case_number, mis)))

    @responses.activate
    def test_email_sending(self):
        facility = Facility.objects.create(facility_code='0001',
                                           facility_name='Facility 1',
                                           district='The District',
                                           subdistrict='The Subdistrict',
                                           province='The Province')
        mis = self.mk_mis(province=facility.province)
        case = self.mk_case(facility_code=facility.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.case_number,))
        self.assertEqual(message.to, [mis.email_address])
        self.assertTrue('does not support HTML' in message.body)
        [alternative] = message.alternatives
        content, content_type = alternative
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


class EhpReportedCaseTest(MalariaTestCase):

    def setUp(self):
        super(EhpReportedCaseTest, self).setUp()
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_mis, sender=ReportedCase)

    def tearDown(self):
        super(EhpReportedCaseTest, self).tearDown()
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)
        post_save.connect(
            new_case_alert_mis, sender=ReportedCase)

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
                       ('Unable to SMS report for case %s to %s. '
                        'Missing phone_number.') % (
                            case.case_number, ehp)))

    @responses.activate
    def test_capture_no_ehp_email_address(self):
        with LogCapture() as log:
            ehp = self.mk_ehp(email_address='')
            case = self.mk_case(facility_code=ehp.facility_code)
            log.check(('root',
                       'WARNING',
                       ('Unable to Email report for case %s to %s. '
                        'Missing email_address.') % (
                            case.case_number, ehp)))

    @responses.activate
    def test_capture_no_reported_by(self):
        with LogCapture() as log:
            ehp = self.mk_ehp()
            case = self.mk_case(facility_code=ehp.facility_code,
                                reported_by='')
            log.check(('root',
                       'WARNING',
                       ('Unable to SMS case number for case %s. '
                        'Missing reported_by.') % (
                            case.case_number)))

    @responses.activate
    def test_capture_all_ok(self):
        self.assertEqual(SMS.objects.count(), 0)
        ehp = self.mk_ehp()
        case = self.mk_case(facility_code=ehp.facility_code)
        [ehp_sms, reporter_sms] = SMS.objects.all()
        self.assertEqual(ehp_sms.to, 'phone_number')
        self.assertEqual(ehp_sms.content,
                         'A new case has been reported, the full report will '
                         'be sent to you via email.')
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
        case = self.mk_case(facility_code=facility.facility_code)
        [message] = mail.outbox
        self.assertEqual(message.subject,
                         'Malaria case number %s' % (case.case_number,))
        self.assertEqual(message.to, [ehp.email_address])
        self.assertTrue('does not support HTML' in message.body)
        [alternative] = message.alternatives
        content, content_type = alternative
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

    @responses.activate
    def test_age(self):
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


class DigestTest(MalariaTestCase):

    def setUp(self):
        super(DigestTest, self).setUp()
        post_save.disconnect(new_case_alert_ehps, sender=ReportedCase)
        post_save.disconnect(
            new_case_alert_case_investigators, sender=ReportedCase)

    def tearDown(self):
        super(DigestTest, self).tearDown()
        post_save.connect(new_case_alert_ehps, sender=ReportedCase)
        post_save.connect(
            new_case_alert_case_investigators, sender=ReportedCase)

    @responses.activate
    def test_compile_digest(self):
        manager1 = self.mk_actor(role='MANAGER_DISTRICT')
        manager2 = self.mk_actor(role='MANAGER_DISTRICT')
        cases = [self.mk_case() for i in range(10)]
        digest = Digest.compile_digest()
        self.assertEqual([manager1, manager2],
                         list(digest.recipients.all().order_by('pk')))
        self.assertEqual([c.pk for c in cases],
                         [c.pk for c in digest.reportedcase_set.all()])

    @responses.activate
    def test_send_digest_email(self):
        manager1 = self.mk_actor(role=MANAGER_DISTRICT,
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
        self.assertEqual(message.to, [
            manager1.email_address,
            ehp1.email_address,
            ehp2.email_address,
            mis.email_address])
