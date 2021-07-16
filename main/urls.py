from django.urls import path

from .views import index, electric, electricity_config, electricity_per_3_min

app_name = 'main'
urlpatterns = [
    path('', index, name='index'),
    path('electricity/', electric),
    path('electricity/per_3_min/', electricity_per_3_min),
    path('electricity/config/', electricity_config),
]
