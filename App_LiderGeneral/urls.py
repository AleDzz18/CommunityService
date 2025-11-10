# App_LiderGeneral/urls.py

from django.urls import path
from . import views

# Define un 'namespace' para evitar conflictos de nombres de rutas
app_name = 'lider_general'

urlpatterns = [
    # 1. LISTADO DE USUARIOS (RUTA PRINCIPAL)
    path('usuarios/', views.ListaUsuariosView.as_view(), name='lista_usuarios'),
    
    # 2. CREACIÓN DE USUARIOS
    path('usuarios/crear/', views.CrearUsuarioView.as_view(), name='crear_usuario'),
    
    # 3. EDICIÓN DE USUARIOS
    path('usuarios/editar/<int:pk>/', views.EditarUsuarioView.as_view(), name='editar_usuario'),
    
    # 4. ELIMINACIÓN DE USUARIOS
    path('usuarios/eliminar/<int:pk>/', views.EliminarUsuarioView.as_view(), name='eliminar_usuario'),
]