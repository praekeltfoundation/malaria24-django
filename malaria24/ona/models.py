import logging
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import *


class Digest(models.Model):
    """
    A Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        new_cases = ReportedCase.objects.filter(digest__isnull=True)
        if not new_cases.exists():
            return

        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        new_cases.update(digest=digest)
        return digest

    def send_digest_email(self):
        context = {
            'digest': self,
        }
        text_content = render_to_string('ona/text_digest.txt', context)
        html_content = render_to_string('ona/html_digest.html', context)
        return send_mail(
            subject='Digest of reported Malaria cases %s' % (
                timezone.now().strftime('%x'),),
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=set([actor.email_address
                                for actor
                                in self.recipients.all()]),
            html_message=html_content)


class NationalDigest(models.Model):
    """
    A National Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MANAGER_NATIONAL, MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self):
        provinces = []
        date = datetime.today()
        week = 'Week ' + str(date.strftime("%U")) + ' ' + str(date.year)
        # populate provinces
        total_cases = 0
        total_females = 0
        total_males = 0
        total_under5 = 0
        total_over5 = 0
        for p, p_name in PROVINCES:
            codes = Facility.objects.filter(province=p).values_list(
                'facility_code')
            province_cases = ReportedCase.objects.filter(
                facility_code__in=codes)
            total_cases += province_cases.count()
            females = province_cases.filter(gender__icontains='f').count()
            total_females += females
            males = province_cases.exclude(gender__icontains='f').count()
            total_males += males
            over5 = len([x for x in province_cases if x.age >= 5])
            total_over5 += over5
            under5 = province_cases.count() - over5
            total_under5 += under5
            provinces.append({'province': p_name,
                              'cases': province_cases.count(),
                              'females': females, 'males': males,
                              'under5': under5,
                              'over5': over5,
                              'week': week})
        totals = {}
        totals['total_cases'] = total_cases
        totals['total_females'] = total_females
        totals['total_males'] = total_males
        totals['total_under5'] = total_under5
        totals['total_over5'] = total_over5

        return {
            'digest': self,
            'provinces': provinces,
            'week': week,
            'totals': totals
        }

    def send_digest_email(self):
        context = self.get_digest_email_data()
        text_content = render_to_string(
            'ona/text_national_digest.txt', context)
        html_content = render_to_string('ona/html_national_digest.html',
                                        context)
        return send_mail(
            subject='Digest of reported Malaria cases %s' % (
                timezone.now().strftime('%x'),),
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[actor.email_address
                            for actor
                            in self.recipients.all()],
            html_message=html_content)


