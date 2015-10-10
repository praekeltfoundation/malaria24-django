from django.conf.urls import patterns, url

from views import facilities, localities


urlpatterns = patterns(
    '',
    url(r'^api/v1/facility/(?P<facility_code>.+)\.json$', facilities,
        name='facility'),
    url(r'^api/v1/localities/(?P<facility_code>.+)\.json$', localities,
        name='localities'),
)
