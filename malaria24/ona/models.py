import logging

from django.db import models
from django.db.models.signals import post_save


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
    _id = models.CharField(max_length=255)
    _uuid = models.CharField(max_length=255)
    _xform_id_string = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

EHP = 'EHP'
MANAGER_DISTRICT = 'MANAGER_DISTRICT'
MANAGER_PROVINCIAL = 'MANAGER_PROVINCIAL'
MANAGER_NATIONAL = 'MANAGER_NATIONAL'


class ActorManager(models.Manager):

    def ehps(self):
        return super(ActorManager, self).get_queryset().filter(role=EHP)

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
    email_address = models.EmailField(null=True)
    phone_number = models.CharField(max_length=255, null=True)
    facility_code = models.CharField(max_length=255, null=True)
    role = models.CharField(choices=[
        (EHP, 'EHP'),
        (MANAGER_DISTRICT, 'District Manager'),
        (MANAGER_PROVINCIAL, 'Provincial Manager'),
        (MANAGER_NATIONAL, 'National Manager'),
    ], null=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActorManager()


class SMS(models.Model):
    """
    An SMS sent from the system, for audit trail purposes.
    """
    to = models.CharField(max_length=255)
    content = models.CharField(max_length=255)
    message_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


def alert_new_case(sender, instance, created, **kwargs):
    from malaria24.ona.tasks import send_sms, send_case_email
    if not created:
        return

    ehps = Actor.objects.ehps().filter(facility_code=instance.facility_code)
    if not ehps.exists():
        logging.warning('No EHPs found for facility code %s.' % (
            instance.facility_code,))

    for ehp in ehps:
        if ehp.phone_number and ehp.email_address:
            send_sms.delay(to=ehp.phone_number,
                           content=('A new case has been reported, the full '
                                    'report will be sent to you via email.'))
            send_case_email.delay(instance.pk)
        elif ehp.phone_number:
            logging.warning(
                ('Unable to Email report for case %s. '
                 'Missing email_address.') % (instance.pk))

        elif ehp.email_address:
            logging.warning(
                ('Unable to SMS report for case %s. '
                 'Missing phone_number.') % (instance.pk))

        if instance.reported_by:
            send_sms.delay(to=instance.reported_by,
                           content=('Your reported case has been assigned '
                                    'case number %s.' % (
                                        instance.pk,)))
        else:
            logging.warning(
                ('Unable to SMS case number for case %s. '
                 'Missing reported_by.') % (instance.pk,))


post_save.connect(alert_new_case, sender=ReportedCase)
