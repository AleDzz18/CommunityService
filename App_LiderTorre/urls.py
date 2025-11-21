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

    path('censo/', views.CensoTorreListView.as_view(), name='censo_lista'),
    path('censo/nuevo/', views.CensoTorreCreateView.as_view(), name='censo_crear'),
    path('censo/editar/<int:pk>/', views.CensoTorreUpdateView.as_view(), name='censo_editar'),
    path('censo/eliminar/<int:pk>/', views.CensoTorreDeleteView.as_view(), name='censo_eliminar'),
]