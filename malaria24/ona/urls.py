from django.urls import re_path, include
from rest_framework import routers
from malaria24.ona.views import InboundSMSViewSet, SMSEventViewSet
from malaria24.ona.views import facilities, localities


router = routers.DefaultRouter()
router.register(r'inbound', InboundSMSViewSet)
router.register(r'event', SMSEventViewSet)

urlpatterns = [
    re_path(r'^facility/(?P<facility_code>.+)\.json$', facilities,
            name='facility'),
    re_path(r'^localities/(?P<facility_code>.+)\.json$', localities,
            name='localities'),
    re_path(r'', include(router.urls)),

]
