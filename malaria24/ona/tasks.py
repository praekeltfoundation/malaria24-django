from django.conf import settings

from malaria24 import celery_app

from onapie.client import Client

from malaria24.ona.models import ReportedCase, SMS

from go_http.send import HttpApiSender


@celery_app.task
def ona_fetch_reported_cases(form_pk=None):
    form_pk = form_pk or settings.ONAPIE_FORM_PK
    client = Client('https://ona.io', api_token=settings.ONAPIE_ACCESS_TOKEN,
                    api_entrypoint='/api/v1/')
    form_data_list = client.data.get(form_pk)
    uuids = []
    for data in form_data_list:
        if ReportedCase.objects.filter(_uuid=data['_uuid']).exists():
            continue

        case = ReportedCase.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            locality=data['locality'],
            date_of_birth=data['date_of_birth'],
            create_date_time=data['create_date_time'],
            sa_id_number=data.get('sa_id_number'),
            msisdn=data['msisdn'],
            id_type=data['id_type'],
            abroad=data['abroad'],
            reported_by=data['reported_by'],
            gender=data['gender'],
            facility_code=data['facility_code'],
            landmark=data.get('landmark'),
            _id=data['_id'],
            _uuid=data['_uuid'],
            _xform_id_string=data['_xform_id_string'])
        uuids.append(case._uuid)
    return uuids


@celery_app.task
def send_sms(to, content, sender_class=HttpApiSender):
    sender = sender_class(settings.VUMI_GO_ACCOUNT_KEY,
                          settings.VUMI_GO_CONVERSATION_KEY,
                          settings.VUMI_GO_API_TOKEN)
    sms = sender.send_text(to, content)
    SMS.objects.create(to=to, content=content, message_id=sms['message_id'])
