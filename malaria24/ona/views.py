from .models import Facility
from django.http import JsonResponse, Http404


def facilities(request, facility_code):
    try:
        facility = Facility.objects.get(facility_code=facility_code)
        return JsonResponse(facility.to_dict(), safe=False)
    except Facility.DoesNotExist:
        raise Http404()
