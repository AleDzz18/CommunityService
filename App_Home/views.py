# App_Home/views.py

import calendar
import json
import random
import string
from Community_Service.decorators import complete_profile
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login as autenticar_login, logout
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from .forms import (
    FormularioCreacionUsuario,
    FormularioPerfilUsuario,
    FormularioFiltroMovimientos,
    SolicitudDocumentoForm,
    VerifyResetCodeForm,
    CustomPasswordResetForm,
)
from .models import (
    CustomUser,
    Tower,
    MovimientoFinanciero,
    CicloBeneficio,
    EntregaBeneficio,
    CensoMiembro,
    SolicitudDocumento,
    PasswordResetCode,
    ReportePublicado,
)

@complete_profile
def vista_index(request):
    contexto = {
        "usuario_autenticado": request.user.is_authenticated,
        "rol_usuario": (
            getattr(request.user, "rol", None)
            if request.user.is_authenticated
            else None
        ),
        "torre_asignada": (
            getattr(request.user, "torre", None)
            if request.user.is_authenticated
            else None
        ),
    }
    return render(request, "index.html", contexto)


@complete_profile
def vista_login(request):
    """Maneja la autenticación del usuario."""

    # Si el usuario ya está autenticado, simplemente se redirige.
    if request.user.is_authenticated:
        return redirect("url_index")

    if request.method == "POST":
        formulario = AuthenticationForm(request, data=request.POST)
        if formulario.is_valid():
            username = formulario.cleaned_data.get("username")
            password = formulario.cleaned_data.get("password")
            usuario = authenticate(username=username, password=password)
            if usuario is not None:
                # 🔑 MODIFICACIÓN AQUÍ: Usar 'cedula' para forzar la redirección a completar perfil,
                # en lugar de 'is_active', si el login fue exitoso.
                # Si todo está completo, inicia sesión y redirige al dashboard
                # ALEJANDRO, PRIMERO LOGEA AL USUARIO ANTES DE REDIRIGIRLO CABRON, SINO COMO ESPERAS
                # QUE CARGUE LA PAGINA DE COMPLETAR PERFIL
                autenticar_login(request, usuario)
                if not getattr(usuario, "cedula", None):
                    messages.warning(
                        request,
                        "Su perfil está incompleto. Por favor, complete sus datos.",
                    )
                    return redirect("url_completar_perfil", user_id=usuario.id)

                return redirect("url_index")
            else:
                messages.error(request, "Nombre de usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Error en la forma de autenticación.")

    formulario = AuthenticationForm()

    # Obtener mensajes existentes para mostrarlos
    storage = get_messages(request)

    return render(
        request, "pages/login.html", {"formulario": formulario, "messages": storage}
    )


@login_required
def vista_logout(request):
    """
    Cierra la sesión del usuario y redirige al dashboard en modo espectador.
    """
    logout(request)
    return redirect("url_index")


@complete_profile
def vista_registro(request):
    """Maneja la creación de nuevos usuarios."""
    if request.user.is_authenticated:
        return redirect("url_index")

    if request.method == "POST":
        formulario = FormularioCreacionUsuario(request.POST)
        if formulario.is_valid():
            usuario = formulario.save(commit=False)
            usuario.save()

            autenticar_login(request, usuario)

            messages.success(
                request,
                f"Cuenta creada exitosamente para {usuario.username}. Por favor, complete su perfil.",
            )

            # Éxito: Redirigir directamente al perfil para evitar el bucle inicial del dashboard.
            return redirect("url_completar_perfil", user_id=usuario.id)
        else:
            # Fallo: Mostrar errores de validación del formulario de registro y redirigir al login
            for field, errors in formulario.errors.items():
                for error in errors:
                    field_name = (
                        formulario.fields.get(field).label
                        if field in formulario.fields
                        and formulario.fields.get(field).label
                        else field
                    )
                    messages.error(request, f"Error en {field_name}: {error}")

    formulario = FormularioCreacionUsuario()
    contexto = {"formulario": formulario, "vue": json.dumps({"register": True})}
    return render(request, "pages/login.html", contexto)


@login_required
def vista_completar_perfil(request, user_id):
    """
    Permite a un nuevo usuario (Líder) completar sus datos de perfil (Torre, Cédula, etc.)
    y activar su cuenta.
    """
    usuario = get_object_or_404(CustomUser, pk=user_id)

    # Asegurar que solo el propio usuario pueda completar su perfil
    if request.user.id != usuario.id:
        messages.error(
            request, "No tiene permisos para editar el perfil de otro usuario."
        )
        return redirect("url_index")

    # Si el usuario tiene Cédula (perfil completo), lo redirigimos
    if getattr(usuario, "cedula", None):
        messages.info(request, "Su perfil ya está completo.")
        return redirect("url_index")

    if request.method == "POST":
        formulario = FormularioPerfilUsuario(request.POST, instance=usuario)
        if formulario.is_valid():
            formulario.save()

            messages.success(
                request, "Perfil completado con éxito. ¡Bienvenido a la comunidad!"
            )
            return redirect("url_index")
        else:
            messages.error(
                request,
                "El formulario contiene errores. Por favor, corrígelos a continuación:",
            )

            # Iterar sobre todos los errores del formulario (incluidos los globales bajo el key '__all__')
            for field, errors in formulario.errors.items():
                for error in errors:
                    if field == "__all__":
                        messages.error(request, f"{error}")
                    else:
                        field_name = (
                            formulario.fields.get(field).label
                            if field in formulario.fields
                            else field
                        )
                        messages.error(request, f"Error en {field_name}: {error}")

    else:
        formulario = FormularioPerfilUsuario(instance=usuario)

    return render(
        request,
        "pages/completar_perfil.html",
        {"formulario": formulario, "usuario": usuario},
    )


