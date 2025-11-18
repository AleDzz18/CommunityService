# App_LiderTorre/urls.py

from django.urls import path
from . import views

# Define un 'namespace' para evitar conflictos de nombres de rutas
app_name = 'lider_torre'

urlpatterns = [
    # Condominio
    path('condominio/ingresar/', views.RegistrarIngresoCondominioView.as_view(), name='ingresar_condominio'),
    path('condominio/egresar/', views.RegistrarEgresoCondominioView.as_view(), name='egresar_condominio'),
    
    # Cuarto de Basura
    path('basura/ingresar/', views.RegistrarIngresoBasuraView.as_view(), name='ingresar_basura'),
]