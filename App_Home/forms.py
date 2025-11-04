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

# Formulario de Perfil para el PASO 2 (Datos completos, Roles y Superusuario)
class FormularioPerfilUsuario(forms.ModelForm):
    
    # Definimos la Cédula (que no es parte del modelo base de Django)
    cedula = forms.CharField(max_length=15, required=True, label='Cédula de Identidad')
    
    # NUEVOS CAMPOS: Roles Secundarios y Superusuario (Checkboxes)
    es_admin_basura = forms.BooleanField(required=False, label='Optar por Líder de Basura')
    es_admin_clap = forms.BooleanField(required=False, label='Optar por Líder de CLAP')
    es_admin_bombonas = forms.BooleanField(required=False, label='Optar por Líder de Bombonas')
    is_superuser_opt = forms.BooleanField(required=False, label='Optar por ser Superusuario (Admin. de Desarrollo)')


    class Meta:
        model = CustomUser
        # Aquí NO incluimos los booleanos, los manejamos explícitamente en save()
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
            self.fields['is_superuser_opt'].initial = self.instance.is_superuser
            
        # Asegurar que los campos principales sean requeridos
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['rol'].required = True


    # VALIDACIÓN CRUCIAL: Limitar Líderes Generales a 2
    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        # Usar la constante definida en models.py (asumiendo que es 3)
        ROL_LIDER_GENERAL = CustomUser.ROL_LIDER_GENERAL
        
        # Solo aplicamos la restricción si el rol seleccionado es Líder General (3)
        # y si estamos creando un nuevo LG o cambiando un rol no general
        if rol == ROL_LIDER_GENERAL and self.instance.rol != ROL_LIDER_GENERAL:
            conteo_lideres = CustomUser.objects.filter(rol=ROL_LIDER_GENERAL).count()
            
            if conteo_lideres >= 2:
                raise ValidationError("Ya existe el número máximo de 2 Líderes Generales permitidos. Por favor, selecciona otro rol.")
        
        return rol


    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Guardar los datos de los Checkboxes en el modelo
        user.es_admin_basura = self.cleaned_data.get('es_admin_basura', user.es_admin_basura)
        user.es_admin_clap = self.cleaned_data.get('es_admin_clap', user.es_admin_clap)
        user.es_admin_bombonas = self.cleaned_data.get('es_admin_bombonas', user.es_admin_bombonas)
        
        # Guardar la opción de Superusuario
        user.is_superuser = self.cleaned_data.get('is_superuser_opt', user.is_superuser)
        user.is_staff = user.is_superuser # Si es superusuario, también debe ser staff
        
        if commit:
            user.save()
        return user