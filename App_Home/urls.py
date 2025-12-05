from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Mantenemos esta importación si otras URLs la usan.

urlpatterns = [
    path("", views.vista_index, name="url_index"),
    path("login/", views.vista_login, name="url_login"),
    path("logout/", views.vista_logout, name="url_logout"),
    path("register/", views.vista_registro, name="url_registro"),
    path(
        "register/perfil/<int:user_id>/",
        views.vista_completar_perfil,
        name="url_completar_perfil",
    path('register/cancelar/<int:user_id>/', views.cancelar_registro, name='url_cancelar_registro'),
    ),
    # --- ADMINISTRACIÓN DE INGRESOS Y EGRESOS ---
    path(
        "finanzas/<str:categoria_slug>/",
        views.ver_ingresos_egresos,
        name="ver_finanzas",
    ),
    # URL para descargar el archivo PDF (ejemplo: /finanzas/condominio/descargar/)
    path(
        "finanzas/<str:categoria_slug>/descargar/",
        views.descargar_pdf,
        name="descargar_pdf",
    ),
    # --- VISTAS DE BENEFICIOS (PÚBLICO + GESTIÓN VISUAL) ---
    path("beneficios/<str:tipo_slug>/", views.vista_beneficio, name="ver_beneficio"),
    path(
        "beneficios/pdf/<int:ciclo_id>/",
        views.descargar_pdf_beneficio,
        name="pdf_beneficio",
    ),
    # --- VISTAS DE DOCUMENTOS ---
    path(
        "solicitudes/nueva/",
        views.vista_solicitar_documento,
        name="solicitar_documento",
    ),
    path('solicitudes/nueva/', views.vista_solicitar_documento, name='solicitar_documento'),

    # --- VISTAS DE RESTABLECIMIENTO DE CONTRASEÑA PERSONALIZADAS ---
    path('password/request-code/', views.RequestResetCodeView.as_view(), name='request_reset_code'),
    path('password/code-sent/', views.reset_code_sent, name='reset_code_sent'),
    path('password/verify-code/', views.VerifyResetCodeView.as_view(), name='verify_reset_code'),
    path('password/set-new/', views.SetNewPasswordView.as_view(), name='set_new_password'),
    path('password/reset/complete/', views.PasswordResetCompleteCustomView.as_view(), name='password_reset_complete_custom'),
]
