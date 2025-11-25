# App_Home/forms.py

from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count
from .models import CustomUser, Tower, CensoMiembro

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
        fields = ('first_name', 'last_name', 'cedula', 'rol', 'tower', 'apartamento') 

        widgets = {
            'rol': forms.Select(choices=CustomUser.ROLES),
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
        self.fields['tower'].required = False


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
                    self.add_error(None, f"Error de Permisos: El rol secundario '{role_name}' ya está asignado a otro usuario. Solo se permite un líder por gestión.")
        
        # --- 2. VALIDACIÓN DE ASIGNACIÓN DE TORRE PARA LÍDERES DE TORRE ---
        rol = cleaned_data.get('rol')
        tower = cleaned_data.get('tower') # Corregido a 'tower'
        
        ROL_LIDER_TORRE = CustomUser.ROL_LIDER_TORRE 
        
        if rol == ROL_LIDER_TORRE:
            
            # Validación A: La Torre no puede ser nula (lógica existente)
            if not tower:
                self.add_error('tower', "Debes seleccionar una Torre obligatoriamente para ser Líder de Torre.")
            else:
                # Validación B: Solo un Líder por Torre (Lógica CRÍTICA)
                # Buscamos si existe otro Líder de Torre (LDT) en la torre seleccionada, excluyendo al usuario actual.
                query = CustomUser.objects.filter(
                    rol=ROL_LIDER_TORRE,
                    tower=tower
                ).exclude(pk=self.instance.pk if self.instance and self.instance.pk else None)
                
                if query.exists():
                    # Usamos 'nombre' del objeto tower si está disponible para el mensaje de error
                    tower_name = getattr(tower, 'nombre', 'seleccionada') 
                    self.add_error('tower', f"La Torre {tower_name} ya tiene un Líder de Torre asignado. Por favor, selecciona otra Torre o Rol.")
        
        # Limpieza: Si el rol NO es Líder de Torre, el campo 'tower' se anula en la data limpia.
        # Esto previene errores de base de datos si cambian de Líder de Torre a Líder General.
        elif 'tower' in cleaned_data: 
            cleaned_data['tower'] = None 
            
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
    
# Formulario para filtrar Movimientos Financieros por fechas
class FormularioFiltroMovimientos(forms.Form):
    fecha_inicio = forms.DateField(
        required=False, 
        label='Fecha de Inicio',
        # Utilizamos 'type': 'date' para el selector de calendario HTML5
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False, 
        label='Fecha de Fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Validación: La fecha de inicio no puede ser posterior a la fecha de fin.
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            # Usamos add_error para mostrar el mensaje junto al campo.
            msg = 'La fecha de inicio no puede ser posterior a la fecha de fin.'
            self.add_error('fecha_inicio', msg)
            self.add_error('fecha_fin', msg)

        return cleaned_data
    
class CensoMiembroForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # 1. Extraemos el dato 'torre_usuario' que nos manda la vista
        self.torre_usuario = kwargs.pop('torre_usuario', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = CensoMiembro
        fields = ['nombres', 'apellidos', 'cedula', 'fecha_nacimiento', 'genero', 'telefono', 'tower', 'piso', 'apartamento_letra', 'es_jefe_familia']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'tower': forms.Select(attrs={'class': 'form-select'}),
            'piso': forms.Select(attrs={'class': 'form-select'}),
            'apartamento_letra': forms.Select(attrs={'class': 'form-select'}),
            # Clase especial para el switch
            'es_jefe_familia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        
        es_jefe = cleaned_data.get('es_jefe_familia')
        piso = cleaned_data.get('piso')
        letra = cleaned_data.get('apartamento_letra')
        
        # 2. DETERMINAR LA TORRE CORRECTA
        # Si viene del formulario (Lider General), usamos esa.
        # Si no viene (Lider Torre), usamos la que inyectamos en __init__.
        torre_final = cleaned_data.get('tower')
        if not torre_final and self.torre_usuario:
            torre_final = self.torre_usuario

        # 3. VALIDACIÓN DE JEFE DE FAMILIA ÚNICO
        if es_jefe and torre_final and piso and letra:
            # Buscamos si YA existe alguien en esa Torre + Piso + Letra que sea Jefe
            # .exclude(pk=self.instance.pk) es VITAL: evita que el sistema se bloquee al editar al mismo usuario.
            existe_otro_jefe = CensoMiembro.objects.filter(
                tower=torre_final,
                piso=piso,
                apartamento_letra=letra,
                es_jefe_familia=True
            ).exclude(pk=self.instance.pk).exists()

            if existe_otro_jefe:
                # Esto lanzará el error rojo en la pantalla e impedirá guardar
                msg = f"Error: Ya existe un Jefe de Familia registrado en la {torre_final}, Apto {piso}-{letra}."
                self.add_error('es_jefe_familia', msg)
                raise ValidationError(msg)
        
        return cleaned_data