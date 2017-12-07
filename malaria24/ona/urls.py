from django.conf.urls import patterns, url, include
from rest_framework import routers

from views import facilities, localities, InboundSMSViewSet


router = routers.DefaultRouter()
router.register(r'inbound', InboundSMSViewSet)

urlpatterns = patterns(
    '',
    url(r'^facility/(?P<facility_code>.+)\.json$', facilities,
        name='facility'),
    url(r'^localities/(?P<facility_code>.+)\.json$', localities,
        name='localities'),
    url(r'', include(router.urls)),
)
