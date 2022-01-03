from django.conf.urls import url, include
from rest_framework import routers
from malaria24.ona.views import InboundSMSViewSet, SMSEventViewSet, facilities, localities


router = routers.DefaultRouter()
router.register(r'inbound', InboundSMSViewSet)
router.register(r'event', SMSEventViewSet)

urlpatterns = [
    url(r'^facility/(?P<facility_code>.+)\.json$', facilities,
        name='facility'),
    url(r'^localities/(?P<facility_code>.+)\.json$', localities,
        name='localities'),
    url(r'', include(router.urls)),
]
