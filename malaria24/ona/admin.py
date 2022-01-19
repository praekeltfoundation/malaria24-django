import csv
import io
import json
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.conf.urls import url
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from .models import (ReportedCase, Actor, SMS, InboundSMS, Email, Digest,
                     Facility, OnaForm)
from .tasks import (import_facilities, ona_fetch_reported_case_for_form,
                    compile_and_send_jembi)


class ReportedCaseAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('first_name',
                    'last_name',
                    'locality',
                    'sa_id_number',
                    'msisdn',
                    'id_type',
                    'gender',
                    'facility_code',
                    'landmark',
                    'create_date_time',
                    'form',
                    'ehp_report_link')
    list_filter = ('facility_code', 'gender', 'create_date_time', 'form',
                   'jembi_alert_sent')
    search_fields = ('case_number', 'first_name', 'last_name', 'sa_id_number')

    actions = ['send_jembi_alert']

    def send_jembi_alert(self, request, queryset):
        if not settings.FORWARD_TO_JEMBI:
            self.message_user(request, 'Sending to Jembi currently disabled.',
                              level=messages.WARNING)
            return
        unsent_cases = queryset.filter(jembi_alert_sent=False)
        for case in unsent_cases:
            compile_and_send_jembi.delay(case.pk)
        self.message_user(
            request, 'Forwarding all unsent cases to Jembi (total %s). '
            'This may take a few minutes.' % (
                unsent_cases.count(),))
    send_jembi_alert.short_description = 'Send selected unsent cases to Jembi.'

    def get_urls(self):
        urls = super(ReportedCaseAdmin, self).get_urls()
        my_urls = [
            url(r'^ehp_report/(?P<pk>\d+)/$', self.admin_site.admin_view(
                self.ehp_report_view), name='ehp_report_view'),
        ]
        return my_urls + urls

    def ehp_report_link(self, reported_case):
        return '<a href="./ehp_report/%s/">View EHP Email</a>' % (
            reported_case.pk,)
    ehp_report_link.short_description = 'EHP Email'
    ehp_report_link.allow_tags = True

    def ehp_report_view(self, request, pk):
        reported_case = ReportedCase.objects.get(pk=pk)
        return HttpResponse(reported_case.get_html_email_content())


class SMSAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('to', 'content', 'created_at', 'status', 'message_id')
    list_filter = ('created_at',)
    search_fields = ('to', 'content')

    def status(self, sms):
        event = sms.smsevent_set.latest('timestamp')
        if event is None:
            return
        return event.event_type


class InboundSMSAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('message_id', 'sender', 'content', 'timestamp', 'reply_to')
    list_filter = ('timestamp',)
    search_fields = ('sender', 'content', 'timestamp')


class EmailAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('to', 'created_at', 'email_link')
    list_filter = ('created_at',)
    search_fields = ('to',)

    def get_urls(self):
        urls = super(EmailAdmin, self).get_urls()
        my_urls = [
            url(r'^sent_email/(?P<pk>\d+)/$', self.admin_site.admin_view(
                self.email_view), name='email_view'),
        ]
        return my_urls + urls

    def email_link(self, email):
        return '<a href="./sent_email/%s/">View Email</a>' % (
            email.pk,)
    email_link.short_description = 'Email'
    email_link.allow_tags = True

    def email_view(self, request, pk):
        email = Email.objects.get(pk=pk)
        return HttpResponse(email.html_content)


class ActorAdminForm(forms.ModelForm):
    district = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(ActorAdminForm, self).__init__(*args, **kwargs)
        self.fields['district'].choices = [('', '---------')] + [(
            d, d) for d in Facility.objects.all().values_list(
                'district', flat=True).distinct().order_by("district")]

    class Meta:
        model = Actor
        fields = (
            'name',
            'email_address',
            'phone_number',
            'role',
            'facility_code',
            'province',
            'district')


