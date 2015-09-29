from django.contrib import admin

from .models import ReportedCase, EHP, SMS


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
                    'created_at')
    list_filter = ('facility_code', 'gender', 'created_at')


class SMSAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('to', 'content', 'created_at')
    list_filter = ('created_at',)


admin.site.register(ReportedCase, ReportedCaseAdmin)
admin.site.register(EHP)
admin.site.register(SMS, SMSAdmin)
