# App_LiderGeneral/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count
from App_Home.models import CustomUser, Tower, SolicitudDocumento 
from App_LiderTorre.forms import MovimientoFormBase


class FormularioAdminUsuario(forms.ModelForm):
    """
    Formulario para la Administración de Usuarios (CRUD), usado 
    por el Líder General. Incluye campos de edición de perfil, roles 
    y permisos avanzados.
    """
    
    # CAMPOS BASE AÑADIDOS (Permiten al administrador editar datos básicos)
    username = forms.CharField(max_length=150, required=True, label='Nombre de Usuario')
    email = forms.EmailField(required=True, label='Correo Electrónico')
    cedula = forms.CharField(max_length=15, required=True, label='Cédula de Identidad')
    
    # Roles Secundarios (Se definen como BooleanField para los Checkboxes)
    es_admin_basura = forms.BooleanField(required=False, label='Administrador de Basura')
    es_admin_clap = forms.BooleanField(required=False, label='Administrador de CLAP')
    es_admin_bombonas = forms.BooleanField(required=False, label='Administrador de Bombonas')

    class Meta:
        model = CustomUser
        # Incluimos TODOS los campos que un administrador puede editar
        fields = [
            'username', 'email', 'cedula', 
            'first_name', 'last_name', 'apartamento', 'tower', 'rol',
            'is_active', 'is_staff', 'is_superuser', # Permisos avanzados de Django
            'es_admin_basura', 'es_admin_clap', 'es_admin_bombonas'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # LÓGICA DE VALIDACIÓN CRÍTICA: Limitar Líderes Generales a 2
    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        ROL_LIDER_GENERAL = CustomUser.ROL_LIDER_GENERAL 
        
        # Validar si el rol es Líder General y si el rol está cambiando
        if rol == ROL_LIDER_GENERAL:
            if self.instance.pk is None or self.instance.rol != ROL_LIDER_GENERAL:
                
                # Contamos a todos los líderes, excluyendo la instancia actual (para ediciones)
                conteo_lideres = CustomUser.objects.filter(rol=ROL_LIDER_GENERAL).exclude(pk=self.instance.pk).count()
                
                if conteo_lideres >= 2:
                    raise ValidationError("Ya existe el número máximo de 2 Líderes Generales permitidos. Por favor, selecciona otro rol.")
        
        return rol


    def save(self, commit=True):
        """Asegura el guardado correcto de permisos y roles secundarios."""
        user = super().save(commit=False)
        
        # 1. Guardar los datos de los Checkboxes de Roles Secundarios
        user.es_admin_basura = self.cleaned_data.get('es_admin_basura', user.es_admin_basura)
        user.es_admin_clap = self.cleaned_data.get('es_admin_clap', user.es_admin_clap)
        user.es_admin_bombonas = self.cleaned_data.get('es_admin_bombonas', user.es_admin_bombonas)
        
        # 2. Asignar is_staff automáticamente al ser Líder General
        user.is_staff = (user.rol == user.ROL_LIDER_GENERAL)

        if commit:
            user.save()
        return user
    
# --- Formularios Base para Líder General ---

class LiderGeneralMovimientoBaseForm(MovimientoFormBase):
    """Formulario base para Ingresos y Egresos del Líder General, añade el campo 'tower'."""
    # Añadimos el campo 'tower' (Torre) que estaba excluido en MovimientoFormBase
    tower = forms.ModelChoiceField(
        queryset=Tower.objects.all().order_by('nombre'),
        label='Seleccionar Torre',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'})
    )

    class Meta(MovimientoFormBase.Meta):
        # Aseguramos que 'tower' no esté en exclude y lo añadimos a fields
        fields = MovimientoFormBase.Meta.fields + ['tower']

# --- Formularios Específicos para Líder General (Condominio) ---

class IngresoCondominioGeneralForm(LiderGeneralMovimientoBaseForm):
    # Replicamos el campo de monto específico para que no se pierda en la herencia
    monto_condominio = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Ingreso Condominio (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta(LiderGeneralMovimientoBaseForm.Meta):
        fields = LiderGeneralMovimientoBaseForm.Meta.fields + ['monto_condominio']


class EgresoCondominioGeneralForm(LiderGeneralMovimientoBaseForm):
    # Replicamos el campo de monto específico
    monto_condominio = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Egreso Condominio (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    class Meta(LiderGeneralMovimientoBaseForm.Meta):
        fields = LiderGeneralMovimientoBaseForm.Meta.fields + ['monto_condominio']

# --- Formularios Específicos para Líder General / Admin Basura (Cuarto de Basura) ---

class IngresoBasuraGeneralForm(LiderGeneralMovimientoBaseForm):
    # Replicamos el campo de monto específico
    monto_basura = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Ingreso Cuarto de Basura (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta(LiderGeneralMovimientoBaseForm.Meta):
        fields = LiderGeneralMovimientoBaseForm.Meta.fields + ['monto_basura']


class EgresoBasuraGeneralForm(LiderGeneralMovimientoBaseForm):
    # Replicamos el campo de monto específico
    monto_basura = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label='Monto Egreso Cuarto de Basura (Bs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos el campo tower no requerido para egresos generales de Basura
        self.fields['tower'].required = False

    class Meta(LiderGeneralMovimientoBaseForm.Meta):
        fields = LiderGeneralMovimientoBaseForm.Meta.fields + ['monto_basura']


# --- Formulario para Procesar Solicitudes de Documentos ---
class ProcesarCartaConductaForm(forms.ModelForm):
    """
    Formulario usado por el Líder General para completar los datos
    faltantes de una Carta de Buena Conducta antes de generar el PDF.
    """
    anios_residencia = forms.CharField(
        max_length=50,
        label='Años de Residencia',
        help_text='Ejemplo: "10 años" o "5 años y 2 meses"',
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': 'required'})
    )

    class Meta:
        model = SolicitudDocumento
        fields = ['anios_residencia']

# --- NUEVO: Formulario para Carta de Mudanza ---
class ProcesarCartaMudanzaForm(forms.ModelForm):
    class Meta:
        model = SolicitudDocumento
        fields = ['mudanza_anio_inicio', 'mudanza_fecha_fin']
        labels = {
            'mudanza_anio_inicio': 'Año de Inicio de Residencia',
            'mudanza_fecha_fin': 'Fecha de Finalización (Mes y Año)'
        }
        widgets = {
            'mudanza_anio_inicio': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: 2023',
                'type': 'number'
            }),
            'mudanza_fecha_fin': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Octubre del 2025'
            }),
        }