def cancelar_registro(request, user_id):
    """
    Elimina el usuario creado parcialmente si decide cancelar
    en la pantalla de completar perfil.
    """
    try:
        # Buscamos el usuario por su ID
        usuario = get_object_or_404(CustomUser, pk=user_id)

        # Eliminamos el usuario de la base de datos
        usuario.delete()

        # Mensaje de retroalimentación
        messages.info(
            request, "El registro ha sido cancelado y los datos temporales eliminados."
        )

    except Exception as e:
        messages.error(request, "Ocurrió un error al intentar cancelar el registro.")

    # Redirigimos al Login
    return redirect("url_login")


# ------------------------------------------------------------------
# --- ADMINISTRACIÓN DE INGRESOS Y EGRESOS (USUARIO BÁSICO) ---
# ------------------------------------------------------------------

@complete_profile
def vista_reportes_publicos(request, categoria_slug):
    slug = categoria_slug.lower()
    mapa_categorias = {'basura': 'BAS', 'condominio': 'CON'}
    
    if slug not in mapa_categorias:
        return redirect('url_index')
    
    categoria_db = mapa_categorias[slug]

    # 1. CAPTURAR DATOS DEL FILTRO (Vienen del formulario en el HTML)
    f_torre = request.GET.get('torre')
    f_mes = request.GET.get('mes')
    f_anio = request.GET.get('anio')
    
    # 2. LÓGICA DE PERMISOS (Tu lógica original se mantiene)
    es_lider = False
    if request.user.is_authenticated:
        rol = getattr(request.user, 'rol', None)
        if request.user.is_staff or rol in ['LDG', 'LDT']:
            es_lider = True
        if slug == 'basura' and getattr(request.user, 'es_admin_basura', False):
            es_lider = True

    # 3. FILTRADO DINÁMICO
    reportes = ReportePublicado.objects.filter(categoria=categoria_db)

    if f_torre and f_torre != '0':
        if f_torre == 'general':
            reportes = reportes.filter(tower__isnull=True)
        else:
            reportes = reportes.filter(tower_id=f_torre)
    
    if f_mes and f_mes != '0':
        reportes = reportes.filter(mes=f_mes)
        
    if f_anio and f_anio != '0':
        reportes = reportes.filter(anio=f_anio)

    # 4. DATOS PARA LOS SELECTS (Para que aparezcan las torres, meses y años en el filtro)
    context = {
        'titulo': f"Reportes de {'Cuarto de Basura' if categoria_db == 'BAS' else 'Condominio'}",
        'reportes': reportes.order_by('-anio', '-mes'),
        'categoria_slug': slug,
        'es_lider': es_lider,
        
        # Listados para llenar los select
        'towers': Tower.objects.all(),
        'anios_disponibles': range(2022, datetime.now().year + 1), # Ajusta el año de inicio
        'meses_listado': [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ],
        
        # Mantener los valores seleccionados en el filtro después de cargar
        'f_torre': f_torre,
        'f_mes': f_mes,
        'f_anio': f_anio,
    }

    return render(request, "pages/finanzas/reportes_vecinos.html", context)

