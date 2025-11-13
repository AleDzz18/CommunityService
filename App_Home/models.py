# App_Home/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.db.models import Sum # Necesario para la función de saldo
from django.db.utils import OperationalError # Importación clave para manejar el error

# Modelo para las 24 Torres
class Tower(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre de la Torre')
    
    def __str__(self):
        return self.nombre  # Ejemplo: 'T01'
    
    class Meta:
        verbose_name = "Torre"
        verbose_name_plural = "Torres"
        ordering = ['nombre'] # Ordenar alfabéticamente

class MovimientoFinancieroManager(models.Manager):
    def calcular_saldo_torre(self, tower, categoria):
        """Calcula el saldo actual para una torre y categoría específica."""
        
        # Determina el campo de monto a usar basado en la categoría
        monto_field = 'monto_condominio' if categoria == 'CON' else 'monto_basura'
        
        # Filtra por torre y categoría
        qs = self.filter(
            tower=tower, 
            categoria=categoria
        )

        # Suma los ingresos
        ingresos = qs.filter(tipo='ING').aggregate(total=Sum(monto_field))['total'] or 0.0
        
        # Suma los egresos
        egresos = qs.filter(tipo='EGR').aggregate(total=Sum(monto_field))['total'] or 0.0

        return ingresos - egresos

# --- MODELO AÑADIDO: MOVIMIENTO FINANCIERO ---
class MovimientoFinanciero(models.Model):

    objects = MovimientoFinancieroManager()  # Asignar el Manager personalizado
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
    monto_condominio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Monto Condominio')
    monto_basura = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Monto Basura')
    
    tipo = models.CharField(max_length=3, choices=TIPOS, verbose_name='Tipo de Movimiento')
    categoria = models.CharField(max_length=3, choices=CATEGORIAS, verbose_name='Categoría')
    
    # Relación con la Torre (Si es un ingreso/egreso de una torre específica)
    tower = models.ForeignKey(Tower, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Torre Asociada')
    
    creado_por = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Registrado por')

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.get_categoria_display()} ({self.fecha})"
    
    class Meta:
        verbose_name = "Movimiento Financiero"
        verbose_name_plural = "Movimientos Financieros"
        ordering = ['-fecha', '-id']

    @staticmethod
    def calcular_saldo_condominio(tower=None):
        """Calcula el saldo total de Condominio, opcionalmente filtrado por Torre."""
        qs = MovimientoFinanciero.objects.filter(categoria='CON')
        if tower:
            qs = qs.filter(tower=tower)

        ingresos = qs.filter(tipo='ING').aggregate(total=Sum('monto_condominio'))['total'] or 0
        egresos = qs.filter(tipo='EGR').aggregate(total=Sum('monto_condominio'))['total'] or 0
        return ingresos - egresos

    @staticmethod
    def calcular_saldo_basura(tower=None):
        """Calcula el saldo total de Basura, opcionalmente filtrado por Torre."""
        qs = MovimientoFinanciero.objects.filter(categoria='BAS')
        if tower:
            qs = qs.filter(tower=tower)

        ingresos = qs.filter(tipo='ING').aggregate(total=Sum('monto_basura'))['total'] or 0
        egresos = qs.filter(tipo='EGR').aggregate(total=Sum('monto_basura'))['total'] or 0
        return ingresos - egresos


# --- MODELO PRINCIPAL: USUARIO PERSONALIZADO ---
class CustomUser(AbstractUser):
    
    # OPCIONES DE ROL
    ROL_LIDER_TORRE = 'LDT'
    ROL_LIDER_GENERAL = 'LDG'
    
    ROLES = [
        (ROL_LIDER_TORRE, 'Líder de Torre'),
        (ROL_LIDER_GENERAL, 'Líder General'),
    ]

    # CAMPOS PERSONALIZADOS
    cedula = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name='Cédula de Identidad')
    rol = models.CharField(max_length=3, choices=ROLES, default=ROL_LIDER_TORRE, verbose_name='Rol en la Comunidad')
    tower = models.ForeignKey(Tower, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Torre Asignada')
    apartamento = models.CharField(max_length=10, null=True, blank=True, verbose_name='Apartamento (Ej: P1-A)')

    # Campos de Roles Secundarios (Permisos)
    es_admin_basura = models.BooleanField(default=False, verbose_name='Administrador de Cuarto de Basura')
    es_admin_clap = models.BooleanField(default=False, verbose_name='Administrador de Bolsas CLAP')
    es_admin_bombonas = models.BooleanField(default=False, verbose_name='Administrador de Bombonas')
    
    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Usuario Personalizado"
        verbose_name_plural = "Usuarios Personalizados"

# ----------------------------------------------------
# SEÑAL PARA CREAR TORRES INICIALES (CORREGIDA)
# ----------------------------------------------------
@receiver(post_migrate)
def crear_torres_iniciales(sender, apps, **kwargs): # Añadimos 'apps' como argumento
    # Asegurarse de que el código se ejecute solo para esta aplicación
    if sender.name == 'App_Home':
        print("Verificando la creación de Torres iniciales (T01 a T24)...")
        
        # Obtenemos el modelo de Tower del estado actual de la BD
        try:
            Tower = apps.get_model('App_Home', 'Tower')
        except LookupError:
            return

        # Generar los nombres de las 24 torres (T01 a T24)
        nombres_torres = [f"T{i:02d}" for i in range(1, 25)]
        
        try:
            # Lógica de creación de torres, envuelta en try-except
            torres_existentes = Tower.objects.values_list('nombre', flat=True)
            torres_a_crear = []
            
            for nombre in nombres_torres:
                if nombre not in torres_existentes:
                    torres_a_crear.append(Tower(nombre=nombre))
            
            if torres_a_crear:
                Tower.objects.bulk_create(torres_a_crear)
                print(f"Se crearon {len(torres_a_crear)} torres faltantes.")
            else:
                print("Todas las torres ya existen.")
        
        except OperationalError as e:
            # Capturamos el error específico de tabla no existente y salimos limpiamente
            if 'no such table' in str(e):
                print(f"ADVERTENCIA: La tabla 'App_Home_tower' aún no existe. La creación de torres se pospone hasta que se complete la migración.")
            else:
                raise e # Re-lanzar cualquier otro error
        except Exception as e:
            # Capturamos otros posibles errores de Django
            if 'no such table' in str(e):
                print(f"ADVERTENCIA: La tabla 'App_Home_tower' aún no existe. La creación de torres se pospone hasta que se complete la migración.")
            else:
                raise e