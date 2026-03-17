from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def home_view(request: HttpRequest) -> HttpResponse:
    context = {
        "debug": settings.DEBUG,
        "allowed_hosts": ", ".join(settings.ALLOWED_HOSTS),
        "database_host": settings.DATABASES["default"]["HOST"],
    }
    return render(request, "app/home.html", context)


def healthcheck_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
