from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Tower

# Register your models here.

# Personalización del Administrador de Usuarios
class AdministradorUsuario(UserAdmin):
    # Campos adicionales para mostrar en la lista de usuarios
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'rol', 'torre')
    
    # Definir la sección de campos adicionales en el formulario de detalle del usuario
    fieldsets = UserAdmin.fieldsets + (
        # Nueva sección en el formulario de edición de usuario para roles y permisos
        ('Roles y Asignación', {'fields': ('rol', 'torre', 'es_admin_basura', 'es_admin_clap', 'es_admin_bombonas')}),
    )

# Registrar los modelos
admin.site.register(CustomUser, AdministradorUsuario)
admin.site.register(Tower)