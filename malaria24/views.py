from django.http import JsonResponse


def health(request):
    status = 200
    resp = {
        "up": True,
    }
    return JsonResponse(resp, status=status)
