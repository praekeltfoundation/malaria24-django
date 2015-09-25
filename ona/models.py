from django.db import models


class ReportedCase(models.Model):
    first_name = models.CharField()
    last_name = models.CharField()
    locality = models.CharField()
    date_of_birth = models.CharField()
    create_date_time = models.DateTimeField()
    sa_id_number = models.CharField()
    msisdn = models.CharField()
    id_type = models.CharField()
    abroad = models.CharField()
    reported_by = models.CharField()
    gender = models.CharField()
    facility_code = models.CharField()
    landmark = models.CharField()
    _id = models.CharField()
    _uuid = models.CharField()
    _xform_id_string = models.CharField()
