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


admin.site.register(ReportedCase, ReportedCaseAdmin)
admin.site.register(EHP)
admin.site.register(SMS)
