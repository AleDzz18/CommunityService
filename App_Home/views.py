# App_Home/views.py

import json
from datetime import datetime, timedelta
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

from Community_Service.decorators import complete_profile
from .forms import (
    FormularioCreacionUsuario,
    FormularioPerfilUsuario,
    FormularioFiltroMovimientos,
    SolicitudDocumentoForm,
)
from .models import (
    CustomUser,
    Tower,
    MovimientoFinanciero,
    CicloBeneficio,
    EntregaBeneficio,
    CensoMiembro,
    SolicitudDocumento,
)
from decimal import Decimal
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
)
import random
import string


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
def ver_ingresos_egresos(request, categoria_slug):
    """
    Muestra la lista de movimientos financieros para Condominio o Cuarto de Basura.
    Accesible por usuarios NO autenticados (Usuario Básico).
    """
    # 1. Definir la categoría y el título basados en el slug de la URL
    if categoria_slug == "condominio":
        categoria_filtro = "CON"
        titulo = "Administración de Ingresos y Egresos - Condominio"
        monto_field = "monto_condominio"  # Campo de monto dinámico
    elif categoria_slug == "basura":
        categoria_filtro = "BAS"
        titulo = "Administración de Ingresos y Egresos - Cuarto de Basura"
        monto_field = "monto_basura"  # Campo de monto dinámico
    else:
        # Si la URL es inválida, se redirige al dashboard.
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
            return redirect("ver_finanzas", categoria_slug=categoria_slug)

        # 2. Restricción por Torre (Se mantiene la lógica)
        if (
            not request.user.is_authenticated
            or request.user.rol != "LDT"
            or not request.user.tower
        ):
            messages.error(
                request,
                "Operación denegada. Solo los Líderes de Torre asignados pueden registrar movimientos.",
            )
            return redirect("ver_finanzas", categoria_slug=categoria_slug)

        torre_asignada = request.user.tower

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
                    "ver_finanzas", categoria_slug=categoria_slug
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
        return redirect("ver_finanzas", categoria_slug=categoria_slug)

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
    torre_id = request.GET.get("torre")
    if torre_id is None:
        user_tower_id = getattr(request.user, "tower_id", None)
        if user_tower_id:
            movimientos_query = movimientos_query.filter(tower__id=int(user_tower_id))
            torre_id = str(user_tower_id)
        else:
            torre_id = "0"
    elif torre_id is not None and torre_id.isdigit() and torre_id != "0":
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

    context = {
        "titulo": titulo,
        "movimientos": movimientos_con_saldo,
        "torres": torres,
        "tipo_seleccionado": tipo_filtro,
        "torre_seleccionada_id": torre_id,
        "categoria_slug": categoria_slug,  # Para el botón de descarga
        "filtro_form": filtro_form,  # Formulario de filtro para la plantilla
    }

    return render(request, "pages/finanzas/listado_movimientos.html", context)


