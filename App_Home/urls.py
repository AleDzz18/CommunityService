from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_dashboard, name='url_dashboard'),
    path('login/', views.vista_login, name='url_login'),
    path('logout/', views.vista_logout, name='url_logout'),
    path('register/', views.vista_registro, name='url_registro'),
    path('register/perfil/<int:user_id>/', views.vista_completar_perfil, name='url_completar_perfil'),
]