# App_Home/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.db.models import Sum # Necesario para la función de saldo
from django.db.utils import OperationalError # Importación clave para manejar el error
from decimal import Decimal
from datetime import date

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
        ingresos = qs.filter(tipo='ING').aggregate(total=Sum(monto_field))['total'] or Decimal('0.00')
        
        # Suma los egresos
        egresos = qs.filter(tipo='EGR').aggregate(total=Sum(monto_field))['total'] or Decimal('0.00')

        return ingresos - egresos
    
    def calcular_saldo_general_basura(self):
        """Calcula el saldo total de la categoría 'BASURA' (BAS) de TODAS las torres."""
        
        # El campo de monto a usar para la categoría Basura es 'monto_basura'
        monto_field = 'monto_basura'
        
        # Filtra solo por la categoría de Basura (BAS) de todas las torres
        qs = self.filter(categoria='BAS')

        # Suma los ingresos
        ingresos = qs.filter(tipo='ING').aggregate(total=Sum(monto_field))['total'] or Decimal(0)
        
        # Suma los egresos
        egresos = qs.filter(tipo='EGR').aggregate(total=Sum(monto_field))['total'] or Decimal(0)
        
        # Retorna el saldo total de la categoría 'BAS'
        return ingresos - egresos

# --- MOVIMIENTO FINANCIERO ---
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
    
    tasa_bcv = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name='Tasa BCV (Bs/USD)',
        # Se elimina null=True y blank=True para hacerlo obligatorio
        null=False, 
        blank=False,
        help_text="Tasa de referencia del BCV del día en que se realizó el movimiento."
    )

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

class CensoMiembro(models.Model):
    GENEROS = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    
    # Opciones para Apartamentos (3 Pisos, 4 Letras)
    PISOS = [('P1', 'Piso 1'), ('P2', 'Piso 2'), ('P3', 'Piso 3')]
    LETRAS = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]

    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    cedula = models.CharField(max_length=15, unique=True, verbose_name='Cédula')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de Nacimiento')
    genero = models.CharField(max_length=1, choices=GENEROS, verbose_name='Género')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    
    # Ubicación
    tower = models.ForeignKey(Tower, on_delete=models.CASCADE, verbose_name='Torre')
    piso = models.CharField(max_length=2, choices=PISOS, verbose_name='Piso')
    apartamento_letra = models.CharField(max_length=1, choices=LETRAS, verbose_name='Letra Apto')
    
    es_jefe_familia = models.BooleanField(default=False, verbose_name='¿Es Jefe de Familia?')

    @property
    def edad(self):
        today = date.today()
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))

    @property
    def apartamento_completo(self):
        return f"{self.piso}-{self.apartamento_letra}"

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.tower} - {self.apartamento_completo})"

    class Meta:
        verbose_name = "Miembro del Censo"
        verbose_name_plural = "Miembros del Censo"
        # Ordenar por Torre, luego Piso, luego Letra
        ordering = ['tower', 'piso', 'apartamento_letra']

class CicloBeneficio(models.Model):
    TIPOS = [
        ('CLAP', 'Bolsa CLAP'),
        ('GAS', 'Bombona de Gas'),
    ]

    tipo = models.CharField(max_length=4, choices=TIPOS, verbose_name='Tipo de Beneficio')
    nombre = models.CharField(max_length=50, verbose_name='Nombre del Ciclo (Ej: Noviembre 2024)')
    fecha_apertura = models.DateField(auto_now_add=True, verbose_name='Fecha de Apertura')
    activo = models.BooleanField(default=True, verbose_name='¿Ciclo Activo?')

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

    class Meta:
        verbose_name = "Ciclo de Beneficio"
        verbose_name_plural = "Ciclos de Beneficios"
        ordering = ['-fecha_apertura']

class EntregaBeneficio(models.Model):
    ciclo = models.ForeignKey(CicloBeneficio, on_delete=models.CASCADE, related_name='entregas')
    beneficiario = models.ForeignKey(CensoMiembro, on_delete=models.CASCADE, verbose_name='Vecino Beneficiado')
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    
    # Opcional: Para saber quién lo agregó a la lista
    agregado_por = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Beneficiario en Lista"
        verbose_name_plural = "Beneficiarios en Lista"
        unique_together = ('ciclo', 'beneficiario') # Evita duplicados en la misma lista

    def __str__(self):
        return f"{self.beneficiario} - {self.ciclo}"
    

# --- NUEVO MODELO: SOLICITUDES DE DOCUMENTOS ---
class SolicitudDocumento(models.Model):
    TIPOS = [
        ('CARTA_CONDUCTA', 'Carta de Buena Conducta'),
        # Aquí agregaremos los otros tipos (Mudanza, etc.) luego
    ]
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESADO', 'Procesado'),
    ]

    # Vinculamos con el Censo para sacar datos automáticos
    beneficiario = models.ForeignKey(CensoMiembro, on_delete=models.CASCADE, verbose_name='Vecino Solicitante')
    
    tipo = models.CharField(max_length=20, choices=TIPOS, default='CARTA_CONDUCTA', verbose_name='Tipo de Documento')
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE', verbose_name='Estado')
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name='Fecha Solicitud')
    
    # -- Campos específicos para Carta de Buena Conducta (Se llenan al procesar) --
    anios_residencia = models.CharField(max_length=50, blank=True, null=True, verbose_name='Años de Residencia')

    # Auditoría
    procesado_por = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Procesado por')
    fecha_proceso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.beneficiario.cedula}"

    class Meta:
        verbose_name = "Solicitud de Documento"
        verbose_name_plural = "Solicitudes de Documentos"
        ordering = ['-fecha_solicitud']