from django import forms
from django.contrib import admin, messages
from django.conf.urls import url
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from .models import ReportedCase, Actor, SMS, Email, Digest, Facility, OnaForm
from .tasks import import_facilities, ona_fetch_reported_case_for_form


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
    list_filter = ('facility_code', 'gender', 'create_date_time', 'form')
    search_fields = ('case_number', 'first_name', 'last_name', 'sa_id_number')

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
    list_display = ('to', 'content', 'created_at', 'message_id')
    list_filter = ('created_at',)
    search_fields = ('to', 'content')


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
    district = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(ActorAdminForm, self).__init__(*args, **kwargs)
        self.fields['district'].choices = [('---------', '---------')] + [(
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
    upload = forms.FileField(label='File to import', required=True)
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
                import_facilities.delay(
                    form.cleaned_data['upload'].read(),
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
admin.site.register(Email, EmailAdmin)
admin.site.register(Digest, DigestAdmin)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(OnaForm, OnaFormAdmin)
