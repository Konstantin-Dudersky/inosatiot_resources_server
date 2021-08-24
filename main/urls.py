from django.urls import path

from .views import index, electricity_config, electricity_energy, electricity_power

app_name = 'main'
urlpatterns = [
    path('', index, name='index'),
    path('electricity/', electricity_energy),
    path('electricity/energy/', electricity_energy),
    path('electricity/power/', electricity_power),
    path('electricity/config/', electricity_config),
]
