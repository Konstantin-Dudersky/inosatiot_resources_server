from django.urls import path

from .views import index, electricity_config, electricity_energy, electricity_power, electricity_quality, info

app_name = 'main'
urlpatterns = [
    path('', index, name='index'),
    path('electricity/', electricity_energy),
    path('electricity/energy/', electricity_energy),
    path('electricity/power/', electricity_power),
    path('electricity/quality/', electricity_quality),
    path('electricity/config/', electricity_config),
    path('info/', info),
]
