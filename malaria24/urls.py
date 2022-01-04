import os
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from rest_framework import routers
from malaria24.ona.views import InboundSMSViewSet, SMSEventViewSet


router = routers.DefaultRouter()
router.register(r'inbound', InboundSMSViewSet)
router.register(r'event', SMSEventViewSet)

urlpatterns = [
    url(r'', include(router.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v1/', include('malaria24.ona.urls', namespace='api_v1')),
]


if settings.DEBUG:  # pragma: no cover
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(
        settings.MEDIA_URL + 'images/',
        document_root=os.path.join(settings.MEDIA_ROOT, 'images'))
