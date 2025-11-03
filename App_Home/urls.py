from django.urls import path
from . import views

urlpatterns = [
    path('', views.homeDashboard, name='homeDashboard'),
    path('login/', views.login, name='login'),
]