@complete_profile
def ver_ingresos_egresos(request, categoria_slug):
    """
    Vista de gestión para Líderes y Staff: Manejo detallado de ingresos y egresos.
    Permite registrar movimientos, ver el saldo acumulado y aplicar filtros.
    """
    # --- CAMBIO 1: SEGURIDAD DE ACCESO (NUEVO) ---
    # Solo líderes o staff pueden entrar a esta vista de gestión.
    if not request.user.is_authenticated:
        return redirect('ver_finanzas', categoria_slug=categoria_slug)
        
    es_autorizado = (
        request.user.rol in ['LDG', 'LDT'] or 
        request.user.es_admin_basura or 
        request.user.is_staff
    )
    
    if not es_autorizado:
        messages.warning(request, "No tienes permisos para acceder al panel de gestión.")
        return redirect('ver_finanzas', categoria_slug=categoria_slug)
    # ---------------------------------------------

    if categoria_slug == "condominio":
        categoria_filtro = "CON"
        titulo = "Gestión Detallada - Condominio" # Título más descriptivo
        monto_field = "monto_condominio"
    elif categoria_slug == "basura":
        categoria_filtro = "BAS"
        titulo = "Gestión Detallada - Cuarto de Basura"
        monto_field = "monto_basura"
    else:
        return redirect("url_index")

    # =========================================================================
    # LÓGICA DE MANEJO DE POST (REGISTRO DE MOVIMIENTO)
    # Resuelve: 1. Saldo Negativo, 2. Restricción por Torre, 3. Registro/Redirección
    # =========================================================================
    if request.method == "POST":
        # 1. Validar y Obtener datos del formulario POST
        try:
            fecha = request.POST["fecha"]
            descripcion = request.POST["descripcion"]
            tipo = request.POST["tipo"]  # 'ING' o 'EGR'

            # --- AGREGADO: Extraer Tasa BCV ---
            tasa_bcv = Decimal(request.POST["tasa_bcv"])  # Usar Decimal para precisión
            if tasa_bcv <= 0:
                raise ValueError("La Tasa BCV debe ser un valor positivo.")
            # ----------------------------------

            # Asegurar que el monto es un número positivo
            monto = float(request.POST["monto"])
            if monto <= 0:
                raise ValueError("El monto debe ser una cantidad positiva.")

        except (KeyError, ValueError) as e:
            # Mensaje de error mejorado para el formulario
            messages.error(
                request,
                f"Error en los datos del movimiento. Verifique la fecha, descripción, tipo y monto. Detalle: {e}.",
            )
            return redirect("ver_finanzas_gestion", categoria_slug=categoria_slug)

        # 2. Validación de permisos para registrar (POST)
        if request.user.rol not in ["LDT", "LDG"] and not request.user.is_staff:
            messages.error(request, "No tienes permisos para registrar movimientos.")
            return redirect("ver_finanzas_gestion", categoria_slug=categoria_slug)

        # Determinar a qué torre asignar el movimiento
        if request.user.rol == "LDT":
            if not request.user.tower:
                messages.error(request, "Error: No tienes torre asignada.")
                return redirect("ver_finanzas_gestion", categoria_slug=categoria_slug)
            torre_asignada = request.user.tower
        else:
            # Si es LDG o Staff, debe venir una torre del formulario (o podrías asignar una por defecto)
            torre_form_id = request.POST.get("torre_id")
            torre_asignada = get_object_or_404(Tower, id=torre_form_id) if torre_form_id else None

        # 3. **Prevenir Saldo Negativo (Problema 1 - REFORZADO)**
        if tipo == "EGR":
            # Usa el Manager para calcular el saldo de la categoría correcta
            saldo_actual = MovimientoFinanciero.objects.calcular_saldo_torre(
                tower=torre_asignada, categoria=categoria_filtro
            )

            # VALIDACIÓN CRÍTICA:
            if saldo_actual - monto < 0:
                messages.error(
                    request,
                    f"Operación denegada. Saldo insuficiente para este egreso. Saldo actual: Bs. {saldo_actual:.2f}",
                )
                return redirect(
                    "ver_finanzas_gestion", categoria_slug=categoria_slug
                )  # Redirección a la página actual

        # 4. Crear la instancia del Movimiento (aún sin guardar en DB)
        movimiento = MovimientoFinanciero(
            fecha=fecha,
            descripcion=descripcion,
            tasa_bcv=tasa_bcv,
            tipo=tipo,
            categoria=categoria_filtro,
            creado_por=request.user,
            tower=torre_asignada,
        )

        # 5. **Asignar el Monto Correcto (Problema 2 - Registro de Basura)**
        # Se asigna el monto al campo correspondiente a la categoría.
        if categoria_filtro == "CON":
            movimiento.monto_condominio = monto
            movimiento.monto_basura = 0.00
        else:  # categoria_filtro == 'BAS'
            movimiento.monto_basura = monto
            movimiento.monto_condominio = 0.00

        # 6. Guardar la instancia (Una sola vez)
        try:
            movimiento.save()
            messages.success(
                request,
                f"Movimiento de {movimiento.get_tipo_display()} registrado con éxito en {movimiento.get_categoria_display()}.",
            )
        except Exception as e:
            # Capturar cualquier error inesperado de DB o modelo
            messages.error(
                request,
                f"Error inesperado al guardar el movimiento. Por favor, intente de nuevo. Detalle: {e}",
            )

        # **Redirección Correcta (Problema 2 - Redirección)**
        # Redirecciona a la página con el slug correcto ('condominio' o 'basura')
        return redirect("ver_finanzas_gestion", categoria_slug=categoria_slug)

    # =========================================================================
    # LÓGICA DE MANEJO DE GET (LISTADO Y FILTROS)
    # =========================================================================

    # 2. Obtener opciones de filtro (Todas las Torres)
    torres = Tower.objects.all().order_by("nombre")

    # 3. Aplicar filtros iniciales y ordenar
    # --- Usar select_related('tower') para optimizar la consulta y cargar el objeto 'tower' ---
    movimientos_query = (
        MovimientoFinanciero.objects.filter(categoria=categoria_filtro)
        .select_related("tower")
        .order_by("fecha", "id")
    )

    # Filtro por tipo (Ingreso, Egreso, Ambos)
    tipo_filtro = request.GET.get("tipo", "AMBOS")
    if tipo_filtro == "INGRESOS":
        movimientos_query = movimientos_query.filter(tipo="ING")
    elif tipo_filtro == "EGRESOS":
        movimientos_query = movimientos_query.filter(tipo="EGR")

    # Filtro por torre
    es_solo_ldt = request.user.rol == 'LDT' and not (request.user.rol == 'LDG' or request.user.is_staff)

    if es_solo_ldt:
        # Forzamos que el LDT solo vea su torre asignada
        if request.user.tower:
            movimientos_query = movimientos_query.filter(tower=request.user.tower)
            torre_id = str(request.user.tower.id)
            # Opcional: Filtrar la lista de torres para que el select solo muestre la suya
            torres = Tower.objects.filter(id=request.user.tower.id)
        else:
            messages.error(request, "No tienes una torre asignada. Contacta al administrador.")
            movimientos_query = MovimientoFinanciero.objects.none()
            torre_id = "0"
    else:
        # Lógica para Administradores y Líderes Generales
        torre_id = request.GET.get("torre")
        if torre_id is None or torre_id == "0":
            torre_id = "0" # Ver todas (o lo que desees por defecto)
        elif torre_id.isdigit():
            movimientos_query = movimientos_query.filter(tower__id=int(torre_id))

    # -----------------------------------------------------------
    # AÑADIR NUEVO FILTRO POR RANGO DE FECHAS
    # -----------------------------------------------------------
    filtro_form = FormularioFiltroMovimientos(request.GET)

    if filtro_form.is_valid():
        fecha_inicio = filtro_form.cleaned_data.get("fecha_inicio")
        fecha_fin = filtro_form.cleaned_data.get("fecha_fin")

        if fecha_inicio:
            # Filtrar movimientos donde la fecha es MAYOR O IGUAL a la fecha de inicio
            movimientos_query = movimientos_query.filter(fecha__gte=fecha_inicio)

        if fecha_fin:
            # Filtrar movimientos donde la fecha es MENOR O IGUAL a la fecha de fin
            movimientos_query = movimientos_query.filter(fecha__lte=fecha_fin)

    # 4. Cálculo del Saldo Acumulado
    movimientos_con_saldo = []
    saldo_acumulado = 0

    for mov in movimientos_query:
        # --- Obtener el monto correcto del objeto ---
        monto = getattr(mov, monto_field)

        # Inicializar ingreso/egreso para el diccionario final
        ingreso_monto = None
        egreso_monto = None

        # Sumar o restar al saldo acumulado
        if mov.tipo == "ING":
            saldo_acumulado += monto
            ingreso_monto = monto
        elif mov.tipo == "EGR":  # EGR
            saldo_acumulado -= monto
            egreso_monto = monto

        # --- Manejar el AttributeError para 'tower' ---
        # 1. Comprueba si el atributo 'tower' existe en el objeto (hasattr).
        # 2. Si existe y tiene un valor (es decir, no es None), usa el nombre de la torre.
        # 3. Si no existe o es None, usa 'General'.
        if hasattr(mov, "tower") and mov.tower:
            nombre_torre = mov.tower.nombre
        else:
            nombre_torre = "General"

        # Preparar los datos para la plantilla
        movimientos_con_saldo.append(
            {
                "id": mov.id,
                "tower": mov.tower,
                "fecha": mov.fecha,
                "descripcion": mov.descripcion,
                "tasa_bcv": round(mov.tasa_bcv, 2),
                "ingreso": (
                    ingreso_monto if ingreso_monto and ingreso_monto > 0 else None
                ),
                "egreso": egreso_monto if egreso_monto and egreso_monto > 0 else None,
                "torre": nombre_torre,
                "saldo": round(saldo_acumulado, 2),  # Redondear a dos decimales
                "tipo": mov.tipo,
                "categoria": mov.categoria,
            }
        )

    anio_actual = datetime.now().year
    context = {
        "titulo": titulo,
        "movimientos": movimientos_con_saldo,
        "torres": torres,
        "tipo_seleccionado": tipo_filtro,
        "torre_seleccionada_id": torre_id,
        "categoria_slug": categoria_slug,  # Para el botón de descarga
        "filtro_form": filtro_form,  # Formulario de filtro para la plantilla
        "es_gestion": True, # Para mostrar botones de edición/borrado en el HTML
        "anios_disponibles": range(anio_actual - 5, anio_actual + 1), # Para el modal de publicación
        "meses_listado": [
            (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
            (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
            (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre")
        ],
    }

    return render(request, "pages/finanzas/listado_movimientos.html", context)

@login_required
def publicar_reporte_mensual(request):
    if request.method == "POST":
        # Aseguramos el slug en minúsculas para que el mapa no falle
        categoria_raw = request.POST.get('categoria_slug', 'condominio')
        categoria_slug = categoria_raw.lower()
        
        try:
            # 1. Validar datos numéricos
            mes = int(request.POST.get('mes'))
            anio = int(request.POST.get('anio'))
            tower_id = request.POST.get('tower_id')

            # 2. Mapeo seguro
            mapa = {'basura': 'BAS', 'condominio': 'CON'}
            cat_db = mapa.get(categoria_slug)
            
            if not cat_db:
                raise ValueError(f"Categoría '{categoria_slug}' no es válida.")

            # 3. Lógica de Torre robusta
            torre_reporte = None
            if request.user.rol == 'LDT':
                torre_reporte = request.user.tower
            elif tower_id and str(tower_id) != '0':
                # Intentamos buscar la torre, si no existe, dará error controlado
                torre_reporte = Tower.objects.filter(id=tower_id).first()

            # 4. Guardado con update_or_create
            # IMPORTANTE: Si tower es None, se guarda como reporte General
            reporte, created = ReportePublicado.objects.update_or_create(
                mes=mes, 
                anio=anio, 
                categoria=cat_db, 
                tower=torre_reporte,
                defaults={'publicado_por': request.user}
            )
            
            messages.success(request, f"Reporte de {reporte.get_mes_display()} {anio} publicado con éxito.")
            return redirect('ver_finanzas', categoria_slug=categoria_slug)

        except Exception as e:
            # Imprimimos en consola para que tú lo veas mientras programas
            print(f"ERROR AL PUBLICAR: {str(e)}") 
            messages.error(request, f"Error técnico: {str(e)}")
            return redirect('ver_finanzas_gestion', categoria_slug=categoria_slug)
    
    return redirect('url_index')

def eliminar_reporte(request, reporte_id):
    if not request.user.is_authenticated:
        return redirect('url_login')

    try:
        reporte = ReportePublicado.objects.get(id=reporte_id)
        categoria_slug = "condominio" if reporte.categoria == "CON" else "basura"
        
        # 1. Variables de rol básicas
        rol = getattr(request.user, 'rol', None)
        es_ldg_o_staff = request.user.is_staff or rol == 'LDG'
        permiso_concedido = False

        # 2. Lógica diferenciada por categoría
        if reporte.categoria == "BAS":
            # REGLA BASURA: Solo Lideres Generales/Staff o Administradores de Basura
            es_admin_basura = getattr(request.user, 'es_admin_basura', False)
            if es_ldg_o_staff or es_admin_basura:
                permiso_concedido = True
        else:
            # REGLA CONDOMINIO: LDG/Staff o LDT de su propia torre
            es_lider_de_esta_torre = (rol == 'LDT' and request.user.tower == reporte.tower)
            if es_ldg_o_staff or es_lider_de_esta_torre:
                permiso_concedido = True

        # 3. Ejecución de la eliminación
        if permiso_concedido:
            if reporte.archivo_pdf:
                reporte.archivo_pdf.delete(save=False)
            reporte.delete()
            messages.success(request, "Reporte eliminado con éxito.")
        else:
            messages.error(request, "No tienes permiso para eliminar este reporte.")

        return redirect('ver_finanzas', categoria_slug=categoria_slug)

    except ReportePublicado.DoesNotExist:
        messages.warning(request, "El reporte ya no existe.")
        return redirect('url_index')

def descargar_pdf(request, categoria_slug):
    """
    Genera y descarga el archivo PDF con la información financiera filtrada.
    """

    # 1. Definir la categoría y configuración básica
    if categoria_slug == "condominio":
        categoria_filtro = "CON"
        titulo = "Reporte Financiero - Condominio"
        monto_field = "monto_condominio"
    elif categoria_slug == "basura":
        categoria_filtro = "BAS"
        titulo = "Reporte Financiero - Cuarto de Basura"
        monto_field = "monto_basura"
    else:
        return redirect("url_index")

    # 2. Obtener QuerySet Base
    qs = MovimientoFinanciero.objects.filter(categoria=categoria_filtro).select_related("tower").order_by("fecha", "id")

    # 3. UNIFICAR DATOS
    datos = request.POST if request.method == "POST" else request.GET

    # 4. CAPTURAR FILTROS DE FECHA (Lógica Dual)
    f_inicio = datos.get("fecha_inicio")
    f_fin = datos.get("fecha_fin")
    
    # NUEVO: Lógica para Reportes Cerrados (Viene de reportes_vecinos.html)
    mes_rep = datos.get("mes_reporte") or datos.get("mes")
    anio_rep = datos.get("anio_reporte") or datos.get("anio")

    if mes_rep and anio_rep:
        # Si el usuario seleccionó un mes/año específico (Reporte Cerrado)
        f_inicio = date(int(anio_rep), int(mes_rep), 1)
        ultimo_dia = calendar.monthrange(int(anio_rep), int(mes_rep))[1]
        f_fin = date(int(anio_rep), int(mes_rep), ultimo_dia)

    # 5. FILTRO DE TORRE (Unificado)
    torre_id = datos.get("tower_id") or datos.get("torre") or datos.get("tower")
    if torre_id and torre_id != '0' and str(torre_id).isdigit():
        qs = qs.filter(tower__id=int(torre_id))

    # 6. FILTRO DE TIPO
    tipo_filtro = datos.get("tipo", "AMBOS")
    if tipo_filtro == "INGRESOS":
        qs = qs.filter(tipo="ING")
    elif tipo_filtro == "EGRESOS":
        qs = qs.filter(tipo="EGR")

    # 7. APLICAR FILTROS DE FECHA AL QUERYSET FINAL
    if f_inicio and f_inicio != 'null' and f_inicio != '':
        qs = qs.filter(fecha__gte=f_inicio)
    if f_fin and f_fin != 'null' and f_fin != '':
        qs = qs.filter(fecha__lte=f_fin)

    movimientos_query = qs

    # --- INICIO GENERACIÓN PDF (ReportLab) ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Reporte_{categoria_slug}_{timezone.now().strftime("%Y%m%d")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=inch/2, bottomMargin=inch/2, leftMargin=inch/2, rightMargin=inch/2)
    styles = getSampleStyleSheet()
    Story = []

    # Título y Encabezado
    Story.append(Paragraph(f'<font size="16"><b>{titulo}</b></font>', styles["h1"]))
    Story.append(Paragraph(f'<font size="10">Generado el: {timezone.now().strftime("%d/%m/%Y a las %H:%M")}</font>', styles["Normal"]))
    Story.append(Paragraph("<br/>", styles["Normal"]))

    # Info de Filtros en el PDF
    nombre_torre_filtro = "Todas"
    if torre_id and torre_id != '0':
        # Intenta obtener el nombre de la torre para el encabezado del PDF
        from .models import Tower
        t_obj = Tower.objects.filter(id=torre_id).first()
        if t_obj: nombre_torre_filtro = f"Torre {t_obj.nombre}"

    # Formatear fechas para el encabezado del PDF
    inicio_str = f_inicio.strftime("%d/%m/%Y") if hasattr(f_inicio, 'strftime') else (f_inicio if f_inicio else "Inicio")
    fin_str = f_fin.strftime("%d/%m/%Y") if hasattr(f_fin, 'strftime') else (f_fin if f_fin else "Fin")
    fecha_text = f"{inicio_str} hasta {fin_str}" if (f_inicio or f_fin) else "Todo el Historial"

    filtro_info_text = f"<b>Tipo:</b> {tipo_filtro} | <b>Entidad:</b> {nombre_torre_filtro} | <b>Rango:</b> {fecha_text}"
    Story.append(Paragraph(f'<font size="10">{filtro_info_text}</font>', styles["Normal"]))
    Story.append(Paragraph("<br/>", styles["Normal"]))

    # --- 8. Preparación de la Tabla de Datos ---

    # Cabecera de la tabla
    data = [
        [
            "Fecha",
            "Descripción",
            "Torre",
            "Tasa BCV",
            "Ingreso (Bs.)",
            "Egreso (Bs.)",
            "Saldo Acumulado (Bs.)",
        ]
    ]

    # Inicializar Saldo Acumulado (Decimal para precisión)
    saldo_acumulado = Decimal(0.00)

    for mov in movimientos_query:
        monto = getattr(mov, monto_field)

        ingreso = ""
        egreso = ""

        if mov.tipo == "ING":
            saldo_acumulado += monto
            ingreso = f"{monto:,.2f}"  # Formato de moneda
        elif mov.tipo == "EGR":
            saldo_acumulado -= monto
            egreso = f"({monto:,.2f})"  # Usamos paréntesis para egresos

        # 1. Determinar el nombre inicial de la torre
        nombre_torre = mov.tower.nombre if mov.tower else "General"

        # 2. LÓGICA PARA OCULTAR LA TORRE EN EGRESOS DE BASURA
        # Si es un egreso (EGR) Y es de categoría Basura (BAS), la torre debe ser 'General'.
        if mov.tipo == "EGR" and mov.categoria == "BAS":
            nombre_torre = "General"

        tasa_bcv_str = f"{mov.tasa_bcv:,.2f}"

        data.append(
            [
                mov.fecha.strftime("%d/%m/%Y"),
                mov.descripcion,
                nombre_torre,  # <-- Esta variable ahora contiene 'General' si aplica
                tasa_bcv_str,
                ingreso,
                egreso,
                f"{saldo_acumulado:,.2f}",
            ]
        )

    # --- 9. Creación y Estilo de la Tabla ---

    # Anchos de columna
    table_col_widths = [
        1.0 * inch,
        2.5 * inch,
        0.7 * inch,
        0.7 * inch,
        1.0 * inch,
        1.0 * inch,
        1.4 * inch,
    ]

    table = Table(data, colWidths=table_col_widths)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (3, -1), "LEFT"),
                (
                    "ALIGN",
                    (4, 1),
                    (-1, -1),
                    "RIGHT",
                ),  # Alineación derecha para montos y saldo
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7f7f7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )

    Story.append(table)

    # --- 10. Saldo Total Final ---
    Story.append(Paragraph("<br/><br/>", styles["Normal"]))
    Story.append(
        Paragraph(
            f'<font size="14"><b>SALDO FINAL CALCULADO: Bs. {saldo_acumulado:,.2f}</b></font>',
            styles["h2"],
        )
    )

    # 11. Construir el PDF
    doc.build(Story)
    return response


# --- VISTAS DE BENEFICIOS (PÚBLICO + GESTIÓN VISUAL) ---


def vista_beneficio(request, tipo_slug):
    """
    Muestra la lista activa de CLAP o GAS.
    Permite buscar por cédula.
    Muestra botones de administración si el usuario tiene permisos.
    """
    # Mapeo de slug a tipo de modelo
    tipo_map = {"clap": "CLAP", "gas": "GAS"}
    if tipo_slug not in tipo_map:
        return redirect("url_index")

    tipo_db = tipo_map[tipo_slug]
    titulo = "Bolsa CLAP" if tipo_db == "CLAP" else "Bombona de Gas"

    # 1. Buscar Ciclo Activo
    ciclo_activo = CicloBeneficio.objects.filter(tipo=tipo_db, activo=True).first()

    beneficiarios = []
    mensaje_busqueda = ""

    if ciclo_activo:
        # 2. Query Base
        query = EntregaBeneficio.objects.filter(ciclo=ciclo_activo).select_related(
            "beneficiario", "beneficiario__tower"
        )

        # 3. Filtro de Búsqueda (Por Cédula o Nombre)
        busqueda = request.GET.get("q")
        if busqueda:
            query = query.filter(
                Q(beneficiario__cedula__icontains=busqueda)
                | Q(beneficiario__nombres__icontains=busqueda)
                | Q(beneficiario__apellidos__icontains=busqueda)
            )
            mensaje_busqueda = f"Resultados para: '{busqueda}'"

        beneficiarios = query.order_by("beneficiario__tower", "beneficiario__piso")

    # 4. Verificar Permisos de Administración (Para mostrar botones)
    es_admin = False
    if request.user.is_authenticated:
        if request.user.rol == "LDG":
            es_admin = True
        elif tipo_db == "CLAP" and request.user.es_admin_clap:
            es_admin = True
        elif tipo_db == "GAS" and request.user.es_admin_bombonas:
            es_admin = True

    context = {
        "titulo": titulo,
        "tipo_slug": tipo_slug,
        "tipo_db": tipo_db,
        "ciclo": ciclo_activo,
        "beneficiarios": beneficiarios,
        "es_admin": es_admin,
        "busqueda": request.GET.get("q", ""),
    }
    return render(request, "pages/beneficios/lista_beneficio.html", context)


def descargar_pdf_beneficio(request, ciclo_id):
    """Genera el PDF de la lista de beneficiarios de un ciclo específico con Ref. de Pago."""
    ciclo = get_object_or_404(CicloBeneficio, pk=ciclo_id)
    entregas = (
        EntregaBeneficio.objects.filter(ciclo=ciclo)
        .select_related("beneficiario", "beneficiario__tower")
        .order_by("beneficiario__tower", "beneficiario__apartamento_letra")
    )

    response = HttpResponse(content_type="application/pdf")
    filename = f"Listado_{ciclo.get_tipo_display()}_{ciclo.nombre}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []

    # Encabezado
    Story.append(
        Paragraph(
            f"Listado de Beneficiarios - {ciclo.get_tipo_display()}", styles["h1"]
        )
    )
    Story.append(
        Paragraph(
            f"Ciclo: {ciclo.nombre} (Fecha: {ciclo.fecha_apertura})", styles["h3"]
        )
    )
    Story.append(Paragraph("<br/>", styles["Normal"]))

    # --- TABLA ACTUALIZADA CON REFERENCIA ---
    # 1. Agregamos "Ref. Pago" al encabezado de la tabla
    data = [["Torre", "Apto", "Cédula", "Beneficiario", "Jefe", "Ref. Pago"]]
    
    for item in entregas:
        es_jefe = "SÍ" if item.beneficiario.es_jefe_familia else "NO"
        # 2. Obtenemos el nuevo campo referencia_pago (si es None, ponemos un guion)
        ref = item.referencia_pago if item.referencia_pago else "-"
        
        data.append(
            [
                item.beneficiario.tower.nombre,
                item.beneficiario.apartamento_completo,
                item.beneficiario.cedula,
                f"{item.beneficiario.nombres} {item.beneficiario.apellidos}",
                es_jefe,
                ref, # <--- Nuevo dato en la fila
            ]
        )

    # Ajustamos anchos de columna para que el nombre y la referencia tengan espacio
    # Los valores son en puntos. El total para carta (letter) es aprox 450-500 pts útiles.
    column_widths = [40, 50, 70, 180, 40, 80]
    table = Table(data, colWidths=column_widths)
    
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"), # Centrar todo para mejor lectura
                ("ALIGN", (3, 1), (3, -1), "LEFT"),   # Alineamos nombres a la izquierda
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),    # Tamaño de fuente ligeramente menor
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    Story.append(table)
    Story.append(
        Paragraph(f"<br/>Total Beneficiarios: {entregas.count()}", styles["h4"])
    )

    doc.build(Story)
    return response


