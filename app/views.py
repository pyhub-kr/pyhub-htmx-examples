from django.shortcuts import render
from django.utils import timezone


def weather(request):
    timezone.activate("Asia/Seoul")
    now = timezone.now()
    return render(request, "cotton/app/_weather.html", {
        "now": now,
    })
