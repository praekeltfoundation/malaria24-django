from django.contrib import admin

from .models import ReportedCase, EHP, SMS


admin.site.register(ReportedCase)
admin.site.register(EHP)
admin.site.register(SMS)
