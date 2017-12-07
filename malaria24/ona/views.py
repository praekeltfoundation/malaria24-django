from django.http import JsonResponse, Http404
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from .models import Facility, InboundSMS, SMSEvent
from .serializers import InboundSMSSerializer, SMSEventSerializer


def facilities(request, facility_code):
    try:
        facility = Facility.objects.get(facility_code=facility_code)
        return JsonResponse(facility.to_dict(), safe=False)
    except Facility.DoesNotExist:
        raise Http404()


def localities(request, facility_code):
    try:
        facility = Facility.objects.get(facility_code=facility_code)
        facilities = Facility.objects.filter(district=facility.district)
        localities = facilities.values_list(
            'subdistrict', flat=True).distinct()
        return JsonResponse(list(localities), safe=False)
    except Facility.DoesNotExist:
        raise Http404()


class InboundSMSViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = InboundSMSSerializer
    queryset = InboundSMS.objects.all()

    def create(self, request, *args, **kwargs):
        # Rename the 'from' field because we can't use that as a variable name
        request.data['sender'] = request.data['from']

        # Coerce null values to an empty string
        if 'content' in request.data and request.data['content'] is None:
            request.data['content'] = ""

        return super(InboundSMSViewSet, self).create(request, *args, **kwargs)


class SMSEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = SMSEventSerializer
    queryset = SMSEvent.objects.all()
