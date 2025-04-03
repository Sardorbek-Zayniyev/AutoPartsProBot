from django.urls import path
from .views import get_car_models

urlpatterns = [
    path("admin/get-car-models/", get_car_models, name="get_car_models"),
]
