# App_LiderTorre/views.py

from django.views.generic import CreateView, UpdateView, ListView, DeleteView, ListView, View
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect
from App_Home.models import MovimientoFinanciero, CustomUser, CensoMiembro, CicloBeneficio, EntregaBeneficio
from App_Home.forms import CensoMiembroForm
from .mixins import LiderTorreRequiredMixin 
from .forms import IngresoCondominioForm, EgresoCondominioForm, IngresoBasuraForm
from decimal import Decimal

# ==============================================================
# La plantilla del formulario será la misma para todos los tipos de movimiento
TEMPLATE_NAME = 'lider_torre/movimiento_form.html'
SUCCESS_URL = None # Se define dinámicamente en get_success_url

class BaseMovimientoCreateView(LoginRequiredMixin, LiderTorreRequiredMixin, CreateView):
    """Clase base que asigna automáticamente el creador, tipo, categoría y torre."""
    model = MovimientoFinanciero
    template_name = TEMPLATE_NAME

    TIPO_MOVIMIENTO = None 
    CATEGORIA_MOVIMIENTO = None
    MONTO_FIELD = None 

    # Solución al Problema 2: Redirección dinámica
    def get_success_url(self):
        """Devuelve la URL de éxito dinámica basada en la categoría."""
        categoria_slug = 'condominio' if 'Condominio' in self.CATEGORIA_MOVIMIENTO else 'basura'
        return reverse_lazy('ver_finanzas', kwargs={'categoria_slug': categoria_slug})

    def form_invalid(self, form):
        """Muestra los errores del formulario en la consola para debugging y asegura mensaje al usuario."""
        # Esto imprimirá la causa del error 200 OK en tu terminal de Django.
        print("--- DEBUG: Falla de Validación del Formulario (Causa de 200 OK) ---")
        if form.non_field_errors():
            print(f"Errores No de Campo (Non-Field Errors): {form.non_field_errors()}")
        
        for field, errors in form.errors.items():
            print(f"Error en el campo '{field}': {errors}")

        # Asegura que el usuario vea un mensaje genérico si el template no muestra errores específicos
        messages.error(self.request, "Hubo un error en los datos ingresados. Revisa el formulario para ver los errores específicos.")
            
        return super().form_invalid(form)
    
    # -----------------------------------------------------------
    # MÉTODO form_valid
    # -----------------------------------------------------------
    def form_valid(self, form):
        
        # 1. Asignar creador, tipo y categoría
        form.instance.creado_por = self.request.user
        form.instance.tipo = 'ING' if 'Ingreso' in self.TIPO_MOVIMIENTO else 'EGR'
        form.instance.categoria = 'CON' if 'Condominio' in self.CATEGORIA_MOVIMIENTO else 'BAS'

        # 2. Determinar la Torre (Lógica Central)
        # Se necesita asignar una torre para que el modelo no falle, incluso si el egreso es 'general'
        torre_seleccionada = form.cleaned_data.get('tower')
        
        if torre_seleccionada:
            # Opción 1: Usa la torre que viene en el formulario (Condominio General o Ingreso Basura General)
            form.instance.tower = torre_seleccionada
            
        elif form.instance.categoria == 'BAS' and form.instance.tipo == 'EGR':
            # ** CASO ESPECIAL: EGRESO BASURA GENERAL **
            # Se asigna la torre del usuario (si tiene) o la primera torre como asiento contable.
            
            if self.request.user.tower:
                form.instance.tower = self.request.user.tower
            else:
                from App_Home.models import Tower 
                try:
                    form.instance.tower = Tower.objects.first() 
                except Exception as e:
                    messages.error(self.request, f"Error: No se pudo asignar una torre de destino por defecto para el egreso general. {e}")
                    return self.form_invalid(form)
                    
        elif self.request.user.tower:
            # Caso Líder de Torre (LDT): Usa la torre asignada al usuario LDT
            form.instance.tower = self.request.user.tower
        
        else:
            messages.error(self.request, "Error: No se pudo asignar una torre de destino.")
            return self.form_invalid(form)

        # 3. Control de Egreso Negativo (Solo si es un Egreso)
        if form.instance.tipo == 'EGR':
            monto_egreso = form.cleaned_data.get(self.MONTO_FIELD)
            
            # ---------------------------------------------------------------------------------
            # >>> LÓGICA DE SALDO GENERAL/ESPECÍFICO <<<
            # ---------------------------------------------------------------------------------
            if form.instance.categoria == 'BAS':
                # Si es BASURA, chequeamos el saldo GLOBAL de todas las torres
                saldo_actual = MovimientoFinanciero.objects.calcular_saldo_general_basura()
            else:
                # Si es CONDOMINIO, chequeamos el saldo por Torre
                saldo_actual = MovimientoFinanciero.objects.calcular_saldo_torre(
                    tower=form.instance.tower, 
                    categoria=form.instance.categoria
                )
            # ---------------------------------------------------------------------------------
            
            if saldo_actual < monto_egreso:
                # Mensaje de error ajustado para reflejar si es saldo GENERAL o por Torre
                torre_nombre = 'GENERAL' if form.instance.categoria == 'BAS' else form.instance.tower.nombre
                
                messages.error(
                    self.request, 
                    f"Saldo insuficiente ({self.CATEGORIA_MOVIMIENTO}) en la administración {torre_nombre} para realizar este Egreso. Saldo actual: {saldo_actual:.2f} Bs."
                )
                return self.form_invalid(form)

        # 4. Asignar Montos (Se asigna el monto ingresado y cero al campo no usado)
        monto = form.cleaned_data[self.MONTO_FIELD]
        
        if self.MONTO_FIELD == 'monto_condominio':
            form.instance.monto_condominio = monto
            form.instance.monto_basura = Decimal(0.00) 
            
        elif self.MONTO_FIELD == 'monto_basura':
            form.instance.monto_basura = monto
            form.instance.monto_condominio = Decimal(0.00) 
            
        # 5. Guardar el objeto manipulado
        try:
            self.object = form.save(commit=True) 
        except Exception as e:
            error_msg = f"Error de Base de Datos al intentar guardar el movimiento: {e}"
            print(f"--- DEBUG FATAL: {error_msg} ---")
            messages.error(self.request, error_msg)
            return self.form_invalid(form)

        # 6. Mensaje de éxito
        # Determinar el nombre de la administración para el mensaje de éxito
        torre_display = self.object.tower.nombre
        if self.object.tipo == 'EGR' and self.object.categoria == 'BAS':
            # Si es un egreso general de basura, mostramos 'GENERAL'
            torre_display = 'GENERAL'
        
        # Usamos el nombre ajustado en el mensaje
        messages.success(self.request, f"{self.TIPO_MOVIMIENTO} de {self.CATEGORIA_MOVIMIENTO} registrado con éxito en la Administración {torre_display}.")
        
        # 7. Retornar la redirección
        return HttpResponseRedirect(self.get_success_url())
    