class ProvincialDigest(models.Model):
    """
    A Provincial Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self, facility_code):
        district_list = []
        date = datetime.today()
        week = 'Week ' + str(date.strftime("%U")) + ' ' + str(date.year)
        province = Facility.objects.get(
            facility_code=facility_code).province
        districts = Facility.objects.filter(province=province).values_list(
            'district', flat=True).distinct().order_by("district")
        total_cases = 0
        total_females = 0
        total_males = 0
        total_under5 = 0
        total_over5 = 0
        for district in districts:
            district_fac_codes = Facility.objects.filter(
                district=district).values_list(
                    'facility_code',
                    flat=True).distinct().order_by("district")
            district_cases = ReportedCase.objects.filter(
                facility_code__in=district_fac_codes)
            total_cases = district_cases.count()
            females = district_cases.filter(gender__icontains='f').count()
            total_females += females
            males = district_cases.exclude(gender__icontains='f').count()
            total_males = +males
            over5 = len([x for x in district_cases if x.age >= 5])
            total_over5 += over5
            under5 = district_cases.count() - over5
            total_under5 += under5
            district_list.append({
                'district': district,
                'cases': district_cases.count(),
                'females': females, 'males': males,
                'under5': under5,
                'over5': over5,
                'week': week})
        totals = {}
        totals['total_cases'] = total_cases
        totals['total_females'] = total_females
        totals['total_males'] = total_males
        totals['total_under5'] = total_under5
        totals['total_over5'] = total_over5
        return {
            'digest': self,
            'districts': district_list,
            'week': week,
            'totals': totals,
        }

    def send_digest_email(self):
        for manager in Actor.objects.provincial():
            context = self.get_digest_email_data(manager.facility_code)
            text_content = render_to_string(
                'ona/text_provincial_digest.txt', context)
            html_content = render_to_string(
                'ona/html_provincial_digest.html', context)
            mailing_list = set([
                manager.email_address
            ] + [actor.email_address for actor in self.recipients.all()])
            send_mail(
                subject='Digest of reported Malaria cases %s' % (
                    timezone.now().strftime('%x'),),
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=mailing_list,
                html_message=html_content)


class DistrictDigest(models.Model):
    """
    A District Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self, facility_code):
        date = datetime.today()
        week = 'Week ' + str(date.strftime("%U")) + ' ' + str(date.year)
        facility_cases = ReportedCase.objects.filter(
            facility_code=facility_code)
        females = facility_cases.filter(gender__icontains='f').count()
        males = facility_cases.exclude(gender__icontains='f').count()
        over5 = len([x for x in facility_cases if x.age >= 5])
        under5 = facility_cases.count() - over5

        facilities = Facility.objects.filter(facility_code=facility_code)
        if facilities.exists():
            facility_name = facilities.first().facility_name
        else:
            facility_name = 'Unknown (facility code: %s)' % (facility_code,)

        fac_list = [{
            'facility': facility_name,
            'cases': facility_cases.count(),
            'females': females, 'males': males,
            'under5': under5,
            'over5': over5,
            'week': week}]
        return {
            'digest': self,
            'facility': fac_list,
            'week': week,
        }

    def send_digest_email(self):
        for manager in Actor.objects.district():
            context = self.get_digest_email_data(manager.facility_code)
            text_content = render_to_string(
                'ona/text_district_digest.txt', context)
            html_content = render_to_string(
                'ona/html_district_digest.html', context)
            mailing_list = set([
                manager.email_address
            ] + [actor.email_address for actor in self.recipients.all()])
            send_mail(
                subject='Digest of reported Malaria cases %s' % (
                    timezone.now().strftime('%x'),),
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=mailing_list,
                html_message=html_content)


class OnaForm(models.Model):
    uuid = models.CharField(max_length=255)
    form_id = models.CharField(max_length=255, null=True)
    id_string = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=255, null=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title


