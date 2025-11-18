# App_LiderTorre/views.py

from django.views.generic import CreateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from App_Home.models import MovimientoFinanciero, CustomUser
from .mixins import LiderTorreRequiredMixin 
from .forms import IngresoCondominioForm, EgresoCondominioForm, IngresoBasuraForm
from django.shortcuts import redirect
from decimal import Decimal
from django.http import HttpResponseRedirect # Asegúrate de importar esto

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

    
    # -----------------------------------------------------------
    # MÉTODO form_valid CORREGIDO Y COMPLETO
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
            # >>> LÓGICA DE SALDO GENERAL/ESPECÍFICO CORREGIDA <<<
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
