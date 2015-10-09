from django.conf.urls import patterns, url

from views import facilities


urlpatterns = patterns(
    '',
    url(r'^api/v1/facility/(?P<facility_code>.+)\.json$', facilities,
        name='facility'),
)
