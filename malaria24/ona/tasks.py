import json
import requests
import os

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from rest_framework.authtoken.models import Token
from urlparse import urlunparse

from malaria24 import celery_app
from malaria24.ona.models import (ReportedCase, SMS, Digest, Facility, OnaForm,
                                  Email, NationalDigest, ProvincialDigest,
                                  DistrictDigest)

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
            first_name=data.get('first_name') or "",
            last_name=data.get('last_name') or "",
            locality=data.get('locality') or '_other',
            date_of_birth=data.get('date_of_birth'),
            create_date_time=data.get('create_date_time'),
            sa_id_number=data.get('sa_id_number'),
            msisdn=data.get('msisdn'),
            id_type=data.get('id_type'),
            abroad=data.get('abroad'),
            reported_by=data.get('reported_by'),
            gender=data.get('gender'),
            facility_code=data.get('facility_code'),
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
    channel = getattr(settings, 'SMS_CHANNEL', None)
    # Send with VumiGo
    if (channel is None or channel == 'VUMI_GO'):
        sender = HttpApiSender(
            settings.VUMI_GO_ACCOUNT_KEY,
            settings.VUMI_GO_CONVERSATION_KEY,
            settings.VUMI_GO_API_TOKEN,
            api_url='http://go.vumi.org/api/v1/go/http_api_nostream')
        sms = sender.send_text(to, content)
    # Send with Junebug
    elif channel == 'JUNEBUG':
        long_code = (getattr(settings, 'SMS_CODE'))
        jb_url = getattr(settings, 'JUNEBUG_CHANNEL_URL')
        jb_auth = (getattr(settings, 'JUNEBUG_USERNAME', None),
                   getattr(settings, 'JUNEBUG_PASSWORD', None))

        headers = {'content-type': 'application/json'}
        # Get the url and token for endpoint to send events to
        site = get_current_site(None)
        event_url = urlunparse(
            ('http', site.domain, '/api/v1/event/', '', '', ''))
        event_token = Token.objects.get(user__username='junebug')
        data = {'to': to, 'content': content, 'event_url': event_url,
                'event_auth_token': event_token.key, 'from': long_code}

        data = json.dumps(data)
        r = requests.post(
            '%s/messages/' % jb_url, auth=jb_auth,
            data=data, headers=headers)
        r.raise_for_status()
        sms = json.loads(r.content)['result']
    SMS.objects.create(to=to, content=content, message_id=sms['message_id'])


@celery_app.task(ignore_result=True)
def send_case_email(case_pk, recipients):
    from django.core.mail import EmailMultiAlternatives

    case = ReportedCase.objects.get(pk=case_pk)
    subject = 'Malaria case number %s' % (case.case_number,)
    text_content = case.get_text_email_content()
    html_content = case.get_html_email_content()
    pdf_content = case.get_pdf_email_content()
    from_email = settings.DEFAULT_FROM_EMAIL
    msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
    msg.attach_alternative(html_content, "text/html")
    msg.attach('Reported_Case_%s.pdf' % (case.case_number,),
               make_pdf(pdf_content),
               "application/pdf")
    msg.send()
    Email.objects.create(to=recipients[0], html_content=html_content,
                         pdf_content=pdf_content)


def make_pdf(html_content):  # pragma: no cover
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
    NationalDigest.compile_digest().send_digest_email()
    ProvincialDigest.compile_digest().send_digest_email()
    DistrictDigest.compile_digest().send_digest_email()
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