class ReportedCase(models.Model):
    """
    This is a ReportedCase as captured in Ona.io and synced
    from their API to our database for easy querying.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    locality = models.CharField(max_length=255)
    date_of_birth = models.CharField(max_length=255)
    create_date_time = models.DateTimeField()
    sa_id_number = models.CharField(max_length=255, null=True)
    msisdn = models.CharField(max_length=255)
    id_type = models.CharField(max_length=255)
    abroad = models.CharField(max_length=255)
    reported_by = models.CharField(max_length=255)
    gender = models.CharField(max_length=255)
    facility_code = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, null=True)
    landmark_description = models.CharField(
        max_length=255, null=True, blank=True)
    case_number = models.CharField(
        max_length=255, null=True, blank=True)
    _id = models.CharField(max_length=255)
    _uuid = models.CharField(max_length=255)
    _xform_id_string = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    digest = models.ForeignKey('Digest', null=True, blank=True)
    ehps = models.ManyToManyField('Actor', blank=True)
    form = models.ForeignKey('OnaForm', null=True, blank=True)

    def get_today(self):
        return datetime.today()

    def get_facilities(self):
        return Facility.objects.filter(facility_code=self.facility_code)

    def get_facility_attributes(self, attname):
        return ', '.join([
            getattr(f, attname)
            for f in self.get_facilities() if getattr(f, attname)
        ]) or "Unknown"

    @property
    def facility_names(self):
        return self.get_facility_attributes('facility_name')

    @property
    def provinces(self):
        return self.get_facility_attributes('province')

    @property
    def subdistricts(self):
        return self.get_facility_attributes('subdistrict')

    @property
    def districts(self):
        return self.get_facility_attributes('district')

    @property
    def age(self):
        "Returns the age of the patient"
        today = self.get_today()
        try:
            dob = datetime.strptime(self.date_of_birth, '%Y-%m-%d')
        except ValueError:
            # NOTE: This is an unfortunate side-effect of changing how
            #       date of birth is stored mid-way the data.
            #       There is historical data in Ona that has this
            #       old format.
            dob = datetime.strptime(self.date_of_birth, '%y%m%d')
        return int((today - dob).days / 365)

    def get_ehps(self):
        return Actor.objects.ehps().filter(facility_code=self.facility_code)

    def get_email_context(self):
        return {
            'case': self,
            'ehps': self.get_ehps(),
            'site': Site.objects.get_current(),
        }

    def get_text_email_content(self):
        return render_to_string(
            'ona/text_email.txt', self.get_email_context())

    def get_html_email_content(self):
        return render_to_string(
            'ona/html_email.html', self.get_email_context())

    def get_pdf_email_content(self):
        # use attachment file
        return render_to_string(
            'ona/email_attachment.html', self.get_email_context())

EHP = 'EHP'
CASE_INVESTIGATOR = 'CASE_INVESTIGATOR'
MANAGER_DISTRICT = 'MANAGER_DISTRICT'
MANAGER_PROVINCIAL = 'MANAGER_PROVINCIAL'
MANAGER_NATIONAL = 'MANAGER_NATIONAL'
MIS = 'MIS'

PROVINCES = [
    ('The Eastern Cape', 'The Eastern Cape'),
    ('The Free State', 'The Free State'),
    ('Gauteng', 'Gauteng'),
    ('KwaZulu-Natal', 'KwaZulu-Natal'),
    ('Limpopo', 'Limpopo'),
    ('Mpumalanga', 'Mpumalanga'),
    ('The Northern Cape', 'The Northern Cape'),
    ('North West', 'North West'),
    ('The Western Cape', 'The Western Cape'),
]


class ActorManager(models.Manager):

    def ehps(self):
        return super(ActorManager, self).get_queryset().filter(role=EHP)

    def case_investigators(self):
        return super(ActorManager, self).get_queryset().filter(
            role=CASE_INVESTIGATOR)

    def mis(self):
        return super(ActorManager, self).get_queryset().filter(
            role=MIS)

    def managers(self):
        return super(ActorManager, self).get_queryset().exclude(role=EHP)

    def district(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_DISTRICT)

    def provincial(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_PROVINCIAL)

    def national(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_NATIONAL)


class Actor(models.Model):
    """
    An Actor within the system with a defined role.
    """
    name = models.CharField(max_length=255)
    email_address = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    facility_code = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(choices=[
        (EHP, 'EHP'),
        (CASE_INVESTIGATOR, 'Case Investigator'),
        (MANAGER_DISTRICT, 'District Manager'),
        (MANAGER_PROVINCIAL, 'Provincial Manager'),
        (MANAGER_NATIONAL, 'National Manager'),
        (MIS, 'MIS'),
    ], null=True, max_length=255)
    province = models.CharField(
        max_length=255, null=True, blank=True, choices=PROVINCES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActorManager()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.role)


class SMS(models.Model):
    """
    An SMS sent from the system, for audit trail purposes.
    """
    to = models.CharField(max_length=255)
    content = models.CharField(max_length=255)
    message_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Email(models.Model):
    """
    An Email sent from the system, for audit trail purposes.
    """
    to = models.CharField(max_length=255)
    html_content = models.TextField()
    pdf_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Facility(models.Model):
    facility_code = models.CharField(max_length=255)
    facility_name = models.CharField(max_length=255, null=True, blank=True)
    province = models.CharField(
        max_length=255, null=True, blank=True, choices=PROVINCES)
    district = models.CharField(max_length=255, null=True, blank=True)
    subdistrict = models.CharField(max_length=255, null=True, blank=True)
    phase = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __unicode__(self):
        return u'%s - %s' % (self.facility_code, self.facility_name)

    def to_dict(self):
        return {
            'facility_code': self.facility_code,
            'facility_name': self.facility_name,
            'province': self.province,
            'district': self.district,
            'subdistrict': self.subdistrict,
            'phase': self.phase,
        }


def new_case_alert_ehps(sender, instance, created, **kwargs):
    if not created:
        return

    alert_ehps(instance)


def new_case_alert_case_investigators(sender, instance, created, **kwargs):
    if not created:
        return

    alert_case_investigators(instance)


def new_case_alert_mis(sender, instance, created, **kwargs):
    if not created:
        return

    alert_case_mis(instance)


def alert_ehps(reported_case):
    from malaria24.ona.tasks import send_sms, send_case_email
    ehps = Actor.objects.ehps().filter(
        facility_code=reported_case.facility_code)
    if not ehps.exists():
        logging.warning('No EHPs found for facility code %s.' % (
            reported_case.facility_code,))

    sms_copy = ('New Case: %(case_number)s '
                '%(facility_name)s, %(first_name)s '
                '%(last_name)s, %(locality)s, '
                '%(landmark)s, %(landmark_description)s, age %(age)d, '
                '%(gender)s, phone: %(msisdn)s') % {
        'case_number': reported_case.case_number,
        'facility_name': reported_case.facility_names,
        'first_name': reported_case.first_name,
        'last_name': reported_case.last_name,
        'locality': reported_case.locality,
        'landmark': reported_case.landmark,
        'landmark_description': reported_case.landmark_description,
        'age': reported_case.age,
        'gender': reported_case.gender,
        'msisdn': reported_case.msisdn}

    for ehp in ehps:
        reported_case.ehps.add(ehp)
        if ehp.phone_number and ehp.email_address:
            send_sms.delay(to=ehp.phone_number, content=sms_copy)
            send_case_email.delay(reported_case.pk, [ehp.email_address])
        elif ehp.phone_number:
            send_sms.delay(to=ehp.phone_number, content=sms_copy)
            logging.warning(
                ('Unable to Email report for case %s to %s. '
                 'Missing email_address.') % (
                    reported_case.case_number,
                    ehp))

        elif ehp.email_address:
            send_case_email.delay(reported_case.pk, [ehp.email_address])
            logging.warning(
                ('Unable to SMS report for case %s to %s. '
                 'Missing phone_number.') % (
                    reported_case.case_number,
                    ehp))

    if reported_case.reported_by:
        send_sms.delay(to=reported_case.reported_by,
                       content=('Your reported case for %s %s has been '
                                'assigned case number %s.' % (
                                    reported_case.first_name,
                                    reported_case.last_name,
                                    reported_case.case_number,)))
    else:
        logging.warning(
            ('Unable to SMS case number for case %s. '
             'Missing reported_by.') % (reported_case.case_number,))


def alert_case_investigators(reported_case):
    from malaria24.ona.tasks import send_sms
    case_investigators = Actor.objects.case_investigators().filter(
        facility_code=reported_case.facility_code)

    if not case_investigators.exists():
        logging.warning(
            'No Case Investigators found for facility code %s.' % (
                reported_case.facility_code,))

    for case_investigator in case_investigators:
        if case_investigator.phone_number:
            send_sms.delay(
                to=case_investigator.phone_number,
                content=(
                    'New Case: %(case_number)s '
                    '%(facility_name)s, %(first_name)s '
                    '%(last_name)s, %(locality)s, '
                    '%(landmark)s, %(landmark_description)s, age %(age)d, '
                    '%(gender)s, phone: %(msisdn)s')
                % {
                    'case_number': reported_case.case_number,
                    'facility_name': reported_case.facility_names,
                    'first_name': reported_case.first_name,
                    'last_name': reported_case.last_name,
                    'locality': reported_case.locality,
                    'landmark': reported_case.landmark,
                    'landmark_description': reported_case.landmark_description,
                    'age': reported_case.age,
                    'gender': reported_case.gender,
                    'msisdn': reported_case.msisdn,
                })
        else:
            logging.warning(
                ('Unable to SMS report for case %s to %s. '
                 'Missing phone_number.') % (
                    reported_case.case_number,
                    case_investigator))


def alert_case_mis(reported_case):
    from malaria24.ona.tasks import send_case_email
    facilities = reported_case.get_facilities()
    provinces = set([facility.province for facility in facilities])
    mis_set = Actor.objects.mis().filter(
        province__in=provinces)

    if not mis_set.exists():
        logging.warning(
            'No MIS found for facility code %s.' % (
                reported_case.facility_code,))

    for mis in mis_set:
        if mis.email_address:
            send_case_email.delay(
                reported_case.pk, [mis.email_address])

        else:
            logging.warning(
                ('Unable to Email report for case %s to %s. '
                 'Missing email_address.') % (
                    reported_case.case_number,
                    mis))


post_save.connect(new_case_alert_ehps, sender=ReportedCase)
post_save.connect(new_case_alert_case_investigators, sender=ReportedCase)
post_save.connect(new_case_alert_mis, sender=ReportedCase)