# --- VISTA DE SOLICITUD DE DOCUMENTOS (PÚBLICA) ---
def vista_solicitar_documento(request):
    """
    Vista pública donde un vecino ingresa su cédula para pedir un documento.
    """
    if request.method == "POST":
        form = SolicitudDocumentoForm(request.POST)
        if form.is_valid():
            cedula = form.cleaned_data["cedula"]
            tipo = form.cleaned_data["tipo_documento"]

            # Buscamos al miembro (ya validamos en el form que existe)
            miembro = CensoMiembro.objects.get(cedula=cedula)

            # Verificamos si ya tiene una solicitud pendiente del mismo tipo
            if SolicitudDocumento.objects.filter(
                beneficiario=miembro, tipo=tipo, estado="PENDIENTE"
            ).exists():
                messages.warning(
                    request,
                    f"Ya tienes una solicitud pendiente para {tipo}. Por favor espera a que sea procesada.",
                )
            else:
                # Creamos la solicitud
                SolicitudDocumento.objects.create(beneficiario=miembro, tipo=tipo)
                messages.success(
                    request,
                    "¡Solicitud enviada con éxito! Tu Líder General procesará el documento pronto.",
                )
                return redirect("url_index")
    else:
        form = SolicitudDocumentoForm()

    return render(request, "pages/solicitudes/crear_solicitud.html", {"form": form})


