# App_LiderTorre/forms.py

from django import forms
# Importa MovimientoFinanciero desde App_Home
from App_Home.models import MovimientoFinanciero 

class MovimientoFormBase(forms.ModelForm):
    """Formulario base para Ingresos y Egresos. Solo muestra fecha y descripción."""
    # --- NUEVO CAMPO: Tasa BCV ---
    # Lo definimos de forma explícita para controlar el widget, el step y la precisión.
    tasa_bcv = forms.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        min_value=0.0001, # La tasa debe ser un valor positivo
        label='Tasa BCV (Bs/USD)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'required': 'required'})
    )
    class Meta:
        model = MovimientoFinanciero
        # Excluimos los campos que la vista auto-asignará
        exclude = ('tipo', 'categoria', 'tower', 'creado_por', 'monto_basura', 'monto_condominio')
        
        fields = ['fecha', 'descripcion', 'tasa_bcv'] 

        widgets = {
            # Usamos la clase 'form-control' para aplicar los estilos de styles-lidergeneral.css
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
        labels = {
            'fecha': 'Fecha del Movimiento',
            'descripcion': 'Descripción / Detalle del Pago',
        }

# --- Formularios Específicos para Condominio ---

class IngresoCondominioForm(MovimientoFormBase):
    # Campo personalizado para el monto (se usará en el modelo)
    monto_condominio = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Ingreso Condominio (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta(MovimientoFormBase.Meta):
        # Campos a mostrar en el formulario de ingreso de condominio
        exclude = ('tipo', 'categoria', 'tower', 'creado_por', 'monto_basura')
        fields = MovimientoFormBase.Meta.fields + ['monto_condominio']

class EgresoCondominioForm(MovimientoFormBase):
    monto_condominio = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Egreso Condominio (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta(MovimientoFormBase.Meta):
        exclude = ('tipo', 'categoria', 'tower', 'creado_por', 'monto_basura')
        fields = MovimientoFormBase.Meta.fields + ['monto_condominio']

# --- Formularios Específicos para Cuarto de Basura ---

class IngresoBasuraForm(MovimientoFormBase):
    monto_basura = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Ingreso Cuarto de Basura (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta(MovimientoFormBase.Meta):
        exclude = ('tipo', 'categoria', 'tower', 'creado_por', 'monto_condominio')
        fields = MovimientoFormBase.Meta.fields + ['monto_basura']
