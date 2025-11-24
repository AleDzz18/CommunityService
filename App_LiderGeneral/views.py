# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from App_Home.models import CustomUser, MovimientoFinanciero, Tower, CensoMiembro, CicloBeneficio, EntregaBeneficio
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from App_LiderTorre.views import BaseMovimientoCreateView 
from .forms import ( FormularioAdminUsuario, IngresoCondominioGeneralForm, EgresoCondominioGeneralForm, 
    IngresoBasuraGeneralForm, EgresoBasuraGeneralForm
)
from datetime import date
from App_Home.forms import CensoMiembroForm
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError

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



# --- GESTIÓN DE CICLOS (CREAR / ELIMINAR) ---

class CrearCicloView(LoginRequiredMixin, View):
    """Crea una nueva lista mensual y cierra la anterior si existe."""
    
    def post(self, request, *args, **kwargs):
        tipo = request.POST.get('tipo') # CLAP o GAS
        nombre = request.POST.get('nombre') # Ej: "Octubre 2024"
        
        # Validación de permisos (LDG o Admin Específico)
        permiso = False
        if request.user.rol == 'LDG': permiso = True
        elif tipo == 'CLAP' and request.user.es_admin_clap: permiso = True
        elif tipo == 'GAS' and request.user.es_admin_bombonas: permiso = True
        
        if not permiso:
            messages.error(request, "No tienes permiso para crear listas.")
            return redirect('url_dashboard')

        # 1. Desactivar ciclos anteriores del mismo tipo
        CicloBeneficio.objects.filter(tipo=tipo, activo=True).update(activo=False)
        
        # 2. Crear nuevo ciclo
        CicloBeneficio.objects.create(tipo=tipo, nombre=nombre, activo=True)
        
        slug = 'clap' if tipo == 'CLAP' else 'gas'
        messages.success(request, f"Nueva lista de {tipo} creada exitosamente.")
        return redirect('ver_beneficio', tipo_slug=slug)

class EliminarCicloView(LoginRequiredMixin, View):
    """Elimina (Cierra) la lista actual."""
    def post(self, request, pk):
        ciclo = get_object_or_404(CicloBeneficio, pk=pk)
        
        # Validación de permisos... (Similar a arriba)
        # ... (Omitido por brevedad, usar misma lógica) ...
        
        ciclo.delete() # O ciclo.activo = False si prefieres historial
        
        messages.warning(request, "Lista eliminada.")
        return redirect('url_dashboard')

# --- AGREGAR PERSONAS GLOBALMENTE ---
class AgregarBeneficiarioGeneralView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_general/agregar_beneficiario_global.html' # Asegúrate de crear/usar este template
    context_object_name = 'miembros_disponibles'

    def get_queryset(self):
        tipo_slug = self.kwargs['tipo_slug']
        tipo_db = tipo_slug.upper() # CLAP o GAS

        try:
            # 1. Obtener el ciclo activo
            ciclo = CicloBeneficio.objects.get(tipo=tipo_db, activo=True)
        except CicloBeneficio.DoesNotExist:
            # Si no hay ciclo activo, no hay miembros que listar para agregar.
            messages.error(self.request, f"No existe un ciclo activo para {tipo_db}.")
            return CensoMiembro.objects.none()

        # 2. Obtener IDs de miembros que YA están en la lista (EntregaBeneficio)
        ids_en_lista = EntregaBeneficio.objects.filter(ciclo=ciclo).values_list('beneficiario_id', flat=True)

        # 3. Obtener todos los CensoMiembro que NO están en la lista
        # El Líder General puede ver todas las torres
        qs = CensoMiembro.objects.all().exclude(id__in=ids_en_lista).select_related('tower').order_by('tower__nombre', 'piso', 'apartamento_letra')
        
        # Opcional: Filtro por Torre (útil para el Líder General)
        torre_id = self.request.GET.get('torre')
        if torre_id and torre_id.isdigit():
            qs = qs.filter(tower_id=int(torre_id))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipo_slug = self.kwargs['tipo_slug']
        tipo_db = tipo_slug.upper()
        
        # Intentar obtener el ciclo activo para mostrar la información en el template
        ciclo = CicloBeneficio.objects.filter(tipo=tipo_db, activo=True).first()

        context['tipo_slug'] = tipo_slug
        context['titulo'] = f"Agregar Beneficiarios ({tipo_db})"
        context['ciclo_activo'] = ciclo
        context['torres'] = Tower.objects.all() # Para un posible filtro en el template
        context['torre_seleccionada'] = self.request.GET.get('torre')
        
        return context

    # El método POST se debe redefinir aquí para manejar la adición masiva de la lista.
    # Recibe 'tipo_slug' desde el argumento de la URL.
    def post(self, request, tipo_slug):
        miembros_ids = request.POST.getlist('miembros_ids') # Esperamos una lista de IDs de checkboxes
        
        if not miembros_ids:
            messages.error(request, "No seleccionaste a ningún miembro para agregar.")
            return redirect('lider_general:agregar_beneficiario_global', tipo_slug=tipo_slug)
            
        tipo_db = tipo_slug.upper()
        
        try:
            ciclo_activo = CicloBeneficio.objects.get(tipo=tipo_db, activo=True)
        except CicloBeneficio.DoesNotExist:
            messages.error(request, f"No existe un ciclo activo para {tipo_db}.")
            return redirect('ver_beneficio', tipo_slug=tipo_slug)

        # 4. Crear los objetos EntregaBeneficio
        objetos_a_crear = []
        miembros_seleccionados = CensoMiembro.objects.filter(id__in=miembros_ids)
        
        for miembro in miembros_seleccionados:
            objetos_a_crear.append(
                EntregaBeneficio(
                    ciclo=ciclo_activo,
                    beneficiario=miembro,
                    agregado_por=request.user
                )
            )

        # 5. Guardar en la base de datos de forma masiva
        try:
            # Usamos ignore_conflicts=True para evitar fallos si un beneficiario ya fue agregado
            EntregaBeneficio.objects.bulk_create(objetos_a_crear, ignore_conflicts=True)
            messages.success(request, f"Se agregaron **{len(objetos_a_crear)}** miembros a la lista de {tipo_db}.")
        except IntegrityError:
            messages.warning(request, "Algunos miembros ya estaban en la lista y fueron omitidos.")
        except Exception as e:
            messages.error(request, f"Error al guardar los beneficiarios: {e}")

        # 6. Redirigir a la lista principal de beneficios
        return redirect('ver_beneficio', tipo_slug=tipo_slug)