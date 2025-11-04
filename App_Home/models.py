from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_migrate
from django.dispatch import receiver

# Create your models here.

# Modelo para las 24 Torres
class Tower(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre de la Torre')
    
    def __str__(self):
        return self.nombre  # Ejemplo: 'T01'
    
    class Meta:
        verbose_name = "Torre"
        verbose_name_plural = "Torres"
        ordering = ['nombre'] # Ordenar alfabéticamente

# Modelo de Usuario Personalizado para manejar los roles
class CustomUser(AbstractUser):
    # Definición de Roles Primarios
    # NOTA: Los Usuarios Básicos (espectadores) NO están registrados.
    ROL_LIDER_TORRE = 2
    ROL_LIDER_GENERAL = 3

    OPCIONES_ROLES = (
        (ROL_LIDER_TORRE, 'Líder de Torre'),
        (ROL_LIDER_GENERAL, 'Líder General'),
    )

    # Campo de Rol Primario
    rol = models.PositiveSmallIntegerField(
        choices=OPCIONES_ROLES, 
        default=ROL_LIDER_TORRE, 
        verbose_name='Rol Principal'
    )

    # Asignación de Torre (One-to-One: solo un Líder por Torre)
    torre = models.OneToOneField(
        Tower, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Torre Asignada'
    )

    # Roles Secundarios (Permisos)
    es_admin_basura = models.BooleanField(default=False, verbose_name='Administrador de Cuarto de Basura')
    es_admin_clap = models.BooleanField(default=False, verbose_name='Administrador de Bolsas CLAP')
    es_admin_bombonas = models.BooleanField(default=False, verbose_name='Administrador de Bombonas')
    
    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Usuario Personalizado"
        verbose_name_plural = "Usuarios Personalizados"

# Función para inicializar las 24 torres (T01 a T24) automáticamente
@receiver(post_migrate)
def crear_torres_iniciales(sender, **kwargs):
    # Asegurarse de que el código se ejecute solo para esta aplicación
    if sender.name == 'App_Home':
        print("Verificando la creación de Torres iniciales (T01 a T24)...")
        
        # Generar los nombres de las 24 torres (T01, T02, ..., T24)
        nombres_torres = [f"T{i:02d}" for i in range(1, 25)]
        
        torres_existentes = Tower.objects.values_list('nombre', flat=True)
        torres_a_crear = []
        
        for nombre in nombres_torres:
            if nombre not in torres_existentes:
                torres_a_crear.append(Tower(nombre=nombre))
        
        if torres_a_crear:
            Tower.objects.bulk_create(torres_a_crear)
            print(f"Se crearon {len(torres_a_crear)} torres faltantes.")
        else:
            print("Todas las 24 torres ya existen en la base de datos.")