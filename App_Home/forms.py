from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count
from .models import CustomUser, Tower 

# Formulario de Registro para el PASO 1 (Solo autenticación)
class FormularioCreacionUsuario(UserCreationForm):
    class Meta:
        model = CustomUser
        # UserCreationForm automáticamente añade 'password1' y 'password2'
        fields = ('username', 'email')
        
    def clean(self):
        # Mantiene la validación de password del UserCreationForm
        return super().clean()

# Formulario de Perfil para el PASO 2 (Datos completos, Roles)
class FormularioPerfilUsuario(forms.ModelForm):
    
    # Definimos la Cédula (que no es parte del modelo base de Django)
    cedula = forms.CharField(max_length=15, required=True, label='Cédula de Identidad')
    
    # NUEVOS CAMPOS: Roles Secundarios (Checkboxes)
    es_admin_basura = forms.BooleanField(required=False, label='Optar por Líder de Basura')
    es_admin_clap = forms.BooleanField(required=False, label='Optar por Líder de CLAP')
    es_admin_bombonas = forms.BooleanField(required=False, label='Optar por Líder de Bombonas')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'cedula', 'rol', 'torre')

        widgets = {
            'rol': forms.Select(choices=CustomUser.OPCIONES_ROLES),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inicializar los checkboxes con el valor actual del usuario
        if self.instance:
            self.fields['es_admin_basura'].initial = self.instance.es_admin_basura
            self.fields['es_admin_clap'].initial = self.instance.es_admin_clap
            self.fields['es_admin_bombonas'].initial = self.instance.es_admin_bombonas
            
        # Asegurar que los campos principales sean requeridos
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['rol'].required = True


    # VALIDACIÓN PRINCIPAL: Limitar Líderes Generales (2) y Roles Secundarios (1)
    def clean(self):
        cleaned_data = super().clean()
        
        # --- 1. VALIDACIÓN DE ROLES SECUNDARIOS (MÁXIMO 1 POR ROL) ---
        secondary_roles = [
            ('es_admin_basura', 'Líder de Basura'),
            ('es_admin_clap', 'Líder de CLAP'),
            ('es_admin_bombonas', 'Líder de Bombonas'),
        ]
        
        for field_name, role_name in secondary_roles:
            is_checked = cleaned_data.get(field_name) 
            
            if is_checked:
                filter_kwargs = {field_name: True}
                query = CustomUser.objects.filter(**filter_kwargs)
                
                # Excluir al usuario actual si existe
                if self.instance and self.instance.pk:
                    query = query.exclude(pk=self.instance.pk)

                if query.exists():
                    # 💡 SOLUCIÓN 1: Muestra un mensaje GLOBAL (non-field error)
                    self.add_error(None, f"Error de Permisos: El rol secundario '{role_name}' ya está asignado a otro usuario. Solo se permite un líder por gestión.")
        
        # --- 2. VALIDACIÓN DE ASIGNACIÓN DE TORRE PARA LÍDERES DE TORRE ---
        rol = cleaned_data.get('rol')
        torre = cleaned_data.get('torre')
        
        ROL_LIDER_TORRE = CustomUser.ROL_LIDER_TORRE 
        
        # 💡 SOLUCIÓN 2: Si el rol es Líder de Torre y NO se ha seleccionado torre
        if rol == ROL_LIDER_TORRE and not torre:
            # Añadir un error al campo 'torre'
            self.add_error('torre', "Debes seleccionar una Torre obligatoriamente para ser Líder de Torre.")
            
        return cleaned_data
        
    # VALIDACIÓN CRUCIAL: Limitar Líderes Generales a 2
    def clean_rol(self):
        # Lógica existente para Líder General
        rol = self.cleaned_data.get('rol')
        ROL_LIDER_GENERAL = CustomUser.ROL_LIDER_GENERAL
        
        if rol == ROL_LIDER_GENERAL and self.instance.rol != ROL_LIDER_GENERAL:
            conteo_lideres = CustomUser.objects.filter(rol=ROL_LIDER_GENERAL).exclude(pk=self.instance.pk).count()
            
            if conteo_lideres >= 2:
                raise ValidationError("Ya existe el número máximo de 2 Líderes Generales permitidos. Por favor, selecciona otro rol.")
        
        return rol


    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Guardar los datos de los Checkboxes en el modelo
        user.es_admin_basura = self.cleaned_data.get('es_admin_basura', user.es_admin_basura)
        user.es_admin_clap = self.cleaned_data.get('es_admin_clap', user.es_admin_clap)
        user.es_admin_bombonas = self.cleaned_data.get('es_admin_bombonas', user.es_admin_bombonas)
        
        # ASIGNAR PERMISOS DE LÍDER GENERAL (Lógica del paso anterior)
        if user.rol == CustomUser.ROL_LIDER_GENERAL:
             user.is_superuser = True
             user.is_staff = True 
        else:
             user.is_superuser = False
             user.is_staff = False
        
        if commit:
            user.save()
        return user