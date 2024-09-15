from django.urls import path
from . import views

app_name = "app"

urlpatterns = [
    path("weather/", views.weather, name="weather"),
    path("demo/form/", views.DemoFormView.as_view(), name="demo-form"),
]

