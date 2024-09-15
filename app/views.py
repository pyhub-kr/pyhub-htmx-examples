from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView

from app.forms import DemoForm


def weather(request):
    timezone.activate("Asia/Seoul")
    now = timezone.now()
    return render(request, "cotton/app/_weather.html", {
        "now": now,
    })


class DemoFormView(FormView):
    form_class = DemoForm
    template_name = "app/demo_form.html"
    success_url = reverse_lazy("app:demo-form")
