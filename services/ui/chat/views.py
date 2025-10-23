from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    context = {"API_URL": settings.API_URL}
    return render(request, "chat/index.html", context)
