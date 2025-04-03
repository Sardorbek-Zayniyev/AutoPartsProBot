from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CarModel

@csrf_exempt
def get_car_models(request):
    brand_id = request.GET.get("brand_id")
    if not brand_id:
        return JsonResponse({"models": []})

    models = CarModel.objects.filter(brand_id=brand_id).order_by("name")
    models_data = [{"id": model.id, "name": model.name} for model in models]
    
    return JsonResponse({"models": models_data})