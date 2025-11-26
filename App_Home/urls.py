from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_dashboard, name='url_dashboard'),
    path('login/', views.vista_login, name='url_login'),
    path('logout/', views.vista_logout, name='url_logout'),
    path('register/', views.vista_registro, name='url_registro'),
    path('register/perfil/<int:user_id>/', views.vista_completar_perfil, name='url_completar_perfil'),
    
    # --- ADMINISTRACIÓN DE INGRESOS Y EGRESOS ---
    path('finanzas/<str:categoria_slug>/', views.ver_ingresos_egresos, name='ver_finanzas'),
    
    # URL para descargar el archivo PDF (ejemplo: /finanzas/condominio/descargar/)
    path('finanzas/<str:categoria_slug>/descargar/', views.descargar_pdf, name='descargar_pdf'),

    # --- VISTAS DE BENEFICIOS (PÚBLICO + GESTIÓN VISUAL) ---
    path('beneficios/<str:tipo_slug>/', views.vista_beneficio, name='ver_beneficio'),
    path('beneficios/pdf/<int:ciclo_id>/', views.descargar_pdf_beneficio, name='pdf_beneficio'),

    # --- VISTAS DE DOCUMENTOS ---
    path('solicitudes/nueva/', views.vista_solicitar_documento, name='solicitar_documento'),
]