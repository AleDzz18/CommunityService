# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from App_Home.models import CustomUser, MovimientoFinanciero, Tower
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from App_LiderTorre.views import BaseMovimientoCreateView 
from .forms import ( FormularioAdminUsuario,
    IngresoCondominioGeneralForm, EgresoCondominioGeneralForm, 
    IngresoBasuraGeneralForm, EgresoBasuraGeneralForm
)
from datetime import date

# Create your views here.

# ******************************************************************
# MIXIN DE AUTORIZACIÓN: Restringe el acceso solo a Líderes Generales
# ******************************************************************
class LiderGeneralRequiredMixin(AccessMixin):
    """Verifica que el usuario actual tenga el rol de Lider General."""
    def dispatch(self, request, *args, **kwargs):
        # Aseguramos que el usuario esté autenticado
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Usamos la constante del modelo para la comparación
        if request.user.rol != CustomUser.ROL_LIDER_GENERAL:
            messages.error(request, "No tienes permiso para acceder a esta sección administrativa.")
            # Redirigir al dashboard si no tiene el rol
            return redirect('homeDashboard') 
            
        return super().dispatch(request, *args, **kwargs)

# ******************************************************************
# 1. LISTADO DE USUARIOS (READ)
# ******************************************************************
class ListaUsuariosView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CustomUser
    template_name = 'lider_general/lista_usuarios.html' 
    context_object_name = 'usuarios'
    ordering = ['username'] 

# ******************************************************************
# 2. CREACIÓN DE USUARIOS (CREATE)
# Nota: La creación de usuarios por aquí requiere asignar una contraseña.
# Si prefieres que se registren por App_Home, puedes omitir esta vista.
# Aquí se usa un modelo simple sin manejo de contraseña.
# ******************************************************************
class CrearUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, CreateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        # Recomendación: Si quieres crear el usuario con contraseña, 
        # debes usar un formulario de creación de usuario adecuado (ej: UserCreationForm)
        # o establecer una contraseña temporal hasheada aquí.
        messages.success(self.request, f"Usuario '{form.instance.username}' creado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 3. EDICIÓN DE USUARIOS (UPDATE)
# ******************************************************************
class EditarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, UpdateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' editado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 4. ELIMINACIÓN DE USUARIOS (DELETE)
# ******************************************************************
class EliminarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'lider_general/usuario_confirm_delete.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    context_object_name = 'usuario'

    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{self.object.username}' eliminado con éxito.")
        return super().form_valid(form)
    
# --- Mixin de Permisos ---

class LiderGeneralOrAdminBasuraRequiredMixin(UserPassesTestMixin):
    """Permite el acceso solo a Líder General o a un Lider con rol de Admin Basura."""
    def test_func(self):
        user = self.request.user
        return user.rol == CustomUser.ROL_LIDER_GENERAL or user.es_admin_basura

class LiderGeneralRequiredMixin(UserPassesTestMixin):
    """Permite el acceso solo a Líder General."""
    def test_func(self):
        user = self.request.user
        return user.rol == CustomUser.ROL_LIDER_GENERAL

# --- Vistas de Movimientos Financieros (Líder General) ---

# Condominio (Requiere ser LDG)
class RegistrarIngresoCondominioGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = IngresoCondominioGeneralForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

class RegistrarEgresoCondominioGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = EgresoCondominioGeneralForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

# Cuarto de Basura (Ingreso: Requiere ser LDG)
class RegistrarIngresoBasuraGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = IngresoBasuraGeneralForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'

# Cuarto de Basura (Egreso: Requiere ser LDG O Admin Basura)
# Esta vista permite realizar egresos de basura en cualquier torre (se selecciona en el form)
class RegistrarEgresoBasuraGeneralView(LiderGeneralOrAdminBasuraRequiredMixin, BaseMovimientoCreateView):
    form_class = EgresoBasuraGeneralForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'
    
class EstadoSolvenciaBasuraView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, TemplateView):
    template_name = 'lider_general/estado_solvencia_basura.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obtener mes y año de los parámetros GET o usar los actuales
        hoy = date.today()
        try:
            mes = int(self.request.GET.get('mes', hoy.month))
            anio = int(self.request.GET.get('anio', hoy.year))
        except ValueError:
            mes = hoy.month
            anio = hoy.year

        # 2. Obtener todas las torres ordenadas
        torres = Tower.objects.all().order_by('nombre')
        
        # 3. Buscar pagos registrados (Ingresos de Basura) en ese mes/año
        # Nota: values_list nos da una lista simple de IDs de torres que pagaron
        pagos_registrados = MovimientoFinanciero.objects.filter(
            categoria='BAS',
            tipo='ING',
            fecha__year=anio,
            fecha__month=mes,
            tower__isnull=False # Asegurar que esté asociado a una torre
        ).values_list('tower_id', flat=True).distinct()

        # 4. Construir la estructura de datos para el reporte
        reporte_solvencia = []
        for torre in torres:
            es_solvente = torre.id in pagos_registrados
            reporte_solvencia.append({
                'torre': torre,
                'status': 'SOLVENTE' if es_solvente else 'PENDIENTE',
                'css_class': 'bg-success text-white' if es_solvente else 'bg-warning text-dark'
            })

        context.update({
            'reporte': reporte_solvencia,
            'mes_actual': mes,
            'anio_actual': anio,
            'meses_choices': range(1, 13),
            'anios_choices': range(hoy.year - 2, hoy.year + 3),
        })
        return context