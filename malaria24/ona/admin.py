
from datetime import timedelta
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from django.utils import timezone

from .models import ReportedCase, Actor, SMS

import logging

class DateReportedListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('week logged')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'datereported'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            (7, _('Last week')),
            (14, _('2 weeks ago')),
        )

    def queryset(self, request, queryset):
        now = timezone.now().date()


        some_day_last_week = now - timedelta(days=int(self.value()))
        monday_of_last_week = some_day_last_week - timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
        monday_of_this_week = monday_of_last_week + timedelta(days=int(self.value()))

        logger = logging.getLogger(__name__)


        logger.error('Start date: %s' % monday_of_last_week)

        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """


        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        return queryset.filter(create_date_time__gte=monday_of_last_week,
                                create_date_time__lte=monday_of_this_week)



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
                    'create_date_time')
    list_filter = ('facility_code', 'gender', 'create_date_time', DateReportedListFilter)


class SMSAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('to', 'content', 'created_at')
    list_filter = ('created_at',)


class ActorAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('name',
                    'email_address',
                    'phone_number',
                    'get_role_display')
    list_filter = ('role', 'created_at')


admin.site.register(ReportedCase, ReportedCaseAdmin)
admin.site.register(Actor, ActorAdmin)
admin.site.register(SMS, SMSAdmin)
