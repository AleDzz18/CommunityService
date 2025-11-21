# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from App_Home.models import CustomUser, MovimientoFinanciero, Tower, CensoMiembro
from django.shortcuts import redirect
from django.contrib import messages
from App_LiderTorre.views import BaseMovimientoCreateView 
from .forms import ( FormularioAdminUsuario,
    IngresoCondominioGeneralForm, EgresoCondominioGeneralForm, 
    IngresoBasuraGeneralForm, EgresoBasuraGeneralForm
)
from datetime import date
from App_Home.forms import CensoMiembroForm

# --- MIXINS DE PERMISOS (Definirlos al principio) ---

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
            return redirect('url_dashboard') 
            
        return super().dispatch(request, *args, **kwargs)

class LiderGeneralOrAdminBasuraRequiredMixin(UserPassesTestMixin):
    """Permite el acceso solo a Líder General o a un Lider con rol de Admin Basura."""
    def test_func(self):
        user = self.request.user
        # Verificamos si está autenticado primero para evitar errores
        if not user.is_authenticated:
            return False
        return user.rol == CustomUser.ROL_LIDER_GENERAL or user.es_admin_basura

# ******************************************************************
# 1. GESTIÓN DE USUARIOS
# ******************************************************************

class ListaUsuariosView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CustomUser
    template_name = 'lider_general/lista_usuarios.html' 
    context_object_name = 'usuarios'
    ordering = ['username'] 

class CrearUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, CreateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' creado con éxito.")
        return super().form_valid(form)

class EditarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, UpdateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' editado con éxito.")
        return super().form_valid(form)

class EliminarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'lider_general/usuario_confirm_delete.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    context_object_name = 'usuario'

    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{self.object.username}' eliminado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 2. GESTIÓN FINANCIERA (CONDOMINIO Y BASURA)
# ******************************************************************

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
class RegistrarEgresoBasuraGeneralView(LiderGeneralOrAdminBasuraRequiredMixin, BaseMovimientoCreateView):
    form_class = EgresoBasuraGeneralForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'
    
class EstadoSolvenciaBasuraView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, TemplateView):
    template_name = 'lider_general/estado_solvencia_basura.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        hoy = date.today()
        try:
            mes = int(self.request.GET.get('mes', hoy.month))
            anio = int(self.request.GET.get('anio', hoy.year))
        except ValueError:
            mes = hoy.month
            anio = hoy.year

        torres = Tower.objects.all().order_by('nombre')
        
        pagos_registrados = MovimientoFinanciero.objects.filter(
            categoria='BAS',
            tipo='ING',
            fecha__year=anio,
            fecha__month=mes,
            tower__isnull=False
        ).values_list('tower_id', flat=True).distinct()

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
    
# ******************************************************************
# 3. GESTIÓN DE CENSO GLOBAL
# ******************************************************************

class CensoGeneralListView(LiderGeneralRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_general/censo_list_general.html'
    context_object_name = 'miembros'
    ordering = ['tower', 'piso', 'apartamento_letra']

    def get_queryset(self):
        qs = super().get_queryset().select_related('tower')
        # Filtro por Torre desde el GET
        torre_id = self.request.GET.get('torre')
        if torre_id and torre_id.isdigit():
            qs = qs.filter(tower_id=int(torre_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['torres'] = Tower.objects.all() # Para el dropdown del filtro
        context['torre_seleccionada'] = self.request.GET.get('torre')
        return context

class CensoGeneralCreateView(LiderGeneralRequiredMixin, CreateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_general/censo_form_general.html'
    success_url = reverse_lazy('lider_general:censo_lista') 

class CensoGeneralUpdateView(LiderGeneralRequiredMixin, UpdateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_general/censo_form_general.html'
    success_url = reverse_lazy('lider_general:censo_lista')

class CensoGeneralDeleteView(LiderGeneralRequiredMixin, DeleteView):
    model = CensoMiembro
    template_name = 'lider_general/censo_confirm_delete.html'
    success_url = reverse_lazy('lider_general:censo_lista')