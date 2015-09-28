from django.conf import settings

from malaria24 import celery_app

from onapie.client import Client

from ona.models import ReportedCase


@celery_app.task
def ona_fetch_reported_cases():
    client = Client('https://ona.io', api_token=settings.ONAPIE_ACCESS_TOKEN,
                    api_entrypoint='/api/v1/')
    form_data_list = client.data.get(settings.ONAPIE_FORM_PK)
    for data in form_data_list:
        if ReportedCase.objects.filter(_uuid=data['_uuid']).exists():
            continue

    ReportedCase.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        locality=data['locality'],
        date_of_birth=data['date_of_birth'],
        create_date_time=data['create_date_time'],
        sa_id_number=data['sa_id_number'],
        msisdn=data['msisdn'],
        id_type=data['id_type'],
        abroad=data['abroad'],
        reported_by=data['reported_by'],
        gender=data['gender'],
        facility_code=data['facility_code'],
        landmark=data['landmark'],
        _id=data['_id'],
        _uuid=data['_uuid'],
        _xform_id_string=data['_xform_id_string'])