class RegistrarIngresoCondominioView(BaseMovimientoCreateView):
    form_class = IngresoCondominioForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

class RegistrarEgresoCondominioView(BaseMovimientoCreateView):
    form_class = EgresoCondominioForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

class RegistrarIngresoBasuraView(BaseMovimientoCreateView):
    form_class = IngresoBasuraForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'

# ==============================================================
# --- GESTIÓN DE CENSO LOCAL (LÍDER TORRE) ---
# ==============================================================

# 1. VISTA DE LISTA
class CensoTorreListView(LiderTorreRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_torre/censo_list_torre.html'
    context_object_name = 'miembros'

    def get_queryset(self):
        # FILTRO AUTOMÁTICO: Solo muestra gente de SU torre
        return CensoMiembro.objects.filter(tower=self.request.user.tower).order_by('piso', 'apartamento_letra')

# 2. VISTA DE CREACIÓN
class CensoTorreCreateView(LiderTorreRequiredMixin, CreateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_torre/censo_form_torre.html'
    success_url = reverse_lazy('lider_torre:censo_lista')

    def get_form_kwargs(self):
        """Pasa la torre del usuario actual al formulario para validación."""
        kwargs = super().get_form_kwargs()
        kwargs['torre_usuario'] = self.request.user.tower
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'tower' in form.fields:
            form.fields['tower'].widget.attrs['hidden'] = True
            form.fields['tower'].required = False
        return form

    def form_valid(self, form):
        form.instance.tower = self.request.user.tower
        messages.success(self.request, "Vecino registrado correctamente.")
        return super().form_valid(form)

# 3. VISTA DE EDICIÓN
class CensoTorreUpdateView(LiderTorreRequiredMixin, UpdateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_torre/censo_form_torre.html'
    success_url = reverse_lazy('lider_torre:censo_lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasa la torre al formulario para la validación de 'Jefe de Familia Único'
        kwargs['torre_usuario'] = self.request.user.tower
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'tower' in form.fields:
            # 1. Ocultamos el campo visualmente.
            form.fields['tower'].widget.attrs['hidden'] = True
            # 2. Hacemos el campo NO requerido para que la validación inicial lo ignore.
            form.fields['tower'].required = False
        return form
        
    # --- MÉTODO CRÍTICO AÑADIDO/CORREGIDO ---
    def form_valid(self, form):
        # 3. ¡IMPORTANTE! Asignamos explícitamente la torre del usuario al objeto.
        # Esto evita el IntegrityError al asegurar que tower_id NO es NULL.
        form.instance.tower = self.request.user.tower
        messages.success(self.request, "Cambios guardados correctamente.")
        return super().form_valid(form)
    # ----------------------------------------

    def get_queryset(self):
        # Seguridad: Asegura que solo pueda editar miembros de su propia torre
        return super().get_queryset().filter(tower=self.request.user.tower)
        
    # Método de debugging que añadiste anteriormente
    def form_invalid(self, form):
        print("\n*** ERROR DE VALIDACIÓN DE FORMULARIO DE EDICIÓN ***")
        for field, errors in form.errors.items():
            print(f"Campo: {field} -> Errores: {errors}")
        if form.non_field_errors():
            print(f"Errores No de Campo: {form.non_field_errors()}")
        print("**************************************************\n")
        return super().form_invalid(form)

# 4. VISTA DE ELIMINACIÓN
class CensoTorreDeleteView(LiderTorreRequiredMixin, DeleteView):
    model = CensoMiembro
    template_name = 'lider_torre/censo_confirm_delete.html'
    success_url = reverse_lazy('lider_torre:censo_lista')

    def get_queryset(self):
        return super().get_queryset().filter(tower=self.request.user.tower)

    def form_valid(self, form):
        messages.success(self.request, "Residente eliminado correctamente.")
        return super().form_valid(form)
    

# VISTA PARA AGREGAR VECINOS A LISTAS DE BENEFICIOS (CLAP/GAS)

class AgregarVecinosTorreView(LoginRequiredMixin, LiderTorreRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_torre/agregar_beneficio.html'
    context_object_name = 'vecinos'

    def _get_benefit_slug_map(self):
        """Mapea los códigos DB ('CLAP', 'GAS') a slugs minúsculos ('clap', 'gas') para la URL."""
        # Usa la lista TIPOS definida dentro del modelo CicloBeneficio
        return [(db.lower(), db) for db, desc in CicloBeneficio.TIPOS] #

    def get_queryset(self):
        user_tower = self.request.user.tower
        if not user_tower:
            return CensoMiembro.objects.none()
            
        tipo_slug = self.kwargs.get('tipo_slug')
        
        # Encuentra el código DB ('CLAP' o 'GAS')
        tipo_db = next((db for slug, db in self._get_benefit_slug_map() if slug == tipo_slug), None)
        
        if not tipo_db:
            return CensoMiembro.objects.none()

        # 1. Obtener ciclo activo (usando campo 'activo')
        ciclo = CicloBeneficio.objects.filter(tipo=tipo_db, activo=True).first()
        if not ciclo:
            return CensoMiembro.objects.none()

        # 2. Excluir los que YA están en la lista (usando EntregaBeneficio)
        ids_en_lista = EntregaBeneficio.objects.filter(ciclo=ciclo).values_list('beneficiario_id', flat=True)
        
        # 3. Filtrar y ordenar
        return CensoMiembro.objects.filter(
            tower=user_tower,
            es_jefe_familia=True # Si este es el filtro deseado
        ).exclude(id__in=ids_en_lista).order_by('piso', 'apartamento_letra')


    def post(self, request, *args, **kwargs):
        tipo_slug = self.kwargs['tipo_slug']
        miembros_ids = request.POST.getlist('miembros_ids')
        
        if not miembros_ids:
            messages.error(request, "No seleccionaste a ningún vecino para agregar.")
            return redirect('lider_torre:agregar_vecinos', tipo_slug=tipo_slug)
            
        try:
            tipo_db = next(db for slug, db in self._get_benefit_slug_map() if slug == tipo_slug)
            
            ciclo_activo = CicloBeneficio.objects.get(tipo=tipo_db, activo=True)
            torre_usuario = request.user.tower
            
        except CicloBeneficio.DoesNotExist:
            messages.error(request, f"No existe un ciclo activo para {tipo_slug.upper()}.")
            return redirect('ver_beneficio', tipo_slug=tipo_slug)
        except StopIteration:
            messages.error(request, "Tipo de beneficio inválido.")
            return redirect('ver_beneficio', tipo_slug=tipo_slug)

        # 4. Crear los objetos EntregaBeneficio
        objetos_a_crear = []
        miembros_seleccionados = CensoMiembro.objects.filter(id__in=miembros_ids, tower=torre_usuario)
        
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
            EntregaBeneficio.objects.bulk_create(objetos_a_crear)
            messages.success(request, f"Se agregaron **{len(objetos_a_crear)}** vecinos a la lista de {tipo_slug.upper()}.")
        except IntegrityError:
            messages.warning(request, "Algunos vecinos ya estaban en la lista y fueron omitidos (duplicado).")
        except Exception as e:
            messages.error(request, f"Error al guardar los beneficiarios: {e}")

        # 6. Redirigir a la lista principal de beneficios
        return redirect('ver_beneficio', tipo_slug=tipo_slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipo_slug = self.kwargs.get('tipo_slug')
        context['tipo_slug'] = tipo_slug
        context['titulo'] = "Agregar Vecinos a " + tipo_slug.upper()
        
        tipo_db = next((db for slug, db in self._get_benefit_slug_map() if slug == tipo_slug), None)
        context['ciclo'] = CicloBeneficio.objects.filter(tipo=tipo_db, activo=True).first()
        return context

# La vista para procesar el POST puede ser la misma 'AgregarBeneficiarioGeneralView' 
# reutilizada o una similar en App_LiderTorre si quieres separar lógica.
# Por simplicidad, el formulario en el HTML apuntará a una vista de acción compartida o local.
class ProcesarAgregarTorreView(LoginRequiredMixin, View):
    def post(self, request):
        censo_id = request.POST.get('censo_id')
        ciclo_id = request.POST.get('ciclo_id')
        
        miembro = get_object_or_404(CensoMiembro, pk=censo_id)
        # SEGURIDAD: Verificar que el miembro pertenece a la torre del líder
        if miembro.tower != request.user.tower:
            messages.error(request, "No puedes agregar vecinos de otra torre.")
            return redirect('url_dashboard')

        ciclo = get_object_or_404(CicloBeneficio, pk=ciclo_id)
        
        EntregaBeneficio.objects.create(ciclo=ciclo, beneficiario=miembro, agregado_por=request.user)
        messages.success(request, "Vecino agregado.")
        
        slug = 'clap' if ciclo.tipo == 'CLAP' else 'gas'
        return redirect('lider_torre:agregar_vecinos', tipo_slug=slug)