class ActorAdmin(admin.ModelAdmin):
    form = ActorAdminForm
    date_hierarchy = 'created_at'
    list_display = ('name',
                    'email_address',
                    'phone_number',
                    'role',
                    'facility_code',
                    'province',
                    'district')
    list_filter = ('role', 'created_at')


class ReportedCaseInline(admin.TabularInline):
    model = ReportedCase

    list_display = fields = readonly_fields = (
        'first_name',
        'last_name',
        'locality',
        'date_of_birth',
        'create_date_time',
        'sa_id_number',
        'msisdn',
        'id_type',
        'abroad',
        'reported_by',
        'gender',
        'facility_code',
        'landmark',
        'ehps')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DigestAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('created_at', 'get_recipient_list')
    list_filter = ('created_at',)
    readonly_fields = ('recipients', 'created_at')
    inlines = [
        ReportedCaseInline,
    ]

    def get_recipient_list(self, digest):
        return ', '.join([r.email_address for r in digest.recipients.all()])
    get_recipient_list.short_description = 'Recipients'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FacilityUploadForm(forms.Form):
    upload = forms.FileField(
        label='File to import',
        required=True,
        help_text='Files can either be in csv or json format. '
        'If the file is a csv, the headers must be '
        '"FacCode,Facility,Province,District,Sub-District (Locality),Phase". '
        'If the file is a json, the format must be a list of json objects '
        'with the keys the same as the csv headers')
    wipe = forms.BooleanField(
        help_text=('Check if you want to wipe the existing database before '
                   'importing new data.'), required=False)


class FacilityAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('facility_code',
                    'facility_name',
                    'province',
                    'district',
                    'subdistrict',
                    'created_at',
                    'updated_at',
                    )
    list_filter = ('province', 'district', 'subdistrict', 'phase')
    search_fields = ('facility_code', 'facility_name')

    def get_urls(self):
        urls = super(FacilityAdmin, self).get_urls()
        my_urls = [
            url(r'^upload/$', self.admin_site.admin_view(
                self.upload_facility_codes_view), name='ona_facility_upload'),
        ]
        return my_urls + urls

    def upload_facility_codes_view(self, request):
        if request.method == 'POST':
            form = FacilityUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['upload'].read().decode('utf-8')

                try:
                    file_content_json = json.loads(file)
                except json.JSONDecodeError:
                    string_io_file = io.StringIO(file)
                    next(string_io_file, None)
                    file_content_json = list(csv.DictReader(
                        string_io_file,
                        fieldnames=[
                            "FacCode",
                            "Facility",
                            "Province",
                            "District",
                            "Sub-District (Locality)",
                            "Phase",
                        ],
                        delimiter=',',
                    ))

                import_facilities.delay(
                    file_content_json,
                    form.cleaned_data['wipe'],
                    request.user.email)
                messages.info(
                    request,
                    ('Importing facilities, you will receive an email '
                     'when completed.'))
                return redirect('admin:ona_facility_changelist')
        else:
            form = FacilityUploadForm()
        context = dict(
            self.admin_site.each_context(request),
            title='Upload Facility Codes',
            form=form,
        )
        return TemplateResponse(
            request, 'ona/upload_facility_codes.html', context)


class OnaFormAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('title',
                    'id_string',
                    'form_id',
                    'active',
                    'created_at',
                    )
    actions = ['pull_reported_cases']

    def pull_reported_cases(self, request, queryset):
        forms = queryset.filter(active=True)
        for form in forms:
            ona_fetch_reported_case_for_form.delay(form.form_id)
        self.message_user(
            request, 'Scheduling manual pull for %s active forms.' % (
                forms.count(),))
    pull_reported_cases.short_description = 'Manually pull reported cases.'


admin.site.register(ReportedCase, ReportedCaseAdmin)
admin.site.register(Actor, ActorAdmin)
admin.site.register(SMS, SMSAdmin)
admin.site.register(InboundSMS, InboundSMSAdmin)
admin.site.register(Email, EmailAdmin)
admin.site.register(Digest, DigestAdmin)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(OnaForm, OnaFormAdmin)
