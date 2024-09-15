from django.urls import path
from . import views

app_name = "app"

urlpatterns = [
    path("weather/", views.weather, name="weather"),
]

