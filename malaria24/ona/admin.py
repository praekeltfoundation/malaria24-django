
from datetime import timedelta
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from django.utils import timezone

from .models import ReportedCase, Actor, SMS, Digest


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
            (0, _('Last week')),
            (-1, _('2 weeks ago')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() is None:
            return queryset

        return queryset.last_week(
            timezone.now() - timedelta(weeks=int(self.value())))


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
    list_filter = ('facility_code', 'gender', 'create_date_time',
                   DateReportedListFilter)


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


admin.site.register(ReportedCase, ReportedCaseAdmin)
admin.site.register(Actor, ActorAdmin)
admin.site.register(SMS, SMSAdmin)
admin.site.register(Digest, DigestAdmin)
