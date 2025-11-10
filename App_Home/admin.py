# App_Home/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum, F
from django.utils.html import format_html
from .models import CustomUser, Tower, MovimientoFinanciero


# Clase de administrador personalizada para CustomUser
class AdministradorUsuario(UserAdmin):
    # Campos que se mostrarán en la lista de usuarios del Admin
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff', 
        'rol', 'tower', # <--- ¡CORREGIDO! De 'torre' a 'tower'
        'is_active', 'mostrar_roles_secundarios'
    )
    
    # Campos que se podrán editar/filtrar
    list_filter = ('is_staff', 'is_active', 'rol', 'tower', 'es_admin_basura', 'es_admin_clap', 'es_admin_bombonas')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'cedula')
    ordering = ('username',)

    # Campos de roles secundarios combinados
    def mostrar_roles_secundarios(self, obj):
        roles = []
        if obj.es_admin_basura:
            roles.append("Basura")
        if obj.es_admin_clap:
            roles.append("CLAP")
        if obj.es_admin_bombonas:
            roles.append("Bombonas")
        
        if roles:
            return format_html('<span style="color: blue;">{}</span>', ", ".join(roles))
        return "-"
    mostrar_roles_secundarios.short_description = 'Roles Secundarios'
    
    # Definición de Fieldsets (cómo se agrupan los campos en la vista de edición)
    fieldsets = UserAdmin.fieldsets + (
        ('Información Personal Adicional', {'fields': ('cedula', 'apartamento', 'tower')}),
        ('Roles en la Comunidad', {'fields': ('rol', 'es_admin_basura', 'es_admin_clap', 'es_admin_bombonas')}),
    )

# ----------------------------------------------------
# Administrador para el modelo Tower
# ----------------------------------------------------
class AdministradorTower(admin.ModelAdmin):
    list_display = ('nombre', 'saldo_condominio', 'saldo_basura')
    search_fields = ('nombre',)
    ordering = ('nombre',)
    
    # Añadir campos de saldo calculado
    def saldo_condominio(self, obj):
        return MovimientoFinanciero.calcular_saldo_condominio(tower=obj)
    saldo_condominio.short_description = 'Saldo Condominio'

    def saldo_basura(self, obj):
        return MovimientoFinanciero.calcular_saldo_basura(tower=obj)
    saldo_basura.short_description = 'Saldo Basura'
    
# ----------------------------------------------------
# Administrador para MovimientoFinanciero
# ----------------------------------------------------
class AdministradorMovimientoFinanciero(admin.ModelAdmin):
    list_display = ('fecha', 'descripcion', 'tipo', 'categoria', 'monto_total', 'tower', 'creado_por')
    list_filter = ('tipo', 'categoria', 'tower', 'creado_por')
    search_fields = ('descripcion',)
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)
    
    # Añadir una función para mostrar el monto total (suma de condominio y basura)
    def monto_total(self, obj):
        return obj.monto_condominio + obj.monto_basura
    monto_total.short_description = 'Monto Total'
    
    # Personalizar el formulario de edición/creación
    fieldsets = (
        (None, {'fields': ('fecha', 'descripcion', 'tipo', 'categoria', 'tower', 'creado_por')}),
        ('Montos', {'fields': ('monto_condominio', 'monto_basura')}),
    )
    
    # Auto-llenar el campo 'creado_por' con el usuario actual
    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


# Registro de modelos en el administrador de Django
admin.site.register(CustomUser, AdministradorUsuario)
admin.site.register(Tower, AdministradorTower)
admin.site.register(MovimientoFinanciero, AdministradorMovimientoFinanciero)