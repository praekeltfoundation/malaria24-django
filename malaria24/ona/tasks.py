from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail

from malaria24 import celery_app
from malaria24.ona.models import ReportedCase, SMS, Actor

from onapie.client import Client

from go_http.send import HttpApiSender


@celery_app.task(ignore_result=True)
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


@celery_app.task(ignore_result=True)
def send_sms(to, content):
    sender = HttpApiSender(
        settings.VUMI_GO_ACCOUNT_KEY,
        settings.VUMI_GO_CONVERSATION_KEY,
        settings.VUMI_GO_API_TOKEN,
        api_url='http://go.vumi.org/api/v1/go/http_api_nostream')
    sms = sender.send_text(to, content)
    SMS.objects.create(to=to, content=content, message_id=sms['message_id'])


@celery_app.task(ignore_result=True)
def send_case_email(case_number):
    case = ReportedCase.objects.get(pk=case_number)
    ehps = Actor.objects.ehps().filter(facility_code=case.facility_code)
    for ehp in ehps:
        context = {
            'case': case,
            'ehp': ehp,
        }
        text_content = render_to_string('ona/text_email.txt', context)
        html_content = render_to_string('ona/html_email.html', context)
        send_mail(subject='Malaria case number %s' % (case_number,),
                  message=text_content,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[ehp.email_address],
                  html_message=html_content)
