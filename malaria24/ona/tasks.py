import json
import os

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail

from malaria24 import celery_app
from malaria24.ona.models import ReportedCase, SMS, Digest, Facility, OnaForm

from onapie.client import Client

from go_http.send import HttpApiSender


@celery_app.task(ignore_result=True)
def ona_fetch_forms():
    client = Client('https://ona.io', api_token=settings.ONAPIE_ACCESS_TOKEN,
                    api_entrypoint='/api/v1/')
    for ona_form in client.forms.list():
        form, _ = OnaForm.objects.get_or_create(uuid=ona_form['uuid'])
        form.title = ona_form['title']
        form.id_string = ona_form['id_string']
        form.form_id = ona_form['formid']
        form.save()


@celery_app.task(ignore_result=True)
def ona_fetch_reported_cases():
    return dict(
        [(form.form_id, ona_fetch_reported_case_for_form(form.form_id))
         for form in OnaForm.objects.filter(active=True)])


@celery_app.task(ignore_result=True)
def ona_fetch_reported_case_for_form(form_id):
    client = Client('https://ona.io', api_token=settings.ONAPIE_ACCESS_TOKEN,
                    api_entrypoint='/api/v1/')
    form_data_list = client.data.get(form_id)
    uuids = []
    for data in form_data_list:
        if ReportedCase.objects.filter(_uuid=data['_uuid']).exists():
            continue

        case = ReportedCase.objects.create(
            form=OnaForm.objects.get(form_id=form_id),
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
            landmark_description=data.get('landmark_description'),
            case_number=data.get('case_number'),
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
def send_case_email(case_pk):
    from django.core.mail import EmailMultiAlternatives

    case = ReportedCase.objects.get(pk=case_pk)
    subject = 'Malaria case number %s' % (case.case_number,)
    text_content = case.get_text_email_content()
    html_content = case.get_html_email_content()
    from_email = settings.DEFAULT_FROM_EMAIL
    recipients = [ehp.email_address for ehp in case.get_ehps()]
    msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
    msg.attach_alternative(html_content, "text/html")
    msg.attach_alternative(make_pdf(html_content), "application/pdf")
    msg.send()


def make_pdf(html_content):
    print 'making PDF!!'
    import pdfkit
    import tempfile
    fd, output_file = tempfile.mkstemp()
    pdfkit.from_string(html_content, output_file)
    with open(output_file, 'rb') as fp:
        value = fp.read()
    os.close(fd)
    os.unlink(output_file)
    return value


@celery_app.task(ignore_result=True)
def compile_and_send_digest_email():
    cases = ReportedCase.objects.filter(digest__isnull=True)
    if not cases.exists():
        return

    digest = Digest.compile_digest()
    if digest:
        return digest.send_digest_email()


@celery_app.task(ignore_result=True)
def import_facilities(json_data, wipe, email_address):
    data = json.loads(json_data)
    if wipe:
        Facility.objects.all().delete()

    for row in data:
        facility, _ = Facility.objects.get_or_create(
            facility_code=row['FacCode'])
        facility.facility_name = row['Facility']
        facility.province = row['Province']
        facility.district = row['District']
        facility.subdistrict = row['Sub-District (Locality)']
        facility.phase = row['Phase']
        facility.save()

    if email_address:
        context = {
            'facilities': Facility.objects.all(),
            'data': data,
        }
        text_content = render_to_string(
            'ona/import_complete_email.txt', context)
        html_content = render_to_string(
            'ona/import_complete_email.html', context)

        send_mail(subject='Facilities import complete.',
                  message=text_content,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[email_address],
                  html_message=html_content)
