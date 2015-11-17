import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.template.loader import render_to_string
from django.utils import timezone

from datetime import datetime


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

        managers = Actor.objects.managers().filter(
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = managers
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
            recipient_list=[actor.email_address
                            for actor
                            in self.recipients.all()],
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
    landmark_description = models.CharField(max_length=255, null=True)
    case_number = models.CharField(max_length=255, null=True)
    _id = models.CharField(max_length=255)
    _uuid = models.CharField(max_length=255)
    _xform_id_string = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    digest = models.ForeignKey('Digest', null=True, blank=True)
    ehps = models.ManyToManyField('Actor', blank=True)
    form = models.ForeignKey('OnaForm', null=True, blank=True)

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
        today = datetime.today()
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

EHP = 'EHP'
CASE_INVESTIGATOR = 'CASE_INVESTIGATOR'
MANAGER_DISTRICT = 'MANAGER_DISTRICT'
MANAGER_PROVINCIAL = 'MANAGER_PROVINCIAL'
MANAGER_NATIONAL = 'MANAGER_NATIONAL'


class ActorManager(models.Manager):

    def ehps(self):
        return super(ActorManager, self).get_queryset().filter(role=EHP)

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
    ], null=True, max_length=255)
    province = models.CharField(
        max_length=255, null=True, blank=True, choices=[
            ('EC', 'The Eastern Cape'),
            ('FS', 'The Free State'),
            ('GP', 'Gauteng'),
            ('KZN', 'KwaZulu-Natal'),
            ('LP', 'Limpopo'),
            ('MP', 'Mpumalanga'),
            ('NC', 'The Northern Cape'),
            ('NW', 'North West'),
            ('WC)', 'The Western Cape'),
        ])
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


class Facility(models.Model):
    facility_code = models.CharField(max_length=255)
    facility_name = models.CharField(max_length=255, null=True, blank=True)
    province = models.CharField(max_length=255, null=True, blank=True)
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


def alert_new_case(sender, instance, created, **kwargs):
    from malaria24.ona.tasks import send_sms, send_case_email
    if not created:
        return

    ehps = Actor.objects.ehps().filter(facility_code=instance.facility_code)
    if not ehps.exists():
        logging.warning('No EHPs found for facility code %s.' % (
            instance.facility_code,))

    for ehp in ehps:
        instance.ehps.add(ehp)
        if ehp.phone_number and ehp.email_address:
            send_sms.delay(to=ehp.phone_number,
                           content=('A new case has been reported, the full '
                                    'report will be sent to you via email.'))
            send_case_email.delay(instance.pk)
        elif ehp.phone_number:
            logging.warning(
                ('Unable to Email report for case %s. '
                 'Missing email_address.') % (instance.case_number))

        elif ehp.email_address:
            logging.warning(
                ('Unable to SMS report for case %s. '
                 'Missing phone_number.') % (instance.case_number))

    if instance.reported_by:
        send_sms.delay(to=instance.reported_by,
                       content=('Your reported case for %s %s has been '
                                'assigned case number %s.' % (
                                    instance.first_name,
                                    instance.last_name,
                                    instance.case_number,)))
    else:
        logging.warning(
            ('Unable to SMS case number for case %s. '
             'Missing reported_by.') % (instance.case_number,))


post_save.connect(alert_new_case, sender=ReportedCase)
