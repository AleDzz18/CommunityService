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

    # Condominio
    path('condominio/ingresar/', views.RegistrarIngresoCondominioGeneralView.as_view(), name='ingresar_condominio_general'),
    path('condominio/egresar/', views.RegistrarEgresoCondominioGeneralView.as_view(), name='egresar_condominio_general'),
    
    # Cuarto de Basura
    path('basura/ingresar/', views.RegistrarIngresoBasuraGeneralView.as_view(), name='ingresar_basura_general'),
    path('basura/egresar/', views.RegistrarEgresoBasuraGeneralView.as_view(), name='egresar_basura_general'),
    path('basura/estado-solvencia/', views.EstadoSolvenciaBasuraView.as_view(), name='estado_solvencia_basura'),

    # Censo de Miembros
    path('censo/', views.CensoGeneralListView.as_view(), name='censo_lista'),
    path('censo/nuevo/', views.CensoGeneralCreateView.as_view(), name='censo_crear'),
    path('censo/editar/<int:pk>/', views.CensoGeneralUpdateView.as_view(), name='censo_editar'),
    path('censo/eliminar/<int:pk>/', views.CensoGeneralDeleteView.as_view(), name='censo_eliminar'),
    # NUEVA RUTA Censo PDF General
    path('censo/descargar/pdf/', views.CensoPDFGeneralView.as_view(), name='censo_pdf_general'),

    # Gestión de Ciclos y Beneficios
    path('ciclos/crear/', views.CrearCicloView.as_view(), name='crear_ciclo'),
    path('ciclos/eliminar/<int:pk>/', views.EliminarCicloView.as_view(), name='eliminar_ciclo'),
    path('beneficios/agregar-global/<str:tipo_slug>/', views.AgregarBeneficiarioGeneralView.as_view(), name='agregar_beneficiario_global'),

    # GESTIÓN DE SOLICITUDES DE DOCUMENTOS
    path('solicitudes/', views.ListaSolicitudesView.as_view(), name='lista_solicitudes'),
    path('solicitudes/procesar/<int:pk>/', views.ProcesarSolicitudView.as_view(), name='procesar_solicitud'),
]