def handler404(request, exception):
    return render(
        request=request,
        template_name="c404.html",
        status=404,
        context={"page": request.path},
    )


def handler500(request):
    return render(
        request=request,
        template_name="c500.html",
        status=500,
        context={"page": request.get_full_path},
    )


# --- Vistas para el restablecimiento de contraseña con CÓDIGO ---


class RequestResetCodeView(FormView):
    template_name = "pages/registration/request_reset_code_form.html"
    form_class = CustomPasswordResetForm  # Usa CustomPasswordResetForm aquí
    success_url = reverse_lazy("reset_code_sent")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            user = CustomUser.objects.get(email=email)
            # Generar un código de 6 dígitos
            code = "".join(random.choices(string.digits, k=6))
            expiration_time_minutes = 15
            # Crear o actualizar PasswordResetCode
            # Establecer una fecha de expiración (ej. 15 minutos)
            expires_at = timezone.now() + timedelta(minutes=expiration_time_minutes)

            # Eliminar códigos antiguos para este usuario si existen
            PasswordResetCode.objects.filter(user=user).delete()

            PasswordResetCode.objects.create(
                user=user, code=code, expires_at=expires_at
            )

            # Enviar el correo electrónico con el código
            context = {
                "user": user,
                "code": code,
                "expiration_minutes": expiration_time_minutes,  # Formato de hora
            }
            subject = "Tu código de restablecimiento de contraseña"
            email_html_message = render_to_string(
                "pages/registration/reset_code_email.html", context
            )
            email_plain_message = render_to_string(
                "pages/registration/reset_code_email.txt", context
            )

            msg = EmailMultiAlternatives(
                subject, email_plain_message, settings.DEFAULT_FROM_EMAIL, [email]
            )
            msg.attach_alternative(email_html_message, "text/html")
            msg.send()

            messages.success(
                self.request, "Se ha enviado un código a tu correo electrónico."
            )
        except CustomUser.DoesNotExist:
            messages.error(
                self.request, "No existe un usuario con ese correo electrónico."
            )
            return self.form_invalid(form)

        return super().form_valid(form)


