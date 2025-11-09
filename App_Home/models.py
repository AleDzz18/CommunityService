# App_Home/models.py

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

# --- MODELO AÑADIDO: MOVIMIENTO FINANCIERO ---
class MovimientoFinanciero(models.Model):
    # Opciones de Categoría: Condominio General o Cuarto de Basura
    CATEGORIAS = [
        ('CON', 'Condominio'),
        ('BAS', 'Cuarto de Basura'),
    ]
    # Opciones de Tipo: Ingreso o Egreso
    TIPOS = [
        ('ING', 'Ingreso'),
        ('EGR', 'Egreso'),
    ]

    fecha = models.DateField(verbose_name='Fecha del Movimiento')
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    
    # Campos separados para mejor manejo en consultas
    ingreso = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Monto Ingreso')
    egreso = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Monto Egreso')
    
    tipo = models.CharField(max_length=3, choices=TIPOS, verbose_name='Tipo')
    categoria = models.CharField(max_length=3, choices=CATEGORIAS, verbose_name='Categoría')
    
    # Relación con la Torre (Puede ser NULL si es un movimiento general, ej. Egreso de Basura Global)
    torre = models.ForeignKey(Tower, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Torre Asociada')
    
    # Campo para registrar qué usuario (Líder) lo creó (será útil en fases posteriores)
    # creador = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Registrado por')
    
    class Meta:
        verbose_name = "Movimiento Financiero"
        verbose_name_plural = "Movimientos Financieros"
        ordering = ['fecha', 'id'] # Ordenar por fecha y luego por ID para mantener el orden de registro

    def __str__(self):
        return f"[{self.get_categoria_display()}] {self.get_tipo_display()} - {self.descripcion} ({self.fecha})"
# --------------------------------------------------------

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

    # Asignación de Torre (Para Líderes)
    torre = models.ForeignKey(
        Tower, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Torre Asignada'
    )

    # Datos adicionales
    cedula = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name='Cédula de Identidad')
    # Ejemplo de formato: T01-P1-A
    apartamento = models.CharField(max_length=10, null=True, blank=True, verbose_name='Ubicación de Apartamento')

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
            print(f"Se crearon {len(torres_a_crear)} torres nuevas.")
        else:
            print("Todas las torres (T01 a T24) ya existen.")