def descargar_pdf(request, categoria_slug):
    """
    Genera y descarga el archivo PDF con la información financiera filtrada.
    """
    # 1. Definir la categoría, título y campo de monto (monto_field)
    if categoria_slug == "condominio":
        categoria_filtro = "CON"
        titulo = "Reporte Financiero - Condominio"
        monto_field = "monto_condominio"
    elif categoria_slug == "basura":
        categoria_filtro = "BAS"
        titulo = "Reporte Financiero - Cuarto de Basura"
        monto_field = "monto_basura"
    else:
        # Redireccionar si el slug es inválido
        return redirect("url_index")

    # 2. Obtener QuerySet Base
    movimientos_query = (
        MovimientoFinanciero.objects.filter(categoria=categoria_filtro)
        .select_related("tower")
        .order_by("fecha", "id")
    )

    # 3. FILTROS POR TIPO Y TORRE (Lógica existente)
    tipo_filtro = request.GET.get("tipo", "AMBOS")
    if tipo_filtro == "INGRESOS":
        movimientos_query = movimientos_query.filter(tipo="ING")
    elif tipo_filtro == "EGRESOS":
        movimientos_query = movimientos_query.filter(tipo="EGR")

    torre_id = request.GET.get("torre")
    if torre_id and torre_id.isdigit():
        movimientos_query = movimientos_query.filter(tower__id=int(torre_id))

    # 4. 🚀 APLICAR FILTRO POR RANGO DE FECHAS (NUEVO)
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

    # --- FIN Lógica de Filtrado ---

    # 5. Configuración de la Respuesta HTTP
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Reporte_{categoria_slug}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    )

    # 6. Preparación del documento PDF con SimpleDocTemplate
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        topMargin=inch / 2,
        bottomMargin=inch / 2,
        leftMargin=inch / 2,
        rightMargin=inch / 2,
    )
    styles = getSampleStyleSheet()
    Story = []

    # --- 7. Encabezado del Reporte ---
    Story.append(Paragraph(f'<font size="16"><b>{titulo}</b></font>', styles["h1"]))
    Story.append(
        Paragraph(
            f'<font size="10">Generado el: {timezone.now().strftime("%d/%m/%Y a las %H:%M")}</font>',
            styles["Normal"],
        )
    )
    Story.append(Paragraph("<br/>", styles["Normal"]))

    # Info de Filtros (para mostrar qué se filtró)
    filtro_info_text = f"<b>Tipo:</b> {tipo_filtro} | <b>Torre ID:</b> {torre_id if torre_id else 'Todas'}"

    # Detalle de Fechas
    f_i = filtro_form.cleaned_data.get("fecha_inicio")
    f_f = filtro_form.cleaned_data.get("fecha_fin")

    fecha_text = "Todo el Historial"
    if f_i or f_f:
        inicio_str = f_i.strftime("%d/%m/%Y") if f_i else "Inicio"
        fin_str = f_f.strftime("%d/%m/%Y") if f_f else "Fin"
        fecha_text = f"{inicio_str} hasta {fin_str}"

    filtro_info_text += f" | <b>Rango de Fechas:</b> {fecha_text}"

    Story.append(
        Paragraph(f'<font size="10">{filtro_info_text}</font>', styles["Normal"])
    )
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
    """Genera el PDF de la lista de beneficiarios de un ciclo específico."""
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

    # Tabla
    data = [["Torre", "Apto", "Cédula", "Beneficiario", "Jefe Familia"]]
    for item in entregas:
        es_jefe = "SÍ" if item.beneficiario.es_jefe_familia else "NO"
        data.append(
            [
                item.beneficiario.tower.nombre,
                item.beneficiario.apartamento_completo,
                item.beneficiario.cedula,
                f"{item.beneficiario.nombres} {item.beneficiario.apellidos}",
                es_jefe,
            ]
        )

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
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
    return render(request=request, template_name="c404.html", status=404)


def handler500(request):
    return render(request=request, template_name="c500.html", status=500)


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
            # Crear o actualizar PasswordResetCode
            # Establecer una fecha de expiración (ej. 15 minutos)
            expires_at = timezone.now() + timedelta(minutes=15)

            # Eliminar códigos antiguos para este usuario si existen
            PasswordResetCode.objects.filter(user=user).delete()

            PasswordResetCode.objects.create(
                user=user, code=code, expires_at=expires_at
            )

            # Enviar el correo electrónico con el código
            context = {
                "user": user,
                "code": code,
                "expiration_time": expires_at.strftime("%H:%M"),  # Formato de hora
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
                self.request.session["password_reset_code"] = (
                    code  # Opcional, pero útil para verificar de nuevo
                )
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

        if not user_id:
            messages.error(
                request,
                "Acceso denegado. Por favor, solicita un código de restablecimiento primero.",
            )
            return redirect("request_reset_code")

        # Opcional: verificar el código de nuevo por si se usa la URL directamente
        try:
            user = CustomUser.objects.get(id=user_id)
            password_code = PasswordResetCode.objects.get(user=user, code=reset_code)
            if not password_code.is_valid():
                messages.error(
                    request, "El código ha expirado. Por favor, solicita uno nuevo."
                )
                return redirect("request_reset_code")
        except (CustomUser.DoesNotExist, PasswordResetCode.DoesNotExist):
            messages.error(
                request,
                "Verificación de código inválida. Por favor, solicita uno nuevo.",
            )
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
