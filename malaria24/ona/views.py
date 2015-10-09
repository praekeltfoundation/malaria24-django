from .models import Facility
from django.http import JsonResponse, Http404, HttpResponseBadRequest


def facilities(request, facility_code):
    try:
        facility = Facility.objects.get(facility_code=facility_code)
        return JsonResponse(facility.to_dict(), safe=False)
    except Facility.DoesNotExist:
        raise Http404()


def district(request):
    district_name = request.GET.get('district')
    if not district_name:
        return HttpResponseBadRequest()

    facilities = Facility.objects.filter(district=district_name)
    return JsonResponse([f.to_dict() for f in facilities], safe=False)