def reset_code_sent(request):
    return render(request, "pages/registration/reset_code_sent.html")


class VerifyResetCodeView(FormView):
    template_name = "pages/registration/verify_reset_code_form.html"
    form_class = VerifyResetCodeForm
    success_url = reverse_lazy("set_new_password")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        code = form.cleaned_data["code"]

        try:
            user = CustomUser.objects.get(email=email)
            reset_code_obj = PasswordResetCode.objects.get(user=user, code=code)

            if reset_code_obj.is_valid():
                # El código es válido, almacenar el user_id y el código en la sesión
                # para usarlos en SetNewPasswordView
                self.request.session["password_reset_user_id"] = user.id
                self.request.session["password_reset_code"] = str(
                    code
                ).strip()  # Opcional, pero útil para verificar de nuevo
                messages.success(
                    self.request,
                    "Código verificado con éxito. Ahora puedes establecer una nueva contraseña.",
                )
                return super().form_valid(form)
            else:
                messages.error(self.request, "El código ha expirado o es inválido.")
        except (CustomUser.DoesNotExist, PasswordResetCode.DoesNotExist):
            messages.error(self.request, "Correo electrónico o código incorrectos.")

        return self.form_invalid(form)


class SetNewPasswordView(FormView):
    template_name = "pages/registration/set_new_password_form.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("password_reset_complete_custom")

    def dispatch(self, request, *args, **kwargs):
        # Verificar si el usuario ha pasado por la verificación del código
        user_id = request.session.get("password_reset_user_id")
        reset_code = request.session.get("password_reset_code")

        if not user_id or not reset_code:
            messages.error(
                request,
                "Acceso denegado. Por favor, solicita un código de restablecimiento primero.",
            )
            return redirect("request_reset_code")

        # Opcional: verificar el código de nuevo por si se usa la URL directamente
        try:
            password_code = PasswordResetCode.objects.filter(
                user_id=user_id, code=reset_code.strip()
            ).first()
            if not password_code or not password_code.is_valid():
                messages.error(request, "El código es inválido o ha expirado.")
                return redirect("request_reset_code")
        except Exception:
            messages.error(request, "Hubo un error en la verificación.")
            return redirect("request_reset_code")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get("password_reset_user_id")
        user = CustomUser.objects.get(id=user_id)
        kwargs["user"] = user
        return kwargs

    def form_valid(self, form):
        user_id = self.request.session.get("password_reset_user_id")
        user = CustomUser.objects.get(id=user_id)

        # Eliminar todos los códigos de restablecimiento para este usuario una vez que la contraseña es cambiada
        PasswordResetCode.objects.filter(user=user).delete()

        form.save()  # Guarda la nueva contraseña
        messages.success(
            self.request,
            "Tu contraseña ha sido restablecida con éxito. Ya puedes iniciar sesión.",
        )

        # Limpiar la sesión después de cambiar la contraseña
        if "password_reset_user_id" in self.request.session:
            del self.request.session["password_reset_user_id"]
        if "password_reset_code" in self.request.session:
            del self.request.session["password_reset_code"]

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Por favor, corrige los errores en la contraseña. Asegúrate de que coincidan y cumplan con los requisitos.",
        )
        return super().form_invalid(form)


class PasswordResetCompleteCustomView(TemplateView):
    """Muestra un mensaje de éxito después de que la contraseña ha sido cambiada."""

    template_name = "pages/registration/password_reset_complete_custom.html"  # Nombre de tu nueva plantilla
