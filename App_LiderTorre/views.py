# App_LiderTorre/views.py

from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from App_Home.models import MovimientoFinanciero, CustomUser
from .mixins import LiderTorreRequiredMixin 
from .forms import IngresoCondominioForm, EgresoCondominioForm, IngresoBasuraForm
from django.shortcuts import redirect

# La plantilla del formulario será la misma para todos los tipos de movimiento
TEMPLATE_NAME = 'lider_torre/movimiento_form.html'
SUCCESS_URL = None # Se define dinámicamente en get_success_url

class BaseMovimientoCreateView(LoginRequiredMixin, LiderTorreRequiredMixin, CreateView):
    """Clase base que asigna automáticamente el creador, tipo, categoría y torre."""
    model = MovimientoFinanciero
    template_name = TEMPLATE_NAME
    # Ya no se usa success_url, se usa get_success_url

    TIPO_MOVIMIENTO = None 
    CATEGORIA_MOVIMIENTO = None
    MONTO_FIELD = None 

    # Solución al Problema 2: Redirección dinámica
    def get_success_url(self):
        """Devuelve la URL de éxito dinámica basada en la categoría."""
        categoria_slug = 'condominio' if 'Condominio' in self.CATEGORIA_MOVIMIENTO else 'basura'
        return reverse_lazy('ver_finanzas', kwargs={'categoria_slug': categoria_slug})

    def form_valid(self, form):
        # 1. Asignar datos iniciales
        form.instance.creado_por = self.request.user
        form.instance.tower = self.request.user.tower
        form.instance.tipo = 'ING' if 'Ingreso' in self.TIPO_MOVIMIENTO else 'EGR'
        form.instance.categoria = 'CON' if 'Condominio' in self.CATEGORIA_MOVIMIENTO else 'BAS'
        
        # 2. **VALIDACIÓN CRÍTICA DE SALDO (Solución al Problema 1)**
        monto = form.cleaned_data.get(self.MONTO_FIELD, 0)
        
        if form.instance.tipo == 'EGR':
            # Nota: MovimientoFinanciero.objects.calcular_saldo_torre debe estar en App_Home/models.py
            saldo_actual = MovimientoFinanciero.objects.calcular_saldo_torre(
                tower=form.instance.tower, 
                categoria=form.instance.categoria
            )
            
            if saldo_actual < monto:
                messages.error(self.request, f"Operación denegada. Saldo insuficiente para el Egreso de {self.CATEGORIA_MOVIMIENTO}. Saldo disponible: Bs. {saldo_actual:.2f}")
                # CRÍTICO: Detiene el guardado y retorna para mostrar el error en el formulario
                return self.form_invalid(form) 
                
        # 3. Asignar montos dinámicos
        
        if self.MONTO_FIELD == 'monto_condominio':
            form.instance.monto_condominio = monto
            form.instance.monto_basura = 0 
            
        elif self.MONTO_FIELD == 'monto_basura':
            form.instance.monto_basura = monto
            form.instance.monto_condominio = 0 
            
        response = super().form_valid(form)
        
        messages.success(self.request, f"{self.TIPO_MOVIMIENTO} de {self.CATEGORIA_MOVIMIENTO} registrado con éxito para la Torre {form.instance.tower.nombre}.")
        return response


# ----------------------------------------------------------------------
# Vistas Concretas
# ----------------------------------------------------